import os
import sqlite3
from config import Config

def get_db():
    """
    Returns a SQLite database connection with row factory enabled
    and foreign key constraints enforced.
    """
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """
    Initializes the database schema and seeds initial data if tables are empty.
    Guarantees no duplicate records are inserted on restarts.
    """
    os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)
    
    with open(Config.SCHEMA_PATH, 'r', encoding='utf-8') as f:
        schema_sql = f.read()

    conn = get_db()
    try:
        conn.executescript(schema_sql)
        
        # Seed company settings if not present
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM company_settings WHERE id = 1")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO company_settings (id, name, tagline, address, phone, email, gstin, state, state_code)
                VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                Config.COMPANY_NAME,
                Config.COMPANY_TAGLINE,
                Config.COMPANY_ADDRESS,
                Config.COMPANY_PHONE,
                Config.COMPANY_EMAIL,
                Config.COMPANY_GSTIN,
                Config.COMPANY_STATE,
                Config.COMPANY_STATE_CODE
            ))

        # Seed 8 realistic Indian demo products if products table is empty
        cursor.execute("SELECT COUNT(*) FROM products")
        if cursor.fetchone()[0] == 0:
            demo_products = [
                ("Premium Basmati Rice (10 kg)", "Long grain aged aromatic basmati rice for daily & culinary use", 1250.00, 5.0, 40, 10),
                ("Refined Sunflower Oil (5 L)", "Double filtered healthy cooking oil with vitamin enrichment", 780.00, 5.0, 35, 8),
                ("Whole Wheat Chakki Atta (10 kg)", "100% whole grain stone-ground high-fiber wheat flour", 440.00, 5.0, 50, 15),
                ("Dairy Fresh Cow Ghee (1 L)", "Pure traditional clarified butter with rich aroma", 620.00, 12.0, 25, 6),
                ("Assam Orthodox Black Tea (500 g)", "Selected high-grown Assam tea leaves for brisk flavor", 340.00, 5.0, 30, 8),
                ("Arabica Roasted Coffee Beans (500 g)", "Single-origin medium roast specialty coffee beans", 590.00, 18.0, 20, 5),
                ("Organic Almonds Badam Giri (1 kg)", "Premium California grade jumbo raw almonds", 890.00, 12.0, 15, 5),
                ("Kashmiri Mongra Saffron (1 g)", "Grade-A pure organic natural Kashmiri red saffron threads", 350.00, 12.0, 4, 5) # Stock 4 < Min 5 (Low stock demo)
            ]
            cursor.executemany("""
                INSERT INTO products (product_name, description, price, gst_rate, stock, minimum_stock)
                VALUES (?, ?, ?, ?, ?, ?)
            """, demo_products)

        # Seed demo customers if customers table is empty
        cursor.execute("SELECT COUNT(*) FROM customers")
        if cursor.fetchone()[0] == 0:
            demo_customers = [
                ("Sharma Retail & General Store", "9810123456", "sharma.retail@gmail.com", "Shop 12, Main Market, Sector 18, Noida", "Uttar Pradesh", "09AABCS1429B1Z1"),
                ("Verma Provision Store", "9871234567", "verma.provisions@gmail.com", "Plot 45, Connaught Place, New Delhi", "Delhi", "07AAECV3456C1Z4"),
                ("Gupta Wholesale Mart", "9910987654", "gupta.wholesale@yahoo.com", "Civil Lines, Kanpur, Uttar Pradesh", "Uttar Pradesh", "09AADCG9876E1Z8"),
                ("Sunrise Mart & Supermarket", "9820567890", "orders@sunrisemart.in", "DLF Phase 4, Gurugram, Haryana", "Haryana", "06AALCS5678H1Z2")
            ]
            cursor.executemany("""
                INSERT INTO customers (name, phone, email, address, state, gstin)
                VALUES (?, ?, ?, ?, ?, ?)
            """, demo_customers)

        conn.commit()
    finally:
        conn.close()

def get_company_settings():
    """Fetches company profile details."""
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM company_settings WHERE id = 1").fetchone()
        if row:
            return dict(row)
        return {
            'name': Config.COMPANY_NAME,
            'tagline': Config.COMPANY_TAGLINE,
            'address': Config.COMPANY_ADDRESS,
            'phone': Config.COMPANY_PHONE,
            'email': Config.COMPANY_EMAIL,
            'gstin': Config.COMPANY_GSTIN,
            'state': Config.COMPANY_STATE,
            'state_code': Config.COMPANY_STATE_CODE
        }
    finally:
        conn.close()

