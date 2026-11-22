from datetime import datetime
from flask import Blueprint, render_template
from database.db import get_db
from utils.ml_model import load_sales_model

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/', methods=['GET'])
def index():
    conn = get_db()
    try:
        cursor = conn.cursor()

        # 1. Total Invoices & Total Sales
        cursor.execute("""
            SELECT COUNT(*) AS total_invoices,
                   COALESCE(SUM(grand_total), 0) AS total_sales,
                   COALESCE(SUM(CASE WHEN payment_status = 'Pending' THEN grand_total ELSE 0 END), 0) AS pending_amount,
                   COALESCE(SUM(CASE WHEN payment_status = 'Pending' THEN 1 ELSE 0 END), 0) AS pending_count
            FROM invoices
        """)
        inv_stats = cursor.fetchone()

        # 2. Total Customers
        cursor.execute("SELECT COUNT(*) FROM customers")
        total_customers = cursor.fetchone()[0]

        # 3. Total Products & Low Stock Count
        cursor.execute("SELECT COUNT(*) FROM products")
        total_products = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM products WHERE stock <= minimum_stock")
        low_stock_count = cursor.fetchone()[0]

        # 4. Low stock products alert list (up to 5 items)
        cursor.execute("""
            SELECT product_id, product_name, stock, minimum_stock, price
            FROM products 
            WHERE stock <= minimum_stock 
            ORDER BY stock ASC 
            LIMIT 5
        """)
        low_stock_products = cursor.fetchall()

        # 5. Recent Invoices (up to 7 items)
        cursor.execute("""
            SELECT i.invoice_id, i.invoice_number, i.invoice_date, i.grand_total,
                   i.payment_status, c.name AS customer_name
            FROM invoices i
            JOIN customers c ON i.customer_id = c.customer_id
            ORDER BY i.invoice_date DESC, i.invoice_id DESC
            LIMIT 7
        """)
        recent_invoices = cursor.fetchall()

        # 6. Top Selling Products (by quantity from invoice_items)
        cursor.execute("""
            SELECT p.product_name, SUM(it.quantity) AS total_sold,
                   SUM(it.total) AS total_revenue
            FROM invoice_items it
            JOIN products p ON it.product_id = p.product_id
            GROUP BY p.product_id
            ORDER BY total_sold DESC
            LIMIT 5
        """)
        top_selling = cursor.fetchall()

        # 7. Today's and This Month's Sales (from invoices + sales_data)
        today_str = datetime.today().strftime('%Y-%m-%d')
        month_prefix = datetime.today().strftime('%Y-%m')
        
        cursor.execute("SELECT COALESCE(SUM(grand_total), 0) FROM invoices WHERE invoice_date = ?", (today_str,))
        today_sales = cursor.fetchone()[0]

        cursor.execute("SELECT COALESCE(SUM(grand_total), 0) FROM invoices WHERE invoice_date LIKE ?", (f"{month_prefix}%",))
        month_sales = cursor.fetchone()[0]

        # 8. ML Snapshot & Next Day Prediction
        cursor.execute("""
            SELECT prediction_date, predicted_sales, model_metric 
            FROM predictions 
            ORDER BY prediction_date ASC 
            LIMIT 1
        """)
        next_prediction = cursor.fetchone()

        ml_bundle = None
        try:
            ml_bundle = load_sales_model()
        except Exception:
            pass

        # 9. Recent 14-day sales trend for dashboard preview chart
        cursor.execute("""
            SELECT date, daily_sales FROM sales_data 
            ORDER BY date DESC LIMIT 14
        """)
        trend_rows = cursor.fetchall()[::-1]
        chart_trend = {
            'labels': [r['date'] for r in trend_rows],
            'sales': [round(float(r['daily_sales']), 2) for r in trend_rows]
        }

        return render_template(
            'dashboard.html',
            total_sales=inv_stats['total_sales'],
            total_invoices=inv_stats['total_invoices'],
            pending_amount=inv_stats['pending_amount'],
            pending_count=inv_stats['pending_count'],
            total_customers=total_customers,
            total_products=total_products,
            low_stock_count=low_stock_count,
            low_stock_products=low_stock_products,
            recent_invoices=recent_invoices,
            top_selling=top_selling,
            today_sales=today_sales,
            month_sales=month_sales,
            next_prediction=next_prediction,
            ml_bundle=ml_bundle,
            chart_trend=chart_trend
        )
    finally:
        conn.close()

