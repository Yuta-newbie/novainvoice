import unittest
from app import create_app
from database.db import get_db

class TestProductManagement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()

    def test_product_crud_and_stock(self):
        """Tests product creation, stock adjustment, and low stock threshold detection."""
        with self.app.app_context():
            conn = get_db()
            cursor = conn.cursor()

            # Create product with stock 10 and threshold 5
            cursor.execute("""
                INSERT INTO products (product_name, description, price, gst_rate, stock, minimum_stock)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ("Test Product X", "Sample product for testing", 500.0, 18.0, 10, 5))
            conn.commit()
            p_id = cursor.lastrowid

            cursor.execute("SELECT * FROM products WHERE product_id = ?", (p_id,))
            p = cursor.fetchone()
            self.assertIsNotNone(p)
            self.assertEqual(p['stock'], 10)
            self.assertGreater(p['stock'], p['minimum_stock'])

            # Adjust stock down to 4 (triggering low stock alert)
            cursor.execute("UPDATE products SET stock = stock - 6 WHERE product_id = ?", (p_id,))
            conn.commit()

            cursor.execute("SELECT stock, minimum_stock FROM products WHERE product_id = ?", (p_id,))
            p_updated = cursor.fetchone()
            self.assertEqual(p_updated['stock'], 4)
            self.assertLessEqual(p_updated['stock'], p_updated['minimum_stock'])

            # Clean up
            cursor.execute("DELETE FROM products WHERE product_id = ?", (p_id,))
            conn.commit()
            conn.close()

if __name__ == '__main__':
    unittest.main()

