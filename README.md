# Cafe Billing System (Python + Flask + SQLite)

A beginner-friendly, structured cafe billing project for VS Code.

## Features
- Dashboard with customer, product, bill and sales totals
- Customer management: add, view, edit and delete
- Menu/product management: add and remove products
- Billing with quantities, optional 5% tax, and automatic totals
- Printable invoice and bill history/search
- SQLite database is created automatically; sample menu products are seeded on first run

## Requirements
- Python 3.10 or newer
- VS Code (recommended)

## Run on Windows / VS Code
1. Extract the ZIP file.
2. In VS Code, choose **File → Open Folder** and open the `CafeBillingSystem` folder (the folder that contains `app.py` and `requirements.txt`).
3. Open **Terminal → New Terminal**. Make sure the terminal is inside that folder.
4. Create a virtual environment (recommended):
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
   If PowerShell blocks activation, you can skip activation and run the pip command using `python -m pip`.
5. Install the dependency:
   ```powershell
   python -m pip install -r requirements.txt
   ```
6. Start the application:
   ```powershell
   python app.py
   ```
7. Open the local URL printed in the terminal, usually `http://127.0.0.1:5000`.
8. To stop the server, click the terminal and press `Ctrl+C`.

## Important
- Keep the terminal open while using the site.
- The database file `cafe_billing.db` is created in the project folder on first start.
- Product image field accepts an image URL or a path; this starter version keeps product management simple and does not upload image files.
- Change `app.secret_key` before deploying this project publicly. This is a local educational project, not a hardened production system.
