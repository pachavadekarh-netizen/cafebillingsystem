from flask import Flask, render_template, request, redirect, url_for, flash, make_response
import sqlite3, os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'cafe_billing.db')
app = Flask(__name__)
app.secret_key = 'change-this-secret-key'


def get_db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys = ON')
    return con


def init_db():
    with get_db() as con:
        con.executescript('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, phone TEXT NOT NULL UNIQUE, email TEXT DEFAULT '', address TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, category TEXT DEFAULT 'General', price REAL NOT NULL CHECK(price >= 0),
            image TEXT DEFAULT '' , active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER,
            customer_name TEXT NOT NULL, customer_phone TEXT DEFAULT '',
            subtotal REAL NOT NULL, tax REAL NOT NULL, total REAL NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS bill_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, bill_id INTEGER NOT NULL,
            product_id INTEGER, product_name TEXT NOT NULL, price REAL NOT NULL,
            quantity INTEGER NOT NULL, line_total REAL NOT NULL,
            FOREIGN KEY(bill_id) REFERENCES bills(id) ON DELETE CASCADE,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE SET NULL
        );
        ''')
        count = con.execute('SELECT COUNT(*) FROM products').fetchone()[0]
        if count == 0:
            con.executemany('INSERT INTO products(name,category,price,image) VALUES(?,?,?,?)', [
                ('Masala Chai','Hot Drinks',20,''), ('Cold Coffee','Cold Drinks',90,''),
                ('Veg Sandwich','Snacks',80,''), ('French Fries','Snacks',100,''),
                ('Veg Burger','Meals',120,''), ('Chocolate Brownie','Desserts',75,'')
            ])

@app.route('/')
def dashboard():
    with get_db() as con:
        stats = {
            'customers': con.execute('SELECT COUNT(*) FROM customers').fetchone()[0],
            'products': con.execute('SELECT COUNT(*) FROM products WHERE active=1').fetchone()[0],
            'bills': con.execute('SELECT COUNT(*) FROM bills').fetchone()[0],
            'sales': con.execute('SELECT COALESCE(SUM(total),0) FROM bills').fetchone()[0]
        }
        recent = con.execute('SELECT * FROM bills ORDER BY id DESC LIMIT 6').fetchall()
    return render_template('dashboard.html', stats=stats, recent=recent)

@app.route('/customers', methods=['GET','POST'])
def customers():
    if request.method == 'POST':
        name = request.form.get('name','').strip(); phone = request.form.get('phone','').strip()
        if not name or not phone:
            flash('Customer name and phone are required.', 'error')
        else:
            try:
                with get_db() as con:
                    con.execute('INSERT INTO customers(name,phone,email,address) VALUES(?,?,?,?)',
                                (name, phone, request.form.get('email','').strip(), request.form.get('address','').strip()))
                flash('Customer added successfully.', 'success')
                return redirect(url_for('customers'))
            except sqlite3.IntegrityError:
                flash('That phone number is already registered.', 'error')
    with get_db() as con:
        rows = con.execute('SELECT * FROM customers ORDER BY name').fetchall()
    return render_template('customers.html', customers=rows)

@app.route('/customers/<int:customer_id>/edit', methods=['GET','POST'])
def edit_customer(customer_id):
    with get_db() as con:
        customer = con.execute('SELECT * FROM customers WHERE id=?',(customer_id,)).fetchone()
        if not customer:
            flash('Customer not found.', 'error'); return redirect(url_for('customers'))
        if request.method == 'POST':
            name=request.form.get('name','').strip(); phone=request.form.get('phone','').strip()
            if not name or not phone:
                flash('Name and phone are required.', 'error')
            else:
                try:
                    con.execute('UPDATE customers SET name=?,phone=?,email=?,address=? WHERE id=?',
                                (name,phone,request.form.get('email','').strip(),request.form.get('address','').strip(),customer_id))
                    flash('Customer updated.', 'success'); return redirect(url_for('customers'))
                except sqlite3.IntegrityError:
                    flash('That phone number is used by another customer.', 'error')
    return render_template('customer_edit.html', customer=customer)

@app.route('/customers/<int:customer_id>/delete', methods=['POST'])
def delete_customer(customer_id):
    with get_db() as con: con.execute('DELETE FROM customers WHERE id=?',(customer_id,))
    flash('Customer deleted.', 'success'); return redirect(url_for('customers'))

@app.route('/products', methods=['GET','POST'])
def products():
    if request.method == 'POST':
        name=request.form.get('name','').strip(); category=request.form.get('category','General').strip()
        try: price=float(request.form.get('price','0'))
        except ValueError: price=-1
        if not name or price < 0: flash('Enter a product name and a valid non-negative price.', 'error')
        else:
            with get_db() as con:
                con.execute('INSERT INTO products(name,category,price,image) VALUES(?,?,?,?)',
                            (name,category or 'General',price,request.form.get('image','').strip()))
            flash('Product added.', 'success'); return redirect(url_for('products'))
    with get_db() as con: rows=con.execute('SELECT * FROM products WHERE active=1 ORDER BY category,name').fetchall()
    return render_template('products.html', products=rows)

@app.route('/products/<int:product_id>/delete', methods=['POST'])
def delete_product(product_id):
    with get_db() as con: con.execute('UPDATE products SET active=0 WHERE id=?',(product_id,))
    flash('Product removed from the menu.', 'success'); return redirect(url_for('products'))

@app.route('/billing', methods=['GET','POST'])
def billing():
    with get_db() as con:
        customer_rows=con.execute('SELECT * FROM customers ORDER BY name').fetchall()
        product_rows=con.execute('SELECT * FROM products WHERE active=1 ORDER BY category,name').fetchall()
        if request.method == 'POST':
            customer_id=request.form.get('customer_id') or None
            customer_name=request.form.get('walkin_name','').strip() or 'Walk-in Customer'
            customer_phone=''
            if customer_id:
                c=con.execute('SELECT * FROM customers WHERE id=?',(customer_id,)).fetchone()
                if not c: flash('Selected customer was not found.', 'error'); return redirect(url_for('billing'))
                customer_name=c['name']; customer_phone=c['phone']
            items=[]; subtotal=0.0
            for p in product_rows:
                try: qty=int(request.form.get(f"qty_{p['id']}",'0'))
                except ValueError: qty=0
                if qty > 0:
                    line=round(p['price']*qty,2); subtotal += line
                    items.append((p['id'],p['name'],p['price'],qty,line))
            if not items:
                flash('Choose at least one product quantity.', 'error'); return redirect(url_for('billing'))
            subtotal=round(subtotal,2); tax_rate=5.0 if request.form.get('include_tax') == 'yes' else 0.0
            tax=round(subtotal*tax_rate/100,2); total=round(subtotal+tax,2)
            cur=con.execute('INSERT INTO bills(customer_id,customer_name,customer_phone,subtotal,tax,total,created_at) VALUES(?,?,?,?,?,?,?)',
                            (customer_id,customer_name,customer_phone,subtotal,tax,total,datetime.now().strftime('%d %b %Y, %I:%M %p')))
            bill_id=cur.lastrowid
            con.executemany('INSERT INTO bill_items(bill_id,product_id,product_name,price,quantity,line_total) VALUES(?,?,?,?,?,?)',
                            [(bill_id,*it) for it in items])
            flash(f'Bill #{bill_id} created successfully.', 'success')
            return redirect(url_for('invoice',bill_id=bill_id))
    return render_template('billing.html', customers=customer_rows, products=product_rows)

@app.route('/bills')
def bills():
    q=request.args.get('q','').strip()
    with get_db() as con:
        rows=con.execute('SELECT * FROM bills WHERE customer_name LIKE ? OR CAST(id AS TEXT) LIKE ? ORDER BY id DESC', (f'%{q}%',f'%{q}%')).fetchall()
    return render_template('bills.html', bills=rows, q=q)

@app.route('/bills/<int:bill_id>')
def invoice(bill_id):
    with get_db() as con:
        bill=con.execute('SELECT * FROM bills WHERE id=?',(bill_id,)).fetchone()
        if not bill: return 'Bill not found',404
        items=con.execute('SELECT * FROM bill_items WHERE bill_id=?',(bill_id,)).fetchall()
    return render_template('invoice.html', bill=bill, items=items)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
