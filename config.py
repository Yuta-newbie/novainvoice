import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    BASE_DIR = BASE_DIR
    SECRET_KEY = os.environ.get('SECRET_KEY', 'novainvoice-bca-secret-key-2026')
    DATABASE_PATH = os.path.join(BASE_DIR, 'database', 'invoice.db')
    SCHEMA_PATH = os.path.join(BASE_DIR, 'database', 'schema.sql')
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    HISTORICAL_CSV_PATH = os.path.join(BASE_DIR, 'data', 'historical_invoices.csv')
    DAILY_SALES_CSV_PATH = os.path.join(BASE_DIR, 'data', 'daily_sales.csv')
    MODEL_PATH = os.path.join(BASE_DIR, 'models', 'sales_model.pkl')
    PDF_DIR = os.path.join(BASE_DIR, 'generated_invoices')
    
    # Business Profile for GST and Invoicing
    COMPANY_NAME = "NovaInvoice Solutions"
    COMPANY_TAGLINE = "Smart Billing & Sales Intelligence"
    COMPANY_ADDRESS = "Plot 18, Knowledge Park III, Greater Noida, UP - 201306"
    COMPANY_PHONE = "+91 98765 43210"
    COMPANY_EMAIL = "contact@novainvoice.in"
    COMPANY_GSTIN = "09AAACN1234F1Z9"
    COMPANY_STATE = "Uttar Pradesh"
    COMPANY_STATE_CODE = "09"
    
    # Machine Learning Settings
    DEFAULT_FORECAST_HORIZON = 7
    ML_TEST_SPLIT_RATIO = 0.20
    RANDOM_SEED = 42
