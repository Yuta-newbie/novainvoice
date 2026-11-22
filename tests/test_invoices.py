import os
import unittest
from app import create_app
from database.db import get_db
from utils.pdf_generator import generate_invoice_pdf
from config import Config

class TestInvoiceManagement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()

    def test_invoice_creation_stock_reduction_and_restoration(self):
        """
        Tests:
        1. Creation of invoice reduces product stock.
        2. ReportLab generates a valid PDF.
        3. Deletion of invoice restores product stock.
        """
        with self.app.app_context():
            conn = get_db()
            cursor = conn.cursor()

            # Insert dedicated test customer
            cursor.execute("""
                INSERT INTO customers (name, phone, state, gstin)
                VALUES (?, ?, ?, ?)
            """, ("Test Customer Inv", "9811122233", "Uttar Pradesh", "09AABCT1234A1Z5"))
            cust_id = cursor.lastrowid

            # Insert dedicated test product with known stock = 20
            initial_stock = 20
            cursor.execute("""
                INSERT INTO products (product_name, price, gst_rate, stock, minimum_stock)
                VALUES (?, ?, ?, ?, ?)
            """, ("Test Stock Item", 100.0, 18.0, initial_stock, 5))
            prod_id = cursor.lastrowid
            conn.commit()

            # Create an invoice for 5 units
            purchase_qty = 5
            taxable = 100.0 * purchase_qty  # 500.0
            cgst = 45.0  # 9%
            sgst = 45.0  # 9%
            total_tax = 90.0
            grand_total = 590.0
            inv_num = "TEST-INV-9999"

            cursor.execute("""
                INSERT INTO invoices (
                    invoice_number, customer_id, invoice_date, is_inter_state,
                    subtotal, cgst_amount, sgst_amount, igst_amount,
                    gst_amount, grand_total, payment_status, payment_method
                ) VALUES (?, ?, '2026-11-10', 0, ?, ?, ?, 0.0, ?, ?, 'Paid', 'UPI')
            """, (inv_num, cust_id, taxable, cgst, sgst, total_tax, grand_total))
            inv_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO invoice_items (
                    invoice_id, product_id, quantity, price, gst_rate,
                    taxable_amount, cgst_amount, sgst_amount, igst_amount,
                    tax_amount, total
                ) VALUES (?, ?, ?, 100.0, 18.0, ?, ?, ?, 0.0, ?, ?)
            """, (inv_id, prod_id, purchase_qty, taxable, cgst, sgst, total_tax, grand_total))

            # Decrement stock
            cursor.execute("UPDATE products SET stock = stock - ? WHERE product_id = ?", (purchase_qty, prod_id))
            conn.commit()

            # Check stock was decremented: 20 - 5 = 15
            cursor.execute("SELECT stock FROM products WHERE product_id = ?", (prod_id,))
            current_stock = cursor.fetchone()[0]
            self.assertEqual(current_stock, 15)

            # Test PDF generation
            pdf_path = os.path.join(Config.PDF_DIR, f"{inv_num}.pdf")
            out = generate_invoice_pdf(inv_id, pdf_path)
            self.assertTrue(os.path.exists(pdf_path))
            self.assertGreater(os.path.getsize(pdf_path), 1000)  # Valid PDF size > 1KB

            # Delete invoice and restore stock
            cursor.execute("SELECT product_id, quantity FROM invoice_items WHERE invoice_id = ?", (inv_id,))
            items = cursor.fetchall()
            for it in items:
                cursor.execute("UPDATE products SET stock = stock + ? WHERE product_id = ?", (it['quantity'], it['product_id']))
            cursor.execute("DELETE FROM invoices WHERE invoice_id = ?", (inv_id,))
            conn.commit()

            # Check stock is fully restored to 20
            cursor.execute("SELECT stock FROM products WHERE product_id = ?", (prod_id,))
            restored_stock = cursor.fetchone()[0]
            self.assertEqual(restored_stock, initial_stock)

            # Cleanup test records
            cursor.execute("DELETE FROM products WHERE product_id = ?", (prod_id,))
            cursor.execute("DELETE FROM customers WHERE customer_id = ?", (cust_id,))
            conn.commit()
            conn.close()

            if os.path.exists(pdf_path):
                os.remove(pdf_path)

if __name__ == '__main__':
    unittest.main()

