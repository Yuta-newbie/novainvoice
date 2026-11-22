import unittest
import os
import sqlite3
from app import create_app
from database.db import get_db, init_db
from utils.validators import validate_phone, validate_email, validate_gstin

class TestCustomerManagement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def test_phone_validation(self):
        """Validates Indian phone numbers correctly."""
        valid, val = validate_phone("9810123456")
        self.assertTrue(valid)
        self.assertEqual(val, "9810123456")

        valid, val = validate_phone("+91 98101-23456")
        self.assertTrue(valid)
        self.assertEqual(val, "9810123456")

        # Invalid start digit (starts with 1)
        valid, msg = validate_phone("1234567890")
        self.assertFalse(valid)

        # Invalid length (8 digits)
        valid, msg = validate_phone("98101234")
        self.assertFalse(valid)

    def test_email_validation(self):
        """Validates email format."""
        valid, _ = validate_email("test@example.com")
        self.assertTrue(valid)

        valid, _ = validate_email("")
        self.assertTrue(valid)  # Optional field

        valid, _ = validate_email("invalid-email-string")
        self.assertFalse(valid)

    def test_gstin_validation(self):
        """Validates 15-character Indian GSTIN."""
        valid, _ = validate_gstin("09AABCS1429B1Z1")
        self.assertTrue(valid)

        valid, _ = validate_gstin("")
        self.assertTrue(valid)  # Optional for unregistered

        valid, _ = validate_gstin("INVALIDGST")
        self.assertFalse(valid)

    def test_customer_crud_flow(self):
        """Tests complete add, edit, search, and delete customer flow."""
        with self.app.app_context():
            conn = get_db()
            cursor = conn.cursor()
            
            # Insert test customer
            cursor.execute("""
                INSERT INTO customers (name, phone, email, address, state, gstin)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ("Test Retailer Alpha", "9899112233", "alpha@test.com", "Sector 1, Noida", "Uttar Pradesh", "09AABCT1234A1Z5"))
            conn.commit()
            cust_id = cursor.lastrowid

            # Verify presence
            cursor.execute("SELECT * FROM customers WHERE customer_id = ?", (cust_id,))
            cust = cursor.fetchone()
            self.assertIsNotNone(cust)
            self.assertEqual(cust['name'], "Test Retailer Alpha")

            # Edit customer
            cursor.execute("""
                UPDATE customers SET name = ?, phone = ? WHERE customer_id = ?
            """, ("Test Retailer Updated", "9899112244", cust_id))
            conn.commit()

            cursor.execute("SELECT name, phone FROM customers WHERE customer_id = ?", (cust_id,))
            updated = cursor.fetchone()
            self.assertEqual(updated['name'], "Test Retailer Updated")
            self.assertEqual(updated['phone'], "9899112244")

            # Delete customer
            cursor.execute("DELETE FROM customers WHERE customer_id = ?", (cust_id,))
            conn.commit()

            cursor.execute("SELECT * FROM customers WHERE customer_id = ?", (cust_id,))
            self.assertIsNone(cursor.fetchone())
            conn.close()

if __name__ == '__main__':
    unittest.main()

