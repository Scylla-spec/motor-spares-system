# Motor Spares Management System (v2.0 Professional Edition)

![Platform](https://img.shields.io/badge/Platform-Windows_10_%2F_11-blue?logo=windows)
![Python](https://img.shields.io/badge/Python-3.11_%2F_3.12_%2F_3.14-blue?logo=python)
![Framework](https://img.shields.io/badge/UI-PySide6_(Qt_6)-green?logo=qt)
![Database](https://img.shields.io/badge/Database-SQLite3-lightgrey?logo=sqlite)
![License](https://img.shields.io/badge/License-Proprietary_Commercial-orange)

An enterprise-grade, offline-first Point of Sale (POS), Inventory Control, Customer Credit, and Procurement Management system built specifically for motor spares retailers, auto parts wholesalers, and automotive service centers.

---

## 🌟 Key Highlights & Commercial Capabilities

### 🛒 Fast-Paced Point of Sale (POS)
- **High-Contrast Touch/Click Stepper UI**: Instant `+` and `−` quantity controls with stock limit warnings.
- **Barcode Scanner Compatible**: Works out-of-the-box with standard USB/Wireless 1D & 2D barcode scanners (keyboard wedge).
- **Multi-Tender Payment Support**: Cash, EcoCash, Credit/Debit Card, and **Pay Later (On Credit)**.
- **Supermarket-Style Thermal Receipt Printing**: Direct hardware ESC/POS printing for **80mm** (standard retail roll) and **58mm** (compact roll) printers with automatic paper cut and cash drawer kick-out.
- **A4 Digital PDF Receipts**: Clean, branded PDF backups generated automatically with shop logo and details.

### 📦 Inventory & Stock Control
- **Automated Stock Tracking**: Strict stock deduction on sale and real-time replenishment on PO receipt.
- **Audit-Logged Stock Adjustments**: Discrepancy management (physical stock counts, damaged, lost items) with mandatory reason logging and admin user attribution.
- **Bulk Excel Importer**: Import hundreds of parts from supplier spreadsheets in seconds with intelligent column auto-mapping and price calculations.
- **Photo & Document OCR Import**: Scan or photograph supplier invoices and price lists with built-in OCR (Tesseract) to ingest new stock without manual typing.
- **Category Price Adjustments**: Perform bulk percentage markups or discounts across entire categories in one click.

### 💳 Customer Debt & "Pay Later" Credit Management
- **Dedicated Credit Desk**: Full ledger tracking for customers taking spares on credit.
- **Settlement & Payment Tracking**: Record partial or full balance payoffs with audit timestamps and automatic customer balance updates.
- **Counter Credit Dockets**: Generates dedicated thermal dockets stamped `Payment Method: Pay Later (Credit) - PENDING` for physical customer signature at the counter.

### 📋 Procurement & Supplier Management
- **Itemized Purchase Orders**: Build POs with an interactive parts picker that automatically pulls supplier cost prices.
- **1-Click "Receive & Stock In"**: Instantly updates parts inventory and records stock-in movements when goods arrive.
- **PDF Purchase Order Export**: Generates professional, branded purchase orders ready to email or WhatsApp to distributors.
- **Low-Stock Replenishment Export**: Automatically filters parts at or below reorder levels for restocking runs.

### 📊 Reports & Visual Analytics
- **Live Business Dashboard**: Real-time sales metrics, inventory value, low-stock alerts, and pending credit totals.
- **Sales Trend Charts**: Interactive visualization showing rising or declining revenue trends over time.
- **Day-End Closeout Summaries**: Cashier shift reconciliation and revenue breakdowns.

### ⚙️ Customizable Branding & Hardware Configuration
- **Shop Branding**: Configure shop name, physical address, phone numbers, tax details, custom receipt footer disclaimer, and logo image.
- **Thermal Printer Setup**: Select from installed Windows printers, choose 80mm/58mm roll width, toggle auto-cut, and test hardware with a single click.

---

## 🏗️ Technical Architecture

```
motor_spares_system/
│
├── main.py                  # Application entry point & Qt event loop
├── database/                # SQLite database manager, schema migrations, and seeding
├── models/                  # Core dataclass domain entities (Part, Sale, CreditOrder, PO, User)
├── managers/                # Business logic & transactional service layer
│   ├── inventory_manager.py # Stock movements, adjustments, catalog search
│   ├── sales_manager.py     # POS checkout, receipt generation, stock deduction
│   ├── credit_manager.py    # Debt tracking, credit orders, customer balances
│   ├── purchase_order_manager.py # PO lifecycles, receiving stock
│   ├── customer_manager.py  # Customer CRM & credit limits
│   ├── supplier_manager.py  # Supplier directory & lead times
│   └── settings_manager.py  # Store branding, thermal printer settings
├── ui/                      # PySide6 UI screens & modern custom widgets
│   ├── pos_screen.py        # 2-column Point of Sale checkout interface
│   ├── credit_screen.py     # Customer credit management & debt payoff
│   ├── inventory_screen.py  # Part inventory, stock adjustments, imports
│   ├── purchase_order_screen.py # PO management & stock receiving
│   ├── settings_screen.py   # Branding & thermal receipt printer setup
│   └── theme.py             # Design tokens, color palettes, custom widgets
├── utils/                   # Shared utility modules
│   ├── thermal_receipt.py   # ESC/POS binary builder & Windows spooler direct printer
│   ├── receipt_generator.py # ReportLab A4 PDF generator
│   ├── excel_importer.py    # Excel parsing & auto-mapping engine
│   └── image_importer.py    # OCR document & invoice scanning engine
└── tests/                   # Full pytest automated test suite (42 unit/integration tests)
```

---

## 💻 System Requirements

| Specification | Minimum | Recommended |
| :--- | :--- | :--- |
| **Operating System** | Windows 10 (64-bit) | Windows 11 (64-bit) |
| **Processor** | Intel Core i3 / AMD Ryzen 3 (2.0 GHz) | Intel Core i5 / AMD Ryzen 5 or higher |
| **Memory (RAM)** | 4 GB | 8 GB or more |
| **Storage** | 500 MB free disk space | SSD with 2 GB free disk space |
| **Display Resolution** | 1366 × 768 | 1920 × 1080 (Full HD) |
| **Receipt Printer** | None (PDF mode) | 80mm or 58mm Thermal USB / Network Printer |
| **Barcode Scanner** | Optional | Standard USB 1D / 2D Scanner (Keyboard Wedge) |

---

## 🚀 Installation & Quick Start

### 1. Prerequisites
Ensure **Python 3.11+** is installed on your Windows system and added to your system `PATH`.

### 2. Clone the Repository
```bash
git clone https://github.com/Scylla-spec/motor-spares-system.git
cd motor_spares_system
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Launch the Application
```bash
python main.py
```

### 5. Default Credentials
On first launch, the database is automatically created and seeded with default administrative credentials:
- **Username**: `admin`
- **Password**: `admin123`

*(Note: Change this password immediately under **User Management** upon initial deployment).*

---

## 🖨️ Thermal Receipt Printer Setup

1. Connect your thermal receipt printer via USB or Network and install its Windows driver.
2. Launch the application and log in as an **Admin**.
3. Open **Settings** from the sidebar.
4. Scroll to **Receipt Machine (Thermal ESC/POS)**:
   - Select your printer from the **Printer Device** dropdown.
   - Choose your paper width: **80mm (Standard Supermarket Roll)** or **58mm (Compact Roll)**.
   - Check **Auto-Print** and **Paper Cut**.
5. Click **🖨 Test Print Receipt** to verify connection, alignment, and cutting.
6. Click **Save All Settings**.

---

## 🧪 Running Automated Tests

The application includes a comprehensive automated test suite covering authentication, stock deduction, credit handling, numbering sequences, and reports:

```bash
python -m pytest tests -v
```

All 42 test suites must pass before deploying or packaging.

---

## 📦 Packaging Standalone Windows Executable (.exe)

To bundle the application into a standalone `.exe` that does not require Python on customer computers:

```bash
pip install pyinstaller
pyinstaller motor_spares.spec
```

The resulting standalone executable will be located in the `dist/` directory.

---

## 📖 Complete Documentation Suite

- [**Cashier & User Operations Manual**](docs/USER_MANUAL.md) — Comprehensive guide on POS, Credit, Inventory, and PO workflows.
- [**Hardware Compatibility Guide**](docs/HARDWARE_GUIDE.md) — Printer, scanner, and cash drawer setup.
- [**Commercial Product Feature Sheet**](docs/COMMERCIAL_FEATURE_SHEET.md) — Feature breakdown and value proposition for sales presentations.
