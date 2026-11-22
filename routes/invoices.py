import os
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from database.db import get_db, get_company_settings
from utils.validators import calculate_gst_breakdown, round_currency
from utils.pdf_generator import generate_invoice_pdf
from config import Config

invoices_bp = Blueprint('invoices', __name__, url_prefix='/invoices')

def generate_invoice_number(conn):
    """Generates sequential unique invoice number e.g. INV-2026-0001."""
    year = datetime.now().year
    cursor = conn.cursor()
    cursor.execute("""
        SELECT invoice_number FROM invoices 
        WHERE invoice_number LIKE ? 
        ORDER BY invoice_id DESC LIMIT 1
    """, (f"INV-{year}-%",))
    last = cursor.fetchone()
    if last and last[0]:
        try:
            seq = int(last[0].split('-')[-1]) + 1
        except ValueError:
            seq = 1
    else:
        seq = 1
    return f"INV-{year}-{seq:04d}"

@invoices_bp.route('/', methods=['GET'])
def list_invoices():
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '').strip()
    from_date = request.args.get('from_date', '').strip()
    to_date = request.args.get('to_date', '').strip()

    conn = get_db()
    try:
        cursor = conn.cursor()
        query = """
            SELECT i.*, c.name AS customer_name, c.phone AS customer_phone
            FROM invoices i
            JOIN customers c ON i.customer_id = c.customer_id
            WHERE 1=1
        """
        params = []

        if search:
            query += " AND (i.invoice_number LIKE ? OR c.name LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])

        if status:
            query += " AND i.payment_status = ?"
            params.append(status)

        if from_date:
            query += " AND i.invoice_date >= ?"
            params.append(from_date)

        if to_date:
            query += " AND i.invoice_date <= ?"
            params.append(to_date)

        query += " ORDER BY i.invoice_date DESC, i.invoice_id DESC"
        invoices = cursor.execute(query, params).fetchall()

        # Summary statistics
        cursor.execute("""
            SELECT COUNT(*) AS total_count,
                   COALESCE(SUM(grand_total), 0) AS total_amount,
                   COALESCE(SUM(CASE WHEN payment_status = 'Paid' THEN grand_total ELSE 0 END), 0) AS paid_amount,
                   COALESCE(SUM(CASE WHEN payment_status = 'Pending' THEN grand_total ELSE 0 END), 0) AS pending_amount
            FROM invoices
        """)
        stats = cursor.fetchone()

        return render_template(
            'invoices.html',
            invoices=invoices,
            search=search,
            status=status,
            from_date=from_date,
            to_date=to_date,
            stats=stats
        )
    finally:
        conn.close()

