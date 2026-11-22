import os
from flask import Flask, render_template
from config import Config
from database.db import init_db
from utils.sales_data import generate_historical_dataset, aggregate_daily_sales
from utils.ml_model import load_sales_model

# Import Blueprints
from routes.dashboard import dashboard_bp
from routes.customers import customers_bp
from routes.products import products_bp
from routes.invoices import invoices_bp
from routes.analytics import analytics_bp

def create_app():
    """Application factory for NovaInvoice Flask application."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure required directories exist
    os.makedirs(Config.DATA_DIR, exist_ok=True)
    os.makedirs(Config.PDF_DIR, exist_ok=True)
    os.makedirs(os.path.join(Config.BASE_DIR, 'models'), exist_ok=True)

    # Initialize Database Schema & Seed Data
    with app.app_context():
        init_db()
        # Initialize historical dataset (3,000 records, 19 fields) if missing
        if not os.path.exists(Config.HISTORICAL_CSV_PATH):
            generate_historical_dataset()
        # Aggregate daily sales dataset if missing
        if not os.path.exists(Config.DAILY_SALES_CSV_PATH):
            aggregate_daily_sales()
        # Ensure ML model is trained and ready
        if not os.path.exists(Config.MODEL_PATH):
            try:
                load_sales_model()
            except Exception as e:
                print("Initial ML training note:", e)

    # Register Blueprints
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(invoices_bp)
    app.register_blueprint(analytics_bp)

    # Jinja2 Custom Filters
    @app.template_filter('currency')
    def currency_filter(val):
        try:
            val_float = float(val or 0.0)
            return f"₹{val_float:,.2f}"
        except (ValueError, TypeError):
            return "₹0.00"

    @app.template_filter('format_date')
    def format_date_filter(val):
        if not val:
            return ""
        try:
            from datetime import datetime
            dt = datetime.strptime(str(val)[:10], "%Y-%m-%d")
            return dt.strftime("%d %b %Y")
        except Exception:
            return str(val)

    # Error Handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('500.html'), 500

    return app

app = create_app()

if __name__ == '__main__':
    print("Starting NovaInvoice Application...")
    print("Local URL: http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000, debug=True)

