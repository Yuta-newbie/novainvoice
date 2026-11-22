"""
Demo Seeding Script for NovaInvoice
Seeds initial demo invoices so the dashboard has rich historical & recent billing records.
"""

import os
import sys

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from database.db import get_db, init_db
from routes.invoices import generate_invoice_number
from utils.validators import calculate_gst_breakdown
from utils.pdf_generator import generate_invoice_pdf

def seed_demo_invoices():
    init_db()
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM invoices")
    count = cursor.fetchone()[0]

    if count == 0:
        # Invoice 1: Intra-state (UP customer)
        cursor.execute("SELECT customer_id FROM customers WHERE state = 'Uttar Pradesh' LIMIT 1")
        cust1_row = cursor.fetchone()
        if not cust1_row:
            return
        cust1 = cust1_row[0]

        cursor.execute("SELECT product_id, price, gst_rate FROM products LIMIT 2")
        prods = cursor.fetchall()
        
        inv_num1 = generate_invoice_number(conn)
        items1 = [
            (prods[0][0], 2, prods[0][1], prods[0][2]),
            (prods[1][0], 1, prods[1][1], prods[1][2])
        ]
        subtotal1 = sum(p * q for _, q, p, _ in items1)
        b1 = calculate_gst_breakdown(subtotal1, 5.0, is_inter_state=False)
        
        cursor.execute("""
            INSERT INTO invoices (invoice_number, customer_id, invoice_date, is_inter_state, subtotal, cgst_amount, sgst_amount, igst_amount, gst_amount, grand_total, payment_status, payment_method, notes)
            VALUES (?, ?, '2026-11-10', 0, ?, ?, ?, 0.0, ?, ?, 'Paid', 'UPI', 'Delivered via local delivery')
        """, (inv_num1, cust1, b1['taxable_amount'], b1['cgst_amount'], b1['sgst_amount'], b1['tax_amount'], b1['total_amount']))
        inv_id1 = cursor.lastrowid
        
        for pid, qty, price, gst in items1:
            line_taxable = price * qty
            line_b = calculate_gst_breakdown(line_taxable, gst, is_inter_state=False)
            cursor.execute("""
                INSERT INTO invoice_items (invoice_id, product_id, quantity, price, gst_rate, taxable_amount, cgst_amount, sgst_amount, igst_amount, tax_amount, total)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0.0, ?, ?)
            """, (inv_id1, pid, qty, price, gst, line_b['taxable_amount'], line_b['cgst_amount'], line_b['sgst_amount'], line_b['tax_amount'], line_b['total_amount']))
            cursor.execute("UPDATE products SET stock = stock - ? WHERE product_id = ?", (qty, pid))
        
        conn.commit()
        generate_invoice_pdf(inv_id1)

        # Invoice 2: Inter-state (Delhi customer)
        cursor.execute("SELECT customer_id FROM customers WHERE state = 'Delhi' LIMIT 1")
        cust2_row = cursor.fetchone()
        cust2 = cust2_row[0] if cust2_row else cust1
        
        inv_num2 = generate_invoice_number(conn)
        cursor.execute("SELECT product_id, price, gst_rate FROM products LIMIT 1 OFFSET 2")
        p3 = cursor.fetchone()
        
        line3_taxable = p3[1] * 3
        b2 = calculate_gst_breakdown(line3_taxable, p3[2], is_inter_state=True)
        
        cursor.execute("""
            INSERT INTO invoices (invoice_number, customer_id, invoice_date, is_inter_state, subtotal, cgst_amount, sgst_amount, igst_amount, gst_amount, grand_total, payment_status, payment_method, notes)
            VALUES (?, ?, '2026-11-09', 1, ?, 0.0, 0.0, ?, ?, ?, 'Pending', 'Bank Transfer', 'Dispatched via Express Courier')
        """, (inv_num2, cust2, b2['taxable_amount'], b2['igst_amount'], b2['tax_amount'], b2['total_amount']))
        inv_id2 = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO invoice_items (invoice_id, product_id, quantity, price, gst_rate, taxable_amount, cgst_amount, sgst_amount, igst_amount, tax_amount, total)
            VALUES (?, ?, 3, ?, ?, ?, 0.0, 0.0, ?, ?, ?)
        """, (inv_id2, p3[0], p3[1], p3[2], b2['taxable_amount'], b2['igst_amount'], b2['tax_amount'], b2['total_amount']))
        cursor.execute("UPDATE products SET stock = stock - 3 WHERE product_id = ?", (p3[0],))
        
        conn.commit()
        generate_invoice_pdf(inv_id2)
        print("Demo invoices seeded successfully with PDFs generated.")
    else:
        print(f"Database already contains {count} invoices.")
        
    conn.close()

if __name__ == '__main__':
    seed_demo_invoices()
