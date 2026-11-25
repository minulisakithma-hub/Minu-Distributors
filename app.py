"""
================================================================================
MINU DISTRIBUTORS - B2B Chocolate Distribution System
Authorized B2B Distributor for Ceylon Biscuits Limited (CBL)
Tech Stack: Python (Flask), SQLite3, HTML5, CSS3, Vanilla JavaScript
================================================================================
Description:
A clean, minimal, and fully-functional B2B web application designed for a 
first-year IT student to understand, demonstrate, and defend in a viva examination.
"""

import os
import sqlite3
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

# ------------------------------------------------------------------------------
# APPLICATION CONFIGURATION
# ------------------------------------------------------------------------------
app = Flask(__name__)
# Secret key used by Flask to cryptographically sign session cookies
app.secret_key = "minu_distributors_cbl_secure_key_2026"

DATABASE = os.path.join(os.path.abspath(os.path.dirname(__file__)), "minu_distributors.db")


# ------------------------------------------------------------------------------
# DATABASE CONNECTION & INITIALIZATION
# ------------------------------------------------------------------------------
def get_db_connection():
    """
    Creates and returns a database connection.
    row_factory = sqlite3.Row allows accessing columns by name like dictionary keys.
    """
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Initializes database tables if they do not exist.
    Populates sample CBL chocolate products and batches if the product catalog is empty.
    NOTE: In adherence to strict security rules, NO hardcoded or pre-seeded user accounts exist.
    All users register dynamically through the application.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Users Table (Stores Admin, Store Manager, and Retailer accounts)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,              -- 'admin', 'store_manager', 'retailer'
            full_name TEXT NOT NULL,
            shop_name TEXT,                  -- Retailer's shop name
            phone TEXT,
            address TEXT,
            status TEXT DEFAULT 'pending',    -- 'active', 'pending', 'deactivated'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. Products Table (Stores CBL Ritzbury & Tiara chocolate items)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT DEFAULT 'Chocolates',
            box_size TEXT NOT NULL,          -- e.g., '24 Bars / Box'
            price_per_box REAL NOT NULL,     -- Wholesale B2B Price in LKR
            stock_boxes INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 3. Product Batches Table (For Expiry Date Tracking & Management)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            batch_number TEXT NOT NULL,
            quantity_boxes INTEGER NOT NULL,
            expiry_date TEXT NOT NULL,       -- Stored as 'YYYY-MM-DD'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
        )
    """)

    # 4. Orders Table (Stores B2B Purchase Orders placed by Retailers)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            retailer_id INTEGER NOT NULL,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_amount REAL NOT NULL,
            payment_terms TEXT NOT NULL,     -- 'Cash on Delivery' or '30-Day Corporate Credit Invoice'
            status TEXT DEFAULT 'Pending',   -- 'Pending', 'Approved', 'Dispatched', 'Rejected', 'Cancelled'
            notes TEXT,
            FOREIGN KEY (retailer_id) REFERENCES users (id)
        )
    """)

    # 5. Order Items Table (Detailed line items for each order)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity_boxes INTEGER NOT NULL,
            price_per_box REAL NOT NULL,
            subtotal REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders (id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    """)

    # Pre-populate sample CBL chocolate items ONLY if product table is completely empty
    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        cbl_sample_products = [
            ("Ritzbury Revello Special Cashew (100g)", "Chocolates", "24 Bars per Box", 14400.00, 85),
            ("Ritzbury Chunky Choc Milk (45g)", "Chocolates", "48 Bars per Box", 9600.00, 110),
            ("Ritzbury Pebbles Bumper Pack (50g)", "Chocolates", "50 Packs per Box", 12500.00, 70),
            ("CBL Tiara Rollo Chocolate Cake (30g)", "Bakery & Cakes", "36 Packs per Box", 7200.00, 140),
            ("Ritzbury Chit Chat Crunchy Wafers (32g)", "Wafers", "40 Packs per Box", 8000.00, 95),
            ("Ritzbury Revello Hazelnut Praline (100g)", "Chocolates", "24 Bars per Box", 16800.00, 45)
        ]
        cursor.executemany("""
            INSERT INTO products (name, category, box_size, price_per_box, stock_boxes)
            VALUES (?, ?, ?, ?, ?)
        """, cbl_sample_products)

        # Seed sample batches with realistic expiry dates (some safe, some approaching expiry)
        today = date.today()
        cursor.execute("""
            INSERT INTO batches (product_id, batch_number, quantity_boxes, expiry_date)
            VALUES 
            (1, 'CBL-REV-2026A', 50, ?),
            (2, 'CBL-CHK-2026B', 60, ?),
            (3, 'CBL-PEB-2026C', 40, ?),
            (4, 'CBL-TIA-2026D', 70, ?)
        """, (
            (today + timedelta(days=45)).strftime("%Y-%m-%d"),   # Approaching expiry alert
            (today + timedelta(days=180)).strftime("%Y-%m-%d"),  # Safe
            (today + timedelta(days=20)).strftime("%Y-%m-%d"),   # Urgent alert (< 30 days)
            (today + timedelta(days=240)).strftime("%Y-%m-%d")   # Safe
        ))

    conn.commit()
    conn.close()


# ------------------------------------------------------------------------------
# AUTHENTICATION & ACCESS CONTROL HELPERS
# ------------------------------------------------------------------------------
def get_logged_in_user():
    """Helper to retrieve the current session user record from SQLite."""
    if "user_id" not in session:
        return None
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    conn.close()
    return user


# ------------------------------------------------------------------------------
# GENERAL ROUTES (INDEX, REGISTER, LOGIN, LOGOUT)
# ------------------------------------------------------------------------------
@app.route("/")
def index():
    """Landing route: redirects based on login session and role."""
    if "user_id" in session:
        role = session.get("role")
        if role == "admin":
            return redirect(url_for("admin_dashboard"))
        elif role == "store_manager":
            return redirect(url_for("manager_dashboard"))
        elif role == "retailer":
            return redirect(url_for("retailer_dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    """
    User registration route.
    Supports Retailers, Store Managers, and System Admins dynamically.
    Retailers start as 'pending' for Admin approval.
    Managers and Admins are registered as 'active' for immediate system management.
    """
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        shop_name = request.form.get("shop_name", "").strip()
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "").strip()
        role = request.form.get("role", "retailer").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()

        # Basic validation
        if not full_name or not username or not password or not role:
            flash("Please fill in all required fields.", "danger")
            return redirect(url_for("register"))

        if role == "retailer" and not shop_name:
            flash("Retailers must provide a Shop Name.", "danger")
            return redirect(url_for("register"))

        conn = get_db_connection()
        existing_user = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()

        if existing_user:
            conn.close()
            flash("Username already exists. Please choose a different username.", "warning")
            return redirect(url_for("register"))

        # Role-based status: Retailers are 'pending' (need admin approval); Admins/Managers are 'active'
        initial_status = "pending" if role == "retailer" else "active"
        password_hash = generate_password_hash(password)

        conn.execute("""
            INSERT INTO users (username, password_hash, role, full_name, shop_name, phone, address, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (username, password_hash, role, full_name, shop_name, phone, address, initial_status))
        conn.commit()
        conn.close()

        if role == "retailer":
            flash("Registration submitted successfully! Your account is pending Admin approval.", "info")
        else:
            flash(f"{role.replace('_', ' ').title()} account created successfully! You can now log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Login route. Authenticates user, verifies password hash,
    and dynamically routes to the appropriate role-based dashboard.
    """
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "").strip()

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            # Check user status
            if user["status"] == "pending":
                flash("Your account is pending approval by the Admin. Please check back soon.", "warning")
                return redirect(url_for("login"))
            elif user["status"] == "deactivated":
                flash("Your account has been deactivated. Please contact Minu Distributors Admin.", "danger")
                return redirect(url_for("login"))

            # Set session variables
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            session["full_name"] = user["full_name"]
            session["shop_name"] = user["shop_name"] or ""

            flash(f"Welcome back, {user['full_name']}!", "success")

            # Dynamic Role Routing
            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))
            elif user["role"] == "store_manager":
                return redirect(url_for("manager_dashboard"))
            elif user["role"] == "retailer":
                return redirect(url_for("retailer_dashboard"))
            else:
                return redirect(url_for("login"))
        else:
            flash("Invalid username or password. Please try again.", "danger")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    """Logs the user out by clearing the session."""
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("login"))


# ------------------------------------------------------------------------------
# RETAILER MODULE
# ------------------------------------------------------------------------------
@app.route("/retailer")
def retailer_dashboard():
    """
    Retailer Dashboard:
    - View CBL chocolate products catalog with wholesale prices & live stock
    - View past order history with tracking statuses
    - View and manage shop profile details
    """
    if "user_id" not in session or session.get("role") != "retailer":
        flash("Please log in as a Retailer to access this page.", "warning")
        return redirect(url_for("login"))

    user = get_logged_in_user()
    conn = get_db_connection()

    # 1. Fetch available CBL products
    products = conn.execute("SELECT * FROM products ORDER BY name ASC").fetchall()

    # 2. Fetch past orders placed by this retailer
    orders_raw = conn.execute("""
        SELECT * FROM orders 
        WHERE retailer_id = ? 
        ORDER BY order_date DESC
    """, (session["user_id"],)).fetchall()

    # 3. For each order, fetch associated line items
    orders = []
    for ord_row in orders_raw:
        items = conn.execute("""
            SELECT oi.*, p.name as product_name, p.box_size
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = ?
        """, (ord_row["id"],)).fetchall()
        orders.append({
            "order": ord_row,
            "items": items
        })

    conn.close()
    return render_template("retailer.html", user=user, products=products, orders=orders)


@app.route("/retailer/order", methods=["POST"])
def place_order():
    """
    Processes a bulk order from the retailer.
    Captures quantities per product, checks stock, computes subtotal, and creates records.
    """
    if "user_id" not in session or session.get("role") != "retailer":
        return redirect(url_for("login"))

    payment_terms = request.form.get("payment_terms", "Cash on Delivery")
    notes = request.form.get("notes", "").strip()

    conn = get_db_connection()
    products = conn.execute("SELECT * FROM products").fetchall()

    # Inspect submitted quantities from the form
    order_items_to_create = []
    total_order_amount = 0.0

    for prod in products:
        field_name = f"qty_{prod['id']}"
        qty_str = request.form.get(field_name, "0").strip()
        try:
            qty = int(qty_str)
        except ValueError:
            qty = 0

        if qty > 0:
            if qty > prod["stock_boxes"]:
                conn.close()
                flash(f"Insufficient stock for '{prod['name']}'. Available: {prod['stock_boxes']} boxes.", "danger")
                return redirect(url_for("retailer_dashboard"))

            subtotal = qty * prod["price_per_box"]
            total_order_amount += subtotal
            order_items_to_create.append({
                "product_id": prod["id"],
                "quantity": qty,
                "price": prod["price_per_box"],
                "subtotal": subtotal
            })

    if not order_items_to_create:
        conn.close()
        flash("Please select at least 1 box of chocolate to place an order.", "warning")
        return redirect(url_for("retailer_dashboard"))

    # Insert Master Order
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO orders (retailer_id, total_amount, payment_terms, status, notes)
        VALUES (?, ?, ?, 'Pending', ?)
    """, (session["user_id"], total_order_amount, payment_terms, notes))
    new_order_id = cursor.lastrowid

    # Insert Order Line Items
    for item in order_items_to_create:
        cursor.execute("""
            INSERT INTO order_items (order_id, product_id, quantity_boxes, price_per_box, subtotal)
            VALUES (?, ?, ?, ?, ?)
        """, (new_order_id, item["product_id"], item["quantity"], item["price"], item["subtotal"]))

    conn.commit()
    conn.close()

    flash(f"Order #{new_order_id} placed successfully! Status: Pending Approval.", "success")
    return redirect(url_for("retailer_dashboard"))


@app.route("/retailer/order/cancel/<int:order_id>", methods=["POST"])
def cancel_order(order_id):
    """Allows a retailer to cancel their own order only if it is still 'Pending'."""
    if "user_id" not in session or session.get("role") != "retailer":
        return redirect(url_for("login"))

    conn = get_db_connection()
    order = conn.execute("SELECT * FROM orders WHERE id = ? AND retailer_id = ?", (order_id, session["user_id"])).fetchone()

    if not order:
        conn.close()
        flash("Order not found.", "danger")
        return redirect(url_for("retailer_dashboard"))

    if order["status"] != "Pending":
        conn.close()
        flash(f"Order #{order_id} cannot be cancelled because its status is already '{order['status']}'.", "warning")
        return redirect(url_for("retailer_dashboard"))

    conn.execute("UPDATE orders SET status = 'Cancelled' WHERE id = ?", (order_id,))
    conn.commit()
    conn.close()

    flash(f"Order #{order_id} has been cancelled successfully.", "info")
    return redirect(url_for("retailer_dashboard"))


@app.route("/retailer/profile/update", methods=["POST"])
def update_retailer_profile():
    """Allows retailer to update their shop details (Manage profile shop details)."""
    if "user_id" not in session or session.get("role") != "retailer":
        return redirect(url_for("login"))

    full_name = request.form.get("full_name", "").strip()
    shop_name = request.form.get("shop_name", "").strip()
    phone = request.form.get("phone", "").strip()
    address = request.form.get("address", "").strip()

    conn = get_db_connection()
    conn.execute("""
        UPDATE users 
        SET full_name = ?, shop_name = ?, phone = ?, address = ?
        WHERE id = ?
    """, (full_name, shop_name, phone, address, session["user_id"]))
    conn.commit()
    conn.close()

    session["full_name"] = full_name
    session["shop_name"] = shop_name

    flash("Shop profile details updated successfully!", "success")
    return redirect(url_for("retailer_dashboard"))


# ------------------------------------------------------------------------------
# STORE MANAGER MODULE
# ------------------------------------------------------------------------------
@app.route("/manager")
def manager_dashboard():
    """
    Store Manager Dashboard:
    - Pending Order Process (Approve, Reject, Dispatch)
    - Manage Product Catalog (View, Add, Edit items)
    - Expiry Management (Add expiry dates & View expiry alerts)
    - Stock & Sales Monitoring (Daily stocks & Executive sales reports)
    """
    if "user_id" not in session or session.get("role") not in ["store_manager", "admin"]:
        flash("Access restricted to Store Managers & Admins.", "warning")
        return redirect(url_for("login"))

    conn = get_db_connection()

    # 1. Orders list (with retailer info)
    orders_raw = conn.execute("""
        SELECT o.*, u.full_name as retailer_name, u.shop_name, u.phone as retailer_phone
        FROM orders o
        JOIN users u ON o.retailer_id = u.id
        ORDER BY o.order_date DESC
    """).fetchall()

    orders = []
    for ord_row in orders_raw:
        items = conn.execute("""
            SELECT oi.*, p.name as product_name, p.box_size
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = ?
        """, (ord_row["id"],)).fetchall()
        orders.append({
            "order": ord_row,
            "items": items
        })

    # 2. Product Catalog / Daily Stocks
    products = conn.execute("SELECT * FROM products ORDER BY name ASC").fetchall()

    # 3. Expiry Management & Alerts
    batches = conn.execute("""
        SELECT b.*, p.name as product_name, p.box_size
        FROM batches b
        JOIN products p ON b.product_id = p.id
        ORDER BY b.expiry_date ASC
    """).fetchall()

    today = date.today()
    expiry_alerts = []
    for b in batches:
        exp_date = datetime.strptime(b["expiry_date"], "%Y-%m-%d").date()
        days_left = (exp_date - today).days

        if days_left < 0:
            status = "EXPIRED"
            badge = "badge-danger"
        elif days_left <= 30:
            status = "CRITICAL (<= 30 Days)"
            badge = "badge-danger"
        elif days_left <= 60:
            status = "WARNING (<= 60 Days)"
            badge = "badge-warning"
        else:
            status = "GOOD"
            badge = "badge-success"

        expiry_alerts.append({
            "batch": b,
            "days_left": days_left,
            "status": status,
            "badge": badge
        })

    # 4. Sales Reports Metrics
    total_sales_revenue = conn.execute("""
        SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE status IN ('Approved', 'Dispatched')
    """).fetchone()[0]

    total_orders_count = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    pending_orders_count = conn.execute("SELECT COUNT(*) FROM orders WHERE status = 'Pending'").fetchone()[0]
    approved_orders_count = conn.execute("SELECT COUNT(*) FROM orders WHERE status IN ('Approved', 'Dispatched')").fetchone()[0]

    # Revenue by Payment Terms
    revenue_cod = conn.execute("""
        SELECT COALESCE(SUM(total_amount), 0) FROM orders 
        WHERE status IN ('Approved', 'Dispatched') AND payment_terms = 'Cash on Delivery'
    """).fetchone()[0]

    revenue_credit = conn.execute("""
        SELECT COALESCE(SUM(total_amount), 0) FROM orders 
        WHERE status IN ('Approved', 'Dispatched') AND payment_terms LIKE '%Credit%'
    """).fetchone()[0]

    sales_report = {
        "total_revenue": total_sales_revenue,
        "total_orders": total_orders_count,
        "pending_orders": pending_orders_count,
        "approved_orders": approved_orders_count,
        "revenue_cod": revenue_cod,
        "revenue_credit": revenue_credit
    }

    conn.close()
    return render_template("manager.html", 
                           orders=orders, 
                           products=products, 
                           expiry_alerts=expiry_alerts, 
                           sales_report=sales_report)


@app.route("/manager/order/status/<int:order_id>", methods=["POST"])
def update_order_status(order_id):
    """
    Store Manager handles order progression:
    - 'Approve': Deducts stock from products to fulfill the bulk order.
    - 'Reject': Leaves stock unchanged.
    - 'Dispatched': Flags order as out for delivery.
    """
    if "user_id" not in session or session.get("role") not in ["store_manager", "admin"]:
        return redirect(url_for("login"))

    new_status = request.form.get("status")
    if new_status not in ["Approved", "Rejected", "Dispatched"]:
        flash("Invalid status specified.", "danger")
        return redirect(url_for("manager_dashboard"))

    conn = get_db_connection()
    cursor = conn.cursor()

    order = cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not order:
        conn.close()
        flash("Order not found.", "danger")
        return redirect(url_for("manager_dashboard"))

    # When an order is Approved for the first time, deduct product inventory
    if new_status == "Approved" and order["status"] == "Pending":
        items = cursor.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,)).fetchall()
        # Verify stock sufficiency for all items first
        for it in items:
            prod = cursor.execute("SELECT stock_boxes, name FROM products WHERE id = ?", (it["product_id"],)).fetchone()
            if prod["stock_boxes"] < it["quantity_boxes"]:
                conn.close()
                flash(f"Cannot approve order: Insufficient stock for '{prod['name']}'. (Requires {it['quantity_boxes']}, available {prod['stock_boxes']}).", "danger")
                return redirect(url_for("manager_dashboard"))

        # Deduct stock
        for it in items:
            cursor.execute("""
                UPDATE products 
                SET stock_boxes = stock_boxes - ? 
                WHERE id = ?
            """, (it["quantity_boxes"], it["product_id"]))

    cursor.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
    conn.commit()
    conn.close()

    flash(f"Order #{order_id} marked as '{new_status}'.", "success")
    return redirect(url_for("manager_dashboard"))


