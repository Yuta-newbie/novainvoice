from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from database.db import get_db
from utils.validators import validate_phone, validate_email, validate_gstin

customers_bp = Blueprint('customers', __name__, url_prefix='/customers')

@customers_bp.route('/', methods=['GET'])
def list_customers():
    search = request.args.get('search', '').strip()
    conn = get_db()
    try:
        cursor = conn.cursor()
        if search:
            query = """
                SELECT c.*, COUNT(i.invoice_id) AS total_invoices,
                       COALESCE(SUM(i.grand_total), 0) AS total_spent
                FROM customers c
                LEFT JOIN invoices i ON c.customer_id = i.customer_id
                WHERE c.name LIKE ? OR c.phone LIKE ? OR c.email LIKE ? OR c.gstin LIKE ?
                GROUP BY c.customer_id
                ORDER BY c.customer_id DESC
            """
            param = f"%{search}%"
            customers = cursor.execute(query, (param, param, param, param)).fetchall()
        else:
            query = """
                SELECT c.*, COUNT(i.invoice_id) AS total_invoices,
                       COALESCE(SUM(i.grand_total), 0) AS total_spent
                FROM customers c
                LEFT JOIN invoices i ON c.customer_id = i.customer_id
                GROUP BY c.customer_id
                ORDER BY c.customer_id DESC
            """
            customers = cursor.execute(query).fetchall()
        return render_template('customers.html', customers=customers, search=search)
    finally:
        conn.close()

@customers_bp.route('/add', methods=['GET', 'POST'])
def add_customer():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        address = request.form.get('address', '').strip()
        state = request.form.get('state', 'Uttar Pradesh').strip()
        gstin = request.form.get('gstin', '').strip()

        # Validation
        if not name:
            flash("Customer name is required.", "danger")
            return render_template('customer_form.html', action='Add', customer=request.form)

        valid_phone, phone_msg = validate_phone(phone)
        if not valid_phone:
            flash(phone_msg, "danger")
            return render_template('customer_form.html', action='Add', customer=request.form)

        valid_email, email_msg = validate_email(email)
        if not valid_email:
            flash(email_msg, "danger")
            return render_template('customer_form.html', action='Add', customer=request.form)

        valid_gstin, gstin_msg = validate_gstin(gstin)
        if not valid_gstin:
            flash(gstin_msg, "danger")
            return render_template('customer_form.html', action='Add', customer=request.form)

        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO customers (name, phone, email, address, state, gstin)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, phone_msg, email_msg if email else None, address, state, gstin_msg if gstin else None))
            conn.commit()
            flash(f"Customer '{name}' added successfully.", "success")
            return redirect(url_for('customers.list_customers'))
        except Exception as e:
            flash(f"Error saving customer: {str(e)}", "danger")
            return render_template('customer_form.html', action='Add', customer=request.form)
        finally:
            conn.close()

    return render_template('customer_form.html', action='Add', customer={})

@customers_bp.route('/edit/<int:customer_id>', methods=['GET', 'POST'])
def edit_customer(customer_id):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM customers WHERE customer_id = ?", (customer_id,))
        customer = cursor.fetchone()
        if not customer:
            flash("Customer not found.", "warning")
            return redirect(url_for('customers.list_customers'))

        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            phone = request.form.get('phone', '').strip()
            email = request.form.get('email', '').strip()
            address = request.form.get('address', '').strip()
            state = request.form.get('state', 'Uttar Pradesh').strip()
            gstin = request.form.get('gstin', '').strip()

            if not name:
                flash("Customer name is required.", "danger")
                return render_template('customer_form.html', action='Edit', customer=request.form)

            valid_phone, phone_msg = validate_phone(phone)
            if not valid_phone:
                flash(phone_msg, "danger")
                return render_template('customer_form.html', action='Edit', customer=request.form)

            valid_email, email_msg = validate_email(email)
            if not valid_email:
                flash(email_msg, "danger")
                return render_template('customer_form.html', action='Edit', customer=request.form)

            valid_gstin, gstin_msg = validate_gstin(gstin)
            if not valid_gstin:
                flash(gstin_msg, "danger")
                return render_template('customer_form.html', action='Edit', customer=request.form)

            cursor.execute("""
                UPDATE customers
                SET name = ?, phone = ?, email = ?, address = ?, state = ?, gstin = ?
                WHERE customer_id = ?
            """, (name, phone_msg, email_msg if email else None, address, state, gstin_msg if gstin else None, customer_id))
            conn.commit()
            flash(f"Customer '{name}' updated successfully.", "success")
            return redirect(url_for('customers.list_customers'))

        return render_template('customer_form.html', action='Edit', customer=dict(customer))
    finally:
        conn.close()

@customers_bp.route('/delete/<int:customer_id>', methods=['POST'])
def delete_customer(customer_id):
    conn = get_db()
    try:
        cursor = conn.cursor()
        # Verify invoice dependency
        cursor.execute("SELECT COUNT(*) FROM invoices WHERE customer_id = ?", (customer_id,))
        invoice_count = cursor.fetchone()[0]
        if invoice_count > 0:
            flash(f"Cannot delete customer. There are {invoice_count} existing invoices associated with this customer. Delete or reassign invoices first.", "danger")
            return redirect(url_for('customers.list_customers'))

        cursor.execute("DELETE FROM customers WHERE customer_id = ?", (customer_id,))
        conn.commit()
        flash("Customer deleted successfully.", "success")
    except Exception as e:
        flash(f"Error deleting customer: {str(e)}", "danger")
    finally:
        conn.close()
    return redirect(url_for('customers.list_customers'))

@customers_bp.route('/view/<int:customer_id>', methods=['GET'])
def view_customer(customer_id):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM customers WHERE customer_id = ?", (customer_id,))
        customer = cursor.fetchone()
        if not customer:
            flash("Customer not found.", "warning")
            return redirect(url_for('customers.list_customers'))

        cursor.execute("""
            SELECT * FROM invoices 
            WHERE customer_id = ? 
            ORDER BY invoice_date DESC, invoice_id DESC
        """, (customer_id,))
        invoices = cursor.fetchall()

        cursor.execute("""
            SELECT COUNT(*) AS count, COALESCE(SUM(grand_total), 0) AS total_spent
            FROM invoices WHERE customer_id = ?
        """, (customer_id,))
        stats = cursor.fetchone()

        return render_template('customer_view.html', customer=customer, invoices=invoices, stats=stats)
    finally:
        conn.close()

@customers_bp.route('/api/search', methods=['GET'])
def api_search_customers():
    query = request.args.get('q', '').strip()
    conn = get_db()
    try:
        cursor = conn.cursor()
        if query:
            cursor.execute("""
                SELECT customer_id, name, phone, email, address, state, gstin 
                FROM customers 
                WHERE name LIKE ? OR phone LIKE ? OR gstin LIKE ?
                ORDER BY name ASC LIMIT 15
            """, (f"%{query}%", f"%{query}%", f"%{query}%"))
        else:
            cursor.execute("""
                SELECT customer_id, name, phone, email, address, state, gstin 
                FROM customers 
                ORDER BY name ASC LIMIT 50
            """)
        results = [dict(row) for row in cursor.fetchall()]
        return jsonify({'customers': results})
    finally:
        conn.close()

