-- NovaInvoice Database Schema
-- Relational SQLite schema with foreign key enforcement

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT,
    address TEXT,
    state TEXT NOT NULL DEFAULT 'Uttar Pradesh',
    gstin TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT NOT NULL,
    description TEXT,
    price REAL NOT NULL CHECK(price >= 0),
    gst_rate REAL NOT NULL CHECK(gst_rate >= 0),
    stock INTEGER NOT NULL DEFAULT 0 CHECK(stock >= 0),
    minimum_stock INTEGER NOT NULL DEFAULT 5 CHECK(minimum_stock >= 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS invoices (
    invoice_id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number TEXT UNIQUE NOT NULL,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id) ON DELETE RESTRICT,
    invoice_date DATE NOT NULL,
    is_inter_state INTEGER NOT NULL DEFAULT 0,
    subtotal REAL NOT NULL CHECK(subtotal >= 0),
    cgst_amount REAL NOT NULL DEFAULT 0.0 CHECK(cgst_amount >= 0),
    sgst_amount REAL NOT NULL DEFAULT 0.0 CHECK(sgst_amount >= 0),
    igst_amount REAL NOT NULL DEFAULT 0.0 CHECK(igst_amount >= 0),
    gst_amount REAL NOT NULL CHECK(gst_amount >= 0),
    grand_total REAL NOT NULL CHECK(grand_total >= 0),
    payment_status TEXT NOT NULL DEFAULT 'Pending' CHECK(payment_status IN ('Paid', 'Pending', 'Partial')),
    payment_method TEXT DEFAULT 'Cash' CHECK(payment_method IN ('Cash', 'UPI', 'Bank Transfer', 'Credit Card', 'Cheque')),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS invoice_items (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL REFERENCES invoices(invoice_id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    quantity INTEGER NOT NULL CHECK(quantity > 0),
    price REAL NOT NULL CHECK(price >= 0),
    gst_rate REAL NOT NULL CHECK(gst_rate >= 0),
    taxable_amount REAL NOT NULL CHECK(taxable_amount >= 0),
    cgst_amount REAL NOT NULL DEFAULT 0.0 CHECK(cgst_amount >= 0),
    sgst_amount REAL NOT NULL DEFAULT 0.0 CHECK(sgst_amount >= 0),
    igst_amount REAL NOT NULL DEFAULT 0.0 CHECK(igst_amount >= 0),
    tax_amount REAL NOT NULL CHECK(tax_amount >= 0),
    total REAL NOT NULL CHECK(total >= 0)
);

CREATE TABLE IF NOT EXISTS sales_data (
    date DATE PRIMARY KEY,
    daily_sales REAL NOT NULL,
    invoice_count INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,
    is_weekend INTEGER NOT NULL,
    day_number INTEGER NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    lag_sales REAL NOT NULL,
    rolling_avg REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS predictions (
    prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_date DATE NOT NULL,
    predicted_sales REAL NOT NULL,
    model_metric TEXT,
    algorithm TEXT DEFAULT 'Multiple Linear Regression',
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS company_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    name TEXT NOT NULL,
    tagline TEXT,
    address TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT NOT NULL,
    gstin TEXT NOT NULL,
    state TEXT NOT NULL,
    state_code TEXT NOT NULL
);

-- Indexes for fast query performance
CREATE INDEX IF NOT EXISTS idx_invoices_date ON invoices(invoice_date);
CREATE INDEX IF NOT EXISTS idx_invoices_customer ON invoices(customer_id);
CREATE INDEX IF NOT EXISTS idx_invoice_items_invoice ON invoice_items(invoice_id);
CREATE INDEX IF NOT EXISTS idx_products_stock ON products(stock);
CREATE INDEX IF NOT EXISTS idx_predictions_date ON predictions(prediction_date);

