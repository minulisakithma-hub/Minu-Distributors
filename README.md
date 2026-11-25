# Minu Distributors - B2B Chocolate Distribution System
**Authorized B2B Distributor for Ceylon Biscuits Limited (CBL)**

A complete, clean, and lightweight B2B Web Application built for Information Technology students.

---

## 🍫 Project Overview
- **Domain:** Authorized B2B Chocolate Confectionery Distribution (Sourcing from CBL: Ritzbury & Tiara).
- **Target Audience:** Local Retail Grocery Shop Owners, Store Warehouse Managers, and Distributors.
- **Tech Stack:**
  - **Backend:** Python (Flask Web Framework)
  - **Database:** SQLite3 (`sqlite3` standard library)
  - **Frontend:** HTML5, CSS3 (Custom Dark Chocolate Theme), Vanilla JavaScript
  - **Security:** Hashed passwords (`werkzeug.security`) and session-based authentication

---

## 🎨 Theme Palette
- **Deep Dark Chocolate:** `#2B1B17` (Page Background)
- **Rich Dark Brown:** `#3D2721` (Containers & Cards)
- **Caramel Brown:** `#C87D55` (Primary Buttons & CTAs)
- **Warm Gold:** `#D4AF37` (Borders, Accents & Badges)
- **Cream / Light Beige:** `#E6D5C3` (High Contrast Text)

---

## 🚀 Quick Start Guide (VS Code)

### 1. Prerequisites
Ensure you have Python installed. Check via terminal:
```bash
python --version
```

### 2. Install Flask
In your terminal, navigate to the project directory and run:
```bash
pip install -r requirements.txt
# Or simply:
pip install flask
```

### 3. Run the Application
```bash
python app.py
```
Open your web browser and visit: **`http://127.0.0.1:5000`**

---

## 👥 Dynamic Role Testing Workflow (No Hardcoded Accounts)
Because the system relies entirely on dynamic database storage, test the system with this natural workflow:

1. **Step 1 - Register System Administrator:**
   - Go to `/register`
   - Role: **System Administrator**
   - Username: `admin` | Password: `yourpassword`
   - *Status is instantly Active.*

2. **Step 2 - Register Store Manager:**
   - Go to `/register`
   - Role: **Store Manager**
   - Username: `manager` | Password: `yourpassword`
   - *Status is instantly Active.*

3. **Step 3 - Register Retailer (Shop Owner):**
   - Go to `/register`
   - Role: **Retailer**
   - Fill in: Full Name, Shop Name (e.g. *Perera Super City*), Phone, Address.
   - *Status is set to Pending Approval.*

4. **Step 4 - Admin Approval:**
   - Log in as the Admin (`/login`).
   - In `/admin`, review the newly registered retailer under "Retailer Account Approvals".
   - Click **Approve & Activate**.

5. **Step 5 - Retailer Orders CBL Chocolates:**
   - Log in as the Retailer (`/login`).
   - Select box quantities using the **`+`** / **`-`** controls.
   - Choose payment terms (*Cash on Delivery* or *30-Day Corporate Credit*).
   - Submit Order. The order appears as **Pending**.

6. **Step 6 - Store Manager Processes Order & Checks Expiry:**
   - Log in as Store Manager (`/login`).
   - Under **Pending Orders**, click **Approve** (this automatically reduces warehouse stock).
   - Under **Manage Product Catalog**, add new CBL items or adjust pricing.
   - Under **Expiry Management**, review batch expiry alerts (Safe, Approaching, or Expired) and add new batches with expiry dates.
   - Under **Daily Stocks** and **Sales Reports**, review inventory levels and revenue generated.