@invoices_bp.route('/create', methods=['GET', 'POST'])
def create_invoice():
    conn = get_db()
    company = get_company_settings()

    if request.method == 'POST':
        customer_id_str = request.form.get('customer_id', '').strip()
        invoice_date = request.form.get('invoice_date', datetime.today().strftime('%Y-%m-%d')).strip()
        payment_status = request.form.get('payment_status', 'Pending').strip()
        payment_method = request.form.get('payment_method', 'Cash').strip()
        notes = request.form.get('notes', '').strip()

        # Line items lists from form
        product_ids = request.form.getlist('product_id[]')
        quantities = request.form.getlist('quantity[]')

        if not customer_id_str:
            flash("Please select a customer.", "danger")
            return redirect(url_for('invoices.create_invoice'))

        try:
            customer_id = int(customer_id_str)
        except ValueError:
            flash("Invalid customer selected.", "danger")
            return redirect(url_for('invoices.create_invoice'))

        if not product_ids or len(product_ids) == 0:
            flash("At least one product must be added to the invoice.", "danger")
            return redirect(url_for('invoices.create_invoice'))

        # Clean and pair items
        parsed_items = []
        for p_id_str, qty_str in zip(product_ids, quantities):
            if not p_id_str or not qty_str:
                continue
            try:
                p_id = int(p_id_str)
                qty = int(qty_str)
                if qty <= 0:
                    flash("Quantity must be greater than zero for all items.", "danger")
                    return redirect(url_for('invoices.create_invoice'))
                parsed_items.append((p_id, qty))
            except ValueError:
                flash("Invalid product or quantity specified.", "danger")
                return redirect(url_for('invoices.create_invoice'))

        if not parsed_items:
            flash("Please add at least one valid product line item.", "danger")
            return redirect(url_for('invoices.create_invoice'))

        # Aggregate quantities if same product added multiple times
        consolidated = {}
        for p_id, qty in parsed_items:
            consolidated[p_id] = consolidated.get(p_id, 0) + qty

        try:
            cursor = conn.cursor()

            # Verify customer exists
            cursor.execute("SELECT * FROM customers WHERE customer_id = ?", (customer_id,))
            customer = cursor.fetchone()
            if not customer:
                flash("Selected customer does not exist.", "danger")
                return redirect(url_for('invoices.create_invoice'))

            # Determine intra vs inter-state
            cust_state = customer['state'].strip()
            comp_state = company['state'].strip()
            is_inter_state = 1 if cust_state.lower() != comp_state.lower() else 0

            # Validate stock sufficiency for all products
            product_records = {}
            for p_id, req_qty in consolidated.items():
                cursor.execute("SELECT * FROM products WHERE product_id = ?", (p_id,))
                prod = cursor.fetchone()
                if not prod:
                    flash(f"Product ID {p_id} not found in inventory.", "danger")
                    return redirect(url_for('invoices.create_invoice'))
                if prod['stock'] < req_qty:
                    flash(f"Insufficient stock for '{prod['product_name']}'. Available: {prod['stock']}, Requested: {req_qty}.", "danger")
                    return redirect(url_for('invoices.create_invoice'))
                product_records[p_id] = prod

            # Calculate server-side financial figures
            total_taxable = 0.0
            total_cgst = 0.0
            total_sgst = 0.0
            total_igst = 0.0
            total_tax = 0.0
            grand_total = 0.0

            processed_items = []
            for p_id, qty in consolidated.items():
                prod = product_records[p_id]
                unit_price = float(prod['price'])
                gst_rate = float(prod['gst_rate'])
                line_taxable = round_currency(unit_price * qty)

                breakdown = calculate_gst_breakdown(line_taxable, gst_rate, is_inter_state)

                total_taxable += breakdown['taxable_amount']
                total_cgst += breakdown['cgst_amount']
                total_sgst += breakdown['sgst_amount']
                total_igst += breakdown['igst_amount']
                total_tax += breakdown['tax_amount']
                grand_total += breakdown['total_amount']

                processed_items.append({
                    'product_id': p_id,
                    'quantity': qty,
                    'price': unit_price,
                    'gst_rate': gst_rate,
                    'taxable_amount': breakdown['taxable_amount'],
                    'cgst_amount': breakdown['cgst_amount'],
                    'sgst_amount': breakdown['sgst_amount'],
                    'igst_amount': breakdown['igst_amount'],
                    'tax_amount': breakdown['tax_amount'],
                    'total': breakdown['total_amount']
                })

            # Round final totals
            total_taxable = round_currency(total_taxable)
            total_cgst = round_currency(total_cgst)
            total_sgst = round_currency(total_sgst)
            total_igst = round_currency(total_igst)
            total_tax = round_currency(total_tax)
            grand_total = round_currency(grand_total)

            # Generate unique invoice number
            invoice_num = generate_invoice_number(conn)

            # ATOMIC TRANSACTION: Insert invoice, insert items, decrement stock
            cursor.execute("""
                INSERT INTO invoices (
                    invoice_number, customer_id, invoice_date, is_inter_state,
                    subtotal, cgst_amount, sgst_amount, igst_amount,
                    gst_amount, grand_total, payment_status, payment_method, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                invoice_num, customer_id, invoice_date, is_inter_state,
                total_taxable, total_cgst, total_sgst, total_igst,
                total_tax, grand_total, payment_status, payment_method, notes
            ))
            invoice_id = cursor.lastrowid

            for item in processed_items:
                cursor.execute("""
                    INSERT INTO invoice_items (
                        invoice_id, product_id, quantity, price, gst_rate,
                        taxable_amount, cgst_amount, sgst_amount, igst_amount,
                        tax_amount, total
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    invoice_id, item['product_id'], item['quantity'], item['price'],
                    item['gst_rate'], item['taxable_amount'], item['cgst_amount'],
                    item['sgst_amount'], item['igst_amount'], item['tax_amount'], item['total']
                ))

                # Decrement stock in database
                cursor.execute("""
                    UPDATE products
                    SET stock = stock - ?
                    WHERE product_id = ?
                """, (item['quantity'], item['product_id']))

            conn.commit()

            # Generate PDF Invoice immediately
            try:
                generate_invoice_pdf(invoice_id)
            except Exception as pdf_err:
                print(f"Warning: PDF generation failed during invoice creation: {pdf_err}")

            flash(f"Invoice {invoice_num} generated successfully! Stock automatically updated.", "success")
            return redirect(url_for('invoices.view_invoice', invoice_id=invoice_id))

        except Exception as e:
            conn.rollback()
            flash(f"Transaction failed: {str(e)}", "danger")
            return redirect(url_for('invoices.create_invoice'))
        finally:
            conn.close()

    # GET: Load initial dropdown data
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT customer_id, name, phone, state, gstin FROM customers ORDER BY name ASC")
        customers = cursor.fetchall()
        cursor.execute("SELECT product_id, product_name, price, gst_rate, stock FROM products WHERE stock > 0 ORDER BY product_name ASC")
        products = cursor.fetchall()
        today_date = datetime.today().strftime('%Y-%m-%d')
        return render_template(
            'create_invoice.html',
            customers=customers,
            products=products,
            company=company,
            today_date=today_date
        )
    finally:
        conn.close()

