# Privacy Policy

**Motor Spares Management System — Privacy Policy**  
*Version 2.4 | Last Updated: September 2026*

---

## 1. Introduction

Motor Spares Solutions Ltd ("we", "our", "the Company") respects the privacy of the businesses and individuals who use the **Motor Spares Management System** (the "Software"). This policy explains what data the Software collects, how it is stored, and your rights as a system operator.

---

## 2. What Data Is Collected

The Software operates entirely **locally on your hardware**. The following data is created and stored on your premises:

- **Customer information**: Names, phone numbers, and credit account details entered by your staff.
- **Transaction records**: Sales invoices, stock adjustments, purchase orders, and payment history.
- **Inventory data**: Part numbers, stock quantities, pricing, and supplier details.
- **User accounts**: Staff usernames and hashed passwords (no plain-text passwords are ever stored).
- **Audit logs**: Records of who made changes to the system, including timestamps.

---

## 3. Data Storage & Security

- All data is stored in an **SQLite 3 database file** located on your local machine. No data is transmitted to external servers.
- Passwords are stored using **one-way cryptographic hashing**. Even the System Administrator cannot view a user's password in plain text.
- The database uses **SQLite WAL (Write-Ahead Logging)** to protect against data corruption during power cuts.
- You are solely responsible for physical and network security of the machine running the Software.

---

## 4. No Third-Party Sharing

The Software does **not** transmit your data to any third party, cloud service, or remote server. All business records remain under your exclusive control at all times.

The optional WhatsApp messaging feature initiates a message draft in your local WhatsApp client — no data is sent to any server operated by Motor Spares Solutions Ltd.

---

## 5. Data Retention

Data is retained indefinitely within the database until you explicitly delete it or uninstall the Software. We recommend performing regular backups using the built-in backup tool under **Settings → System Info → 1-Click DB Backup**.

---

## 6. Your Rights

As the business owner and system administrator, you have full rights to:
- **Access** all records stored in the system.
- **Correct** any inaccurate information.
- **Delete** customer or staff records at any time.
- **Export** data using the built-in CSV export functionality.

---

## 7. Changes to This Policy

We may update this policy with each new version of the Software. The policy version is displayed in the Software under **Settings → System Info → About & Legal**.

---

## 8. Contact

For questions regarding this Privacy Policy, contact:

**Motor Spares Solutions Ltd**  
Email: support@motorspares.app

---

*Motor Spares Management System — Built with care for Zimbabwean motor spares traders.*