@app.route("/manager/product/add", methods=["POST"])
def add_product():
    """Adds a new CBL chocolate product to the catalog."""
    if "user_id" not in session or session.get("role") not in ["store_manager", "admin"]:
        return redirect(url_for("login"))

    name = request.form.get("name", "").strip()
    category = request.form.get("category", "Chocolates").strip()
    box_size = request.form.get("box_size", "").strip()
    price_per_box = float(request.form.get("price_per_box", 0))
    stock_boxes = int(request.form.get("stock_boxes", 0))

    if not name or not box_size or price_per_box <= 0:
        flash("Please enter valid product details.", "danger")
        return redirect(url_for("manager_dashboard"))

    conn = get_db_connection()
    conn.execute("""
        INSERT INTO products (name, category, box_size, price_per_box, stock_boxes)
        VALUES (?, ?, ?, ?, ?)
    """, (name, category, box_size, price_per_box, stock_boxes))
    conn.commit()
    conn.close()

    flash(f"Product '{name}' added to catalog successfully!", "success")
    return redirect(url_for("manager_dashboard"))


@app.route("/manager/product/edit/<int:product_id>", methods=["POST"])
def edit_product(product_id):
    """Edits price, stock, or packaging of an existing CBL chocolate item."""
    if "user_id" not in session or session.get("role") not in ["store_manager", "admin"]:
        return redirect(url_for("login"))

    name = request.form.get("name", "").strip()
    category = request.form.get("category", "Chocolates").strip()
    box_size = request.form.get("box_size", "").strip()
    price_per_box = float(request.form.get("price_per_box", 0))
    stock_boxes = int(request.form.get("stock_boxes", 0))

    conn = get_db_connection()
    conn.execute("""
        UPDATE products 
        SET name = ?, category = ?, box_size = ?, price_per_box = ?, stock_boxes = ?
        WHERE id = ?
    """, (name, category, box_size, price_per_box, stock_boxes, product_id))
    conn.commit()
    conn.close()

    flash(f"Product #{product_id} updated successfully!", "success")
    return redirect(url_for("manager_dashboard"))


