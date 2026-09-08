# Motor Spares Management System — User & Operations Manual

This manual provides complete operating instructions for cashiers, inventory managers, and store owners operating the **Motor Spares Management System**.

---

## Table of Contents
1. [System Access & Security](#1-system-access--security)
2. [Dashboard Overview](#2-dashboard-overview)
3. [Point of Sale (POS) Operations](#3-point-of-sale-pos-operations)
4. [Pay Later & Customer Credit Management](#4-pay-later--customer-credit-management)
5. [Inventory & Stock Management](#5-inventory--stock-management)
6. [Procurement & Purchase Orders](#6-procurement--purchase-orders)
7. [Reports & Business Analytics](#7-reports--business-analytics)
8. [Settings, Branding & Receipt Printers](#8-settings-branding--receipt-printers)
9. [Data Backup & Maintenance SOP](#9-data-backup--maintenance-sop)

---

## 1. System Access & Security

### 1.1 Logging In
1. Double-click the application icon on your desktop.
2. Enter your assigned **Username** and **Password**.
3. Click **Login**.

### 1.2 User Roles & Access Levels
The system enforces strict role-based access control:
- **Admin**: Full access to all modules, including user account management, cost prices, shop branding, thermal printer settings, and stock adjustments.
- **Cashier**: Restricted to Point of Sale (POS), customer search, and view-only catalog access. Cannot delete parts or change cost margins.

### 1.3 Account Lockout Protection
To protect against unauthorized password guessing:
- If a user enters an incorrect password **5 consecutive times**, their account is automatically locked for **15 minutes**.
- An Administrator can unlock accounts immediately under **User Management**.

---

## 2. Dashboard Overview

The dashboard serves as the central command center for the store manager:
- **Total Revenue**: Cumulative revenue processed through the system.
- **Total Inventory Value**: Total cost and selling valuation of all parts currently in stock.
- **Low Stock Alerts**: Number of items that have reached or fallen below their reorder threshold.
- **Outstanding Credit**: Total unpaid customer debt currently in circulation.
- **Recent Activity Table**: Real-time log of recent transactions, stock adjustments, and orders.

---

## 3. Point of Sale (POS) Operations

The POS screen is optimized for rapid counter sales during peak hours.

### 3.1 Searching and Adding Parts
1. Place cursor in the **Scan barcode or search...** bar.
2. Search by:
   - **Barcode / Part Number** (e.g., `AC3032`, `RH7001`)
   - **Part Name** (e.g., `Brake Pad`, `Air Filter`)
   - **Vehicle Compatibility** (e.g., `Toyota D4D`, `Nissan Sunny`)
3. Review on-hand stock and retail price.
4. Click **+ Add** on the row or scan the barcode to add the item directly to the **Active Order Cart**.

### 3.2 Adjusting Cart Quantities
- Use the **`+`** or **`−`** buttons on the quantity stepper in the cart to increment or decrement units.
- The system automatically checks inventory and blocks cashier entry if requested quantity exceeds available stock.
- Click the **🗑 (Trash)** button to remove an item from the cart.

### 3.3 Completing Checkout
1. Select the **Customer**:
   - For casual counter sales, leave as **Walk-in**.
   - For repeat accounts, select the customer's name from the dropdown.
2. Select the **Payment Method**:
   - **Cash**: Customer pays cash on the spot.
   - **EcoCash / Mobile Money**: Customer pays via mobile transfer.
   - **Card**: POS swipe/terminal payment.
   - **Pay Later (On Credit)**: Customer takes goods on store debt (see Section 4).
3. Click **Complete Sale**:
   - Inventory is immediately deducted from the database.
   - The thermal receipt machine automatically prints and cuts the supermarket-style receipt.
   - A digital PDF receipt is archived in the `receipts/` directory.

---

## 4. Pay Later & Customer Credit Management

Motor spares businesses frequently extend credit to mechanics, fleet owners, and repeat commercial customers. This module tracks and recovers customer debt.

### 4.1 Issuing Goods on Credit at POS
1. Add parts to the cart as normal.
2. Select or enter the customer's name.
3. Set **Payment Method** to `Pay Later (On Credit)`.
4. Click **Complete Sale**.
5. The system:
   - Deducts stock immediately.
   - Creates a pending Credit Order record.
   - Increases the customer's outstanding balance.
   - Prints a counter credit docket stamped `Pay Later (Credit) - PENDING` for the customer to sign.

### 4.2 Managing Credit Accounts
Open the **Pay Later / On Credit** screen:
- **Pending Orders Tab**: Shows all active unpaid credit transactions, order date, customer contact, and total due.
- **Customer Ledger**: View total debt per customer and individual transaction histories.

### 4.3 Recording Debt Settlements
When a customer comes in to pay off their account:
1. Locate the customer or Credit Order in the **Credit** screen.
2. Click **Mark as Paid** or enter the settlement amount.
3. Select settlement method (Cash, EcoCash, Card).
4. Click **Confirm Payment**:
   - The credit order status changes from `Pending` to `Paid`.
   - The customer's credit balance is reduced accordingly.
   - An audit receipt is generated for the customer.

---

## 5. Inventory & Stock Management

### 5.1 Adding a New Part
1. Open the **Inventory** tab.
2. Click **+ Add New Part**.
3. Fill in required details:
   - **Part Number**: Unique manufacturer or internal code (e.g. `BP-1029`).
   - **Part Name**: Clear description (e.g. `FRONT BRAKE PADS COROLLA`).
   - **Category**: Engine, Braking, Electrical, Suspension, etc.
   - **Compatible Vehicles**: Vehicles this part fits (e.g. `Toyota Corolla 2008-2015`).
   - **Cost Price**: What the store paid the supplier.
   - **Selling Price**: Counter retail price.
   - **Quantity on Hand**: Initial stock count.
   - **Reorder Level**: Threshold for automatic low-stock warnings (e.g. 2 units).
4. Click **Save Part**.

### 5.2 Stock Adjustments (Stock-Take Discrepancies)
When a physical stock count reveals a discrepancy (damaged goods, found stock, or stock shrinkage):
1. Select the part in the inventory table.
2. Click **Adjust Stock**.
3. Enter the quantity delta (e.g. `+3` for found stock, `-1` for broken item).
4. **Enter a Mandatory Reason** (e.g. "Physical count variance - June 2026").
5. Click **Apply Adjustment**:
   - System validates that stock cannot go negative.
   - Logs an immutable record in the `AuditLog` table with user timestamp.

### 5.3 Bulk Excel Import
1. Click **Import from Excel**.
2. Select your supplier spreadsheet (`.xlsx` or `.xls`).
3. Use the mapping dialog to align spreadsheet columns with system fields.
4. Review preview rows and click **Commit Import**.

### 5.4 Photograph & OCR Invoice Import
1. Click **Import from Photo / Image**.
2. Select an image (`.png`, `.jpg`, `.jpeg`) of a typed supplier invoice or stock list.
3. Built-in OCR scans the document and presents recognized rows in an editable table.
4. Verify numbers, correct any blurry fields, and click **Commit to Inventory**.

---

## 6. Procurement & Purchase Orders

### 6.1 Creating a Purchase Order
1. Open the **Purchase Orders** tab.
2. Click **+ New Purchase Order**.
3. Select the **Supplier**.
4. In the itemized picker, choose the parts you wish to order and specify quantities.
5. Review the total calculated purchase order cost.
6. Click **Generate Purchase Order**:
   - Generates an official numbered PO (`PO-YYYYMMDD-NNNN`).
   - Saves a professional PDF document ready to send to the distributor.

### 6.2 Receiving Goods (1-Click Stock-In)
When the delivery arrives from the supplier:
1. Open **Purchase Orders** and locate the pending order.
2. Verify physical items against the PO items list.
3. Click **Receive Stock**:
   - All part quantities are automatically credited to inventory in a single transaction.
   - Records official `IN` stock movement logs.
   - Marks the PO status as `Received`.

---

## 7. Reports & Business Analytics

### 7.1 Low Stock Alerts & Reorder Lists
- The system automatically flags any part where current stock ≤ reorder level.
- Click **Export Reorder List** to produce a ready-to-use restocking sheet to take on supplier buying trips.

### 7.2 Sales Performance & Revenue Trends
- View interactive charts showing rising and declining product sales over daily, weekly, and monthly periods.
- Identify top-selling fast movers versus slow-moving capital.

---

## 8. Settings, Branding & Receipt Printers

### 8.1 Shop Branding
Under **Settings**:
- Update **Shop Name**, **Physical Address**, and **Telephone Numbers**.
- Upload your **Store Logo** (appears on top of PDF receipts and invoices).
- Customize your **Receipt Footer Disclaimer** (e.g. "Goods once sold cannot be returned without receipt").

### 8.2 Thermal Receipt Machine Configuration
1. Select your thermal printer from the **Printer Device** list.
2. Set **Paper Width**:
   - **80mm**: Standard wide supermarket receipt roll (48 columns).
   - **58mm**: Small compact POS roll (32 columns).
3. Ensure **Auto-Print** and **Paper Cut** checkboxes are enabled.
4. Click **🖨 Test Print Receipt** to verify.
5. Click **Save All Settings**.

---

## 9. Data Backup & Maintenance SOP

### 9.1 Database Safety
The system uses SQLite with Write-Ahead Logging (WAL) for bulletproof reliability. Data is saved immediately upon every click.

### 9.2 Daily Backup Procedure
1. Open **Settings** or the local application directory.
2. Copy the `database/` folder and `motor_spares.db` file to:
   - A dedicated external USB flash drive.
   - An offsite secure cloud folder (e.g. Google Drive, OneDrive, or Dropbox).
3. In case of computer theft or hard drive failure, simply install the app on a new PC, paste the `motor_spares.db` file into the `database/` folder, and the entire store history is restored in 10 seconds.
