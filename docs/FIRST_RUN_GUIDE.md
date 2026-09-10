# 🚀 Motor Spares System — First-Run & Onboarding Guide

Welcome to **Motor Spares System**! This guide is designed for shop owners setting up the system for the first time. Follow these quick, visual steps to get your store up, branded, and ready to ring up sales in under 10 minutes.

---

## ⚡ Setup Checklist
- [ ] **Step 1:** Log in and change your default admin password.
- [ ] **Step 2:** Customize your shop branding, phone number & WhatsApp message.
- [ ] **Step 3:** Add your first inventory parts.
- [ ] **Step 4:** Create cashier accounts for your staff.
- [ ] **Step 5:** Ring up your first test sale!

---

## Step 1: Initial Login & Change Default Password 🔐

> [!CAUTION]
> **URGENT SECURITY STEP**: The system ships with default credentials (`admin` / `admin123`). You **must** change this password before putting the computer on the sales counter. Anyone with the default password can view store profits and delete data!

1. Double-click the **Motor Spares System** desktop icon.
2. At the login window, enter:
   - **Username**: `admin`
   - **Password**: `admin123`
3. Click **Log In**.

```
┌────────────────────────────────────────┐
│        Motor Spares System             │
│                                        │
│  Username: [ admin                   ] │
│  Password: [ ••••••••                ] │
│                                        │
│            [  LOG IN ➔  ]              │
└────────────────────────────────────────┘
```

4. Immediately navigate to **Users** (or **Settings → User Management**) in the left sidebar.
5. Click **Change Password** next to the `admin` user.
6. Enter a secure new password and click **Save Password**.

---

## Step 2: Configure Your Shop Branding & WhatsApp 🏢

Ensure your receipts and invoices show your store name, physical address, and contact details instead of generic text.

1. Click **Settings** in the left sidebar.
2. In the **Store Profile & Identity** tab, fill in:
   - **Store Name**: e.g. *Precision Motor Spares & Bearings*
   - **Address**: e.g. *104 Commercial Rd, Bay 4*
   - **Phone Number**: e.g. *+263 77 123 4567*
   - **Receipt Footer Note**: e.g. *Thank you for your business! No cash refunds on electrical parts.*
3. In the **WhatsApp & Messages** section:
   - Enter your customer support WhatsApp number.
   - Customize the automated debt reminder text template.
4. Click **💾 Save Store Profile**.

```
┌────────────────────────────────────────────────────────┐
│ Store Profile Settings                                 │
├────────────────────────────────────────────────────────┤
│ Shop Name:     [ Precision Motor Spares              ] │
│ Phone Number:  [ +263 77 123 4567                    ] │
│ Address:       [ 104 Commercial Rd, Harare           ] │
│ Receipt Note:  [ Electrical parts are non-refundable ] │
│                                                        │
│                    [ 💾 Save Profile ]                 │
└────────────────────────────────────────────────────────┘
```

---

## Step 3: Add Your First Spares to Inventory 📦

Before your cashiers can sell, add a few items to your catalog.

1. Click **Inventory** in the left sidebar.
2. Click the orange **＋ Add New Part** button in the top right.
3. Complete the quick form:
   - **Part Number / SKU**: e.g. `BP-COR-001` (or scan the box barcode with your scanner)
   - **Part Name**: e.g. *Front Brake Pads - Toyota Corolla (2007-2014)*
   - **Category**: e.g. *Braking System*
   - **Quantity on Hand**: e.g. `12`
   - **Cost Price**: e.g. `$14.00` *(Visible to Admin only)*
   - **Selling Price**: e.g. `$25.00`
   - **Min Reorder Level**: e.g. `3` *(System alerts you when stock drops below this)*
4. Click **Save Part**.

```
┌────────────────────────────────────────────────────────┐
│ Add New Part                                           │
├────────────────────────────────────────────────────────┤
│ Part Number:   [ BP-COR-001             ] [Scan 📷]    │
│ Description:   [ Front Brake Pads - Corolla 2007-14  ] │
│ Category:      [ Braking System        ▼]              │
│ Cost Price:    [ $14.00  ]  Selling Price: [ $25.00  ] │
│ Stock on Hand: [ 12      ]  Min Alert Lvl: [ 3       ] │
│                                                        │
│                  [ Cancel ]  [ 💾 Save Part ]          │
└────────────────────────────────────────────────────────┘
```

> [!TIP]
> **Have hundreds of parts in a spreadsheet?** Click **📥 Bulk Import Excel** on the Inventory screen to upload your entire supplier price list in seconds!

---

## Step 4: Add Cashier Accounts for Your Staff 👥

Keep administrative control over store profits while giving counter staff fast checkout access.

1. Click **Users** (or **Settings → User Management**).
2. Click **＋ Add New User**.
3. Fill in:
   - **Username**: e.g. `tendai`
   - **Password**: Create a temporary password for the cashier.
   - **Role**: Select **Cashier**.
4. Click **Create User**.

```
┌────────────────────────────────────────────────────────┐
│ Role Permissions Quick Comparison                      │
├─────────────────────────┬───────────────┬──────────────┤
│ Capability              │ Admin (Owner) │ Cashier      │
├─────────────────────────┼───────────────┼──────────────┤
│ Make Sales & POS Cart   │      ✅       │      ✅      │
│ Reprint Receipts        │      ✅       │      ✅      │
│ View Profit Margins     │      ✅       │      ❌      │
│ Adjust Stock Inventory  │      ✅       │      ❌      │
│ View Financial Reports  │      ✅       │      ❌      │
│ Modify Shop Settings    │      ✅       │      ❌      │
└─────────────────────────┴───────────────┴──────────────┘
```

---

## Step 5: Make Your First Counter Sale 🛒

You are ready for business! Test your checkout counter:

1. Click **Point of Sale (POS)** in the sidebar.
2. In the search box, type the part name or scan the barcode.
3. Click the part or press `Enter` to add it to the cart.
4. Adjust quantity using the `+` or `−` buttons.
5. Select the payment method:
   - **Cash**: Enter amount tendered; system calculates change.
   - **Card / EcoCash**: Instant authorization.
   - **Pay Later (Credit)**: Assigns sale to a customer credit ledger.
6. Click **Complete Sale & Print Receipt**.
7. The thermal printer prints the docket and your cash drawer pops open!

---

## 🆘 Need Help?
- Refer to the full [User Operations Manual](USER_MANUAL.md) for detailed credit settlement and purchase order instructions.
- Check the [Hardware Setup Guide](HARDWARE_GUIDE.md) if your thermal receipt printer or barcode scanner needs troubleshooting.
