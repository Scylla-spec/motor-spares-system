# Hardware Compatibility & Peripheral Setup Guide

This guide details recommended hardware, compatibility criteria, and step-by-step setup instructions for POS peripherals used with the **Motor Spares Management System**.

---

## 1. Supported Peripherals Overview

| Hardware Device | Recommended Spec | Connection Types | Compatibility Level |
| :--- | :--- | :--- | :--- |
| **Receipt Printer** | 80mm or 58mm Thermal Printer (ESC/POS) | USB, Ethernet (LAN), Bluetooth, Wi-Fi | 100% Native ESC/POS Spooler Direct |
| **Barcode Scanner** | 1D & 2D Handheld Laser / CCD Scanner | USB, 2.4G Wireless Dongle, Bluetooth | 100% Plug-and-Play (HID Keyboard Wedge) |
| **Cash Drawer** | Heavy Duty Metal Cash Drawer (4-bill / 8-coin) | RJ11 / RJ12 connection to receipt printer | Automatic pulse kick-out via printer |
| **Computer / PC** | Windows 10 or 11 (64-bit), 4GB+ RAM | Standard Desktop, All-in-One, or Laptop | Native Desktop Application |

---

## 2. Thermal Receipt Printer Setup

The system integrates directly with Windows print spooling using direct ESC/POS hardware commands. It does not require proprietary manufacturer SDKs and works with all major brands.

### 2.1 Compatible Printer Brands
- **Epson**: TM-T20, TM-T88 series, TM-T82
- **Xprinter**: XP-58, XP-80, XP-N160, XP-Q90EC
- **Bixolon**: SRP-330, SRP-350 series
- **Star Micronics**: TSP100, TSP650 series
- **Rongta**: RP80, RP326, RP58
- **GOOJPRT & Generic**: Any standard POS-58 / POS-80 USB receipt printer

### 2.2 Paper Roll Specifications
- **80mm Rolls (Supermarket Standard - Recommended)**:
  - Width: 80mm (3 1/8")
  - Diameter: 70mm to 80mm
  - Character Capacity: 48 columns
  - Ideal for busy stores with long part descriptions.
- **58mm Rolls (Compact)**:
  - Width: 58mm (2 1/4")
  - Diameter: 40mm to 50mm
  - Character Capacity: 32 columns

### 2.3 Installation Steps in Windows
1. Plug the printer power cable and connect the USB cable to your computer.
2. Turn the printer power ON.
3. Install the manufacturer driver provided on the USB/CD or download from the brand website.
   - *Alternative for Generic Printers*: In Windows **Printers & Scanners**, add a printer manually using the built-in Windows driver: **Generic -> Generic / Text Only**.
4. Print a Windows Test Page to ensure the printer communicates with Windows.

### 2.4 Activating Printer in the Software
1. Open the Motor Spares software and log in as **Admin**.
2. Click **Settings** in the left sidebar.
3. Scroll down to **Receipt Machine (Thermal ESC/POS)**:
   - Click the **Printer Device** dropdown and select your printer name.
   - Select your paper width (**80mm** or **58mm**).
   - Check **Auto-Print** (prints immediately upon completing a sale).
   - Check **Paper Cut** (automatically fires the paper cutter).
4. Click **🖨 Test Print Receipt**:
   - The printer will feed a sample supermarket receipt and cut the roll.
5. Click **Save All Settings**.

---

## 3. Barcode Scanner Setup

The system uses standard **Keyboard Wedge Mode (HID)**. When a barcode is scanned, the scanner types the part number or code into whichever input field is focused, followed by an automatic `Enter` key.

### 3.1 Recommended Scanner Types
- **1D Laser Scanners**: Ideal for standard UPC, EAN-13, Code 128, and Code 39 barcodes printed on auto spare boxes.
- **2D Image Scanners**: Reads both standard barcodes and QR codes from spare part labels, mobile screens, or supplier packing slips.

### 3.2 Configuration
Most USB barcode scanners require zero software setup:
1. Plug the scanner into any available USB port.
2. Windows will automatically recognize it as an input device.
3. Open Notepad and scan a spare part barcode. The code should appear followed by a new line.
4. If the scanner does not send an `Enter` after each scan, scan the **"Add Enter / Carriage Return"** barcode from your scanner's user manual.

### 3.3 Using with the POS Screen
- Simply click in the search box on the POS screen (or leave it in default focus) and scan any part box.
- The system immediately filters to that part and allows you to add it directly to the cart.

---

## 4. Cash Drawer Setup

### 4.1 Connection
1. Connect the RJ11 or RJ12 telephone-style cable from the back of the cash drawer to the **DK (Drawer Kick)** port on the back of your thermal receipt printer.
2. Do **not** plug the cash drawer directly into a computer telephone port or Ethernet port.

### 4.2 How It Opens
- Every time a sale is completed, the software transmits the ESC/POS drawer pulse command (`ESC p 0 25 250`) to the thermal printer.
- The receipt printer triggers an electrical pulse down the RJ11 cable that springs the cash drawer open automatically for cash transactions.

---

## 5. Troubleshooting Hardware Issues

| Problem | Cause | Solution |
| :--- | :--- | :--- |
| **Printer does not appear in dropdown** | Printer was plugged in after app launched | Click the **⟳ Refresh** button next to the printer dropdown in Settings. |
| **Test print says "Success" but nothing prints** | Printer driver port mismatch or paper empty | Verify printer has paper roll inserted right-side up; check Windows print queue for stuck jobs. |
| **Receipt text is misaligned or cut off on the right** | 80mm profile selected for a 58mm printer | In Settings, change **Paper Width** from 80mm to **58mm** and click Save. |
| **Paper does not cut automatically** | Printer model lacks an internal auto-cutter | In Settings, uncheck **Paper Cut**. The software will feed blank lines so paper can be torn manually. |
| **Barcode scanner beeps but nothing types** | Scanner not in HID USB Keyboard mode | Scan the "Reset to USB Factory Default" barcode in the scanner manufacturer manual. |