@invoices_bp.route('/view/<int:invoice_id>', methods=['GET'])
def view_invoice(invoice_id):
    conn = get_db()
    company = get_company_settings()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT i.*, c.name AS customer_name, c.phone AS customer_phone,
                   c.email AS customer_email, c.address AS customer_address,
                   c.state AS customer_state, c.gstin AS customer_gstin
            FROM invoices i
            JOIN customers c ON i.customer_id = c.customer_id
            WHERE i.invoice_id = ?
        """, (invoice_id,))
        invoice = cursor.fetchone()
        if not invoice:
            flash("Invoice not found.", "warning")
            return redirect(url_for('invoices.list_invoices'))

        cursor.execute("""
            SELECT it.*, p.product_name, p.description AS product_desc
            FROM invoice_items it
            JOIN products p ON it.product_id = p.product_id
            WHERE it.invoice_id = ?
            ORDER BY it.item_id ASC
        """, (invoice_id,))
        items = cursor.fetchall()

        # Check if PDF exists, generate if missing
        pdf_path = os.path.join(Config.PDF_DIR, f"{invoice['invoice_number']}.pdf")
        if not os.path.exists(pdf_path):
            generate_invoice_pdf(invoice_id, pdf_path)

        return render_template('invoice_details.html', invoice=invoice, items=items, company=company)
    finally:
        conn.close()

@invoices_bp.route('/download/<int:invoice_id>', methods=['GET'])
def download_invoice(invoice_id):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT invoice_number FROM invoices WHERE invoice_id = ?", (invoice_id,))
        inv = cursor.fetchone()
        if not inv:
            flash("Invoice not found.", "danger")
            return redirect(url_for('invoices.list_invoices'))

        pdf_path = os.path.join(Config.PDF_DIR, f"{inv['invoice_number']}.pdf")
        if not os.path.exists(pdf_path):
            generate_invoice_pdf(invoice_id, pdf_path)

        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=f"{inv['invoice_number']}.pdf",
            mimetype='application/pdf'
        )
    finally:
        conn.close()

@invoices_bp.route('/delete/<int:invoice_id>', methods=['POST'])
def delete_invoice(invoice_id):
    """
    Deletes invoice and RESTORES product quantities to inventory in a single atomic transaction.
    """
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT invoice_number FROM invoices WHERE invoice_id = ?", (invoice_id,))
        inv = cursor.fetchone()
        if not inv:
            flash("Invoice not found.", "warning")
            return redirect(url_for('invoices.list_invoices'))

        invoice_number = inv['invoice_number']

        # Get items to restore stock
        cursor.execute("SELECT product_id, quantity FROM invoice_items WHERE invoice_id = ?", (invoice_id,))
        items = cursor.fetchall()

        # ATOMIC RESTORATION
        for it in items:
            cursor.execute("""
                UPDATE products
                SET stock = stock + ?
                WHERE product_id = ?
            """, (it['quantity'], it['product_id']))

        # Delete invoice (Foreign key cascade deletes invoice_items)
        cursor.execute("DELETE FROM invoices WHERE invoice_id = ?", (invoice_id,))
        conn.commit()

        # Delete generated PDF file if it exists
        pdf_path = os.path.join(Config.PDF_DIR, f"{invoice_number}.pdf")
        if os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
            except OSError:
                pass

        flash(f"Invoice {invoice_number} deleted and product stock restored to inventory.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Failed to delete invoice: {str(e)}", "danger")
    finally:
        conn.close()

    return redirect(url_for('invoices.list_invoices'))