@app.route("/manager/batch/add", methods=["POST"])
def add_batch():
    """Adds a new batch with an expiry date, and updates inventory quantity."""
    if "user_id" not in session or session.get("role") not in ["store_manager", "admin"]:
        return redirect(url_for("login"))

    product_id = int(request.form.get("product_id"))
    batch_number = request.form.get("batch_number", "").strip()
    quantity_boxes = int(request.form.get("quantity_boxes", 0))
    expiry_date_str = request.form.get("expiry_date", "").strip()

    if not batch_number or quantity_boxes <= 0 or not expiry_date_str:
        flash("Please provide all required batch details.", "danger")
        return redirect(url_for("manager_dashboard"))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Record the batch
    cursor.execute("""
        INSERT INTO batches (product_id, batch_number, quantity_boxes, expiry_date)
        VALUES (?, ?, ?, ?)
    """, (product_id, batch_number, quantity_boxes, expiry_date_str))

    # Add received batch quantity to overall product stock
    cursor.execute("""
        UPDATE products 
        SET stock_boxes = stock_boxes + ? 
        WHERE id = ?
    """, (quantity_boxes, product_id))

    conn.commit()
    conn.close()

    flash(f"Batch '{batch_number}' added with expiry date {expiry_date_str}! Stock updated.", "success")
    return redirect(url_for("manager_dashboard"))


