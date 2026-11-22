import json
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from config import Config
from database.db import get_db
from utils.ml_model import load_sales_model, train_sales_model, generate_future_forecast
from utils.sales_data import aggregate_daily_sales, generate_historical_dataset

analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')

@analytics_bp.route('/', methods=['GET'])
def index():
    # Load ML model bundle
    try:
        bundle = load_sales_model()
    except Exception as e:
        flash(f"ML Model initialization: {str(e)}", "warning")
        bundle = None

    # Load current predictions from database
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM predictions 
            ORDER BY prediction_date ASC
        """)
        predictions = cursor.fetchall()

        # If no predictions yet, generate 7-day default forecast
        if not predictions and bundle:
            try:
                res = generate_future_forecast(7)
                cursor.execute("SELECT * FROM predictions ORDER BY prediction_date ASC")
                predictions = cursor.fetchall()
            except Exception as f_err:
                print("Forecast generation error:", f_err)

        # Recent daily sales history (last 30 days)
        cursor.execute("""
            SELECT date, daily_sales, invoice_count, day_of_week, is_weekend, lag_sales, rolling_avg
            FROM sales_data
            ORDER BY date DESC
            LIMIT 30
        """)
        recent_daily_sales = cursor.fetchall()

        # Total historical observations count
        cursor.execute("SELECT COUNT(*), MIN(date), MAX(date), SUM(daily_sales) FROM sales_data")
        summary_row = cursor.fetchone()
        data_summary = {
            'total_days': summary_row[0] or 0,
            'start_date': summary_row[1] or 'N/A',
            'end_date': summary_row[2] or 'N/A',
            'total_sales': round(float(summary_row[3] or 0.0), 2)
        }
    finally:
        conn.close()

    return render_template(
        'analytics.html',
        bundle=bundle,
        predictions=predictions,
        recent_daily_sales=recent_daily_sales,
        data_summary=data_summary
    )

@analytics_bp.route('/retrain', methods=['POST'])
def retrain():
    try:
        # Re-aggregate sales data from historical invoices
        aggregate_daily_sales()
        # Train Multiple Linear Regression
        bundle = train_sales_model(force_retrain=True)
        # Re-generate default 7-day future predictions
        generate_future_forecast(7)
        flash(f"Multiple Linear Regression retrained successfully! R²: {bundle['metrics']['r2']}, RMSE: Rs. {bundle['metrics']['rmse']:.2f}", "success")
    except Exception as e:
        flash(f"Model retraining failed: {str(e)}", "danger")

    return redirect(url_for('analytics.index'))

@analytics_bp.route('/forecast', methods=['POST'])
def update_forecast():
    horizon_str = request.form.get('horizon_days', '7').strip()
    try:
        horizon = int(horizon_str)
        if horizon < 1 or horizon > 60:
            horizon = 7
    except ValueError:
        horizon = 7

    try:
        result = generate_future_forecast(horizon)
        flash(f"Generated {len(result['forecast'])}-day future sales forecast using Multiple Linear Regression.", "success")
    except Exception as e:
        flash(f"Forecast generation failed: {str(e)}", "danger")

    return redirect(url_for('analytics.index'))

@analytics_bp.route('/api/chart-data', methods=['GET'])
def chart_data():
    """
    Returns structured JSON data for Chart.js visualizations:
    1. Historical daily sales trend
    2. Actual vs Predicted comparison on test set
    3. Future forecast line
    """
    conn = get_db()
    try:
        cursor = conn.cursor()
        
        # 1. Historical daily sales (last 60 days for smooth chart rendering)
        cursor.execute("""
            SELECT date, daily_sales FROM sales_data 
            ORDER BY date DESC LIMIT 60
        """)
        hist_rows = cursor.fetchall()[::-1]  # Chronological order
        historical = {
            'labels': [r['date'] for r in hist_rows],
            'sales': [round(float(r['daily_sales']), 2) for r in hist_rows]
        }

        # 2. Future predictions
        cursor.execute("""
            SELECT prediction_date, predicted_sales 
            FROM predictions 
            ORDER BY prediction_date ASC
        """)
        pred_rows = cursor.fetchall()
        forecast = {
            'labels': [r['prediction_date'] for r in pred_rows],
            'sales': [round(float(r['predicted_sales']), 2) for r in pred_rows]
        }

        # 3. Model test evaluation comparison
        bundle = load_sales_model()
        test_comp = bundle.get('test_comparison', [])
        # Sample last 30 test days for chart clarity
        if len(test_comp) > 30:
            test_comp = test_comp[-30:]

        evaluation = {
            'labels': [x['date'] for x in test_comp],
            'actual': [x['actual'] for x in test_comp],
            'predicted': [x['predicted'] for x in test_comp]
        }

        return jsonify({
            'historical': historical,
            'forecast': forecast,
            'evaluation': evaluation
        })
    finally:
        conn.close()

@analytics_bp.route('/download/historical-dataset', methods=['GET'])
def download_historical_dataset():
    """Provides downloadable CSV file of Dataset A (3,000 synthetic Indian invoice records)."""
    if not os.path.exists(Config.HISTORICAL_CSV_PATH):
        generate_historical_dataset()
    return send_file(
        Config.HISTORICAL_CSV_PATH,
        as_attachment=True,
        download_name='historical_invoices_3000.csv',
        mimetype='text/csv'
    )

@analytics_bp.route('/download/daily-dataset', methods=['GET'])
def download_daily_dataset():
    """Provides downloadable CSV file of Dataset B (daily aggregated sales observations)."""
    if not os.path.exists(Config.DAILY_SALES_CSV_PATH):
        aggregate_daily_sales()
    return send_file(
        Config.DAILY_SALES_CSV_PATH,
        as_attachment=True,
        download_name='daily_sales_aggregated.csv',
        mimetype='text/csv'
    )