# ------------------------------------------------------------------------------
# ADMIN MODULE
# ------------------------------------------------------------------------------
@app.route("/admin")
def admin_dashboard():
    """
    Admin Management Dashboard:
    - View and manage all registered retailer accounts
    - Activate, Deactivate, or Approve retailer accounts
    - Executive system statistics
    """
    if "user_id" not in session or session.get("role") != "admin":
        flash("Access restricted to System Administrators.", "warning")
        return redirect(url_for("login"))

    conn = get_db_connection()

    # Fetch all retailers
    retailers = conn.execute("""
        SELECT * FROM users 
        WHERE role = 'retailer' 
        ORDER BY created_at DESC
    """).fetchall()

    # Also fetch other staff accounts for completeness
    staff = conn.execute("""
        SELECT * FROM users 
        WHERE role != 'retailer' 
        ORDER BY created_at DESC
    """).fetchall()

    # Statistics
    stats = {
        "total_retailers": conn.execute("SELECT COUNT(*) FROM users WHERE role = 'retailer'").fetchone()[0],
        "pending_retailers": conn.execute("SELECT COUNT(*) FROM users WHERE role = 'retailer' AND status = 'pending'").fetchone()[0],
        "active_retailers": conn.execute("SELECT COUNT(*) FROM users WHERE role = 'retailer' AND status = 'active'").fetchone()[0],
        "total_orders": conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    }

    conn.close()
    return render_template("admin.html", retailers=retailers, staff=staff, stats=stats)


@app.route("/admin/user/status/<int:user_id>", methods=["POST"])
def update_user_status(user_id):
    """Admin action to Approve, Activate, or Deactivate an account."""
    if "user_id" not in session or session.get("role") != "admin":
        return redirect(url_for("login"))

    new_status = request.form.get("status")
    if new_status not in ["active", "deactivated", "pending"]:
        flash("Invalid status.", "danger")
        return redirect(url_for("admin_dashboard"))

    # Protect current logged in admin from deactivating themselves
    if user_id == session.get("user_id"):
        flash("You cannot change your own status.", "danger")
        return redirect(url_for("admin_dashboard"))

    conn = get_db_connection()
    conn.execute("UPDATE users SET status = ? WHERE id = ?", (new_status, user_id))
    conn.commit()
    conn.close()

    flash(f"User account #{user_id} status updated to '{new_status.title()}'.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/user/delete/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    """Admin action to remove a user record."""
    if "user_id" not in session or session.get("role") != "admin":
        return redirect(url_for("login"))

    if user_id == session.get("user_id"):
        flash("You cannot delete your own admin account.", "danger")
        return redirect(url_for("admin_dashboard"))

    conn = get_db_connection()
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

    flash(f"User account #{user_id} deleted successfully.", "info")
    return redirect(url_for("admin_dashboard"))


# ------------------------------------------------------------------------------
# APPLICATION LAUNCHER
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    # Ensure database and tables are created before starting the server
    init_db()
    print("==================================================")
    print(" Minu Distributors B2B System Started Successfully")
    print(" Access URL: http://127.0.0.1:5000")
    print("==================================================")
    app.run(debug=True, port=5000)
