import os
from datetime import datetime, timedelta
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from config import Config
from database.db import get_db
from utils.sales_data import aggregate_daily_sales

FEATURE_COLUMNS = [
    'day_number',
    'year',
    'month',
    'day_of_week',
    'is_weekend',
    'previous_day_sales',
    'previous_7_day_average'
]

TARGET_COLUMN = 'daily_sales'

def train_sales_model(force_retrain=False):
    """
    Loads daily sales dataset, performs chronological train/test split (80/20),
    trains Multiple Linear Regression using scikit-learn, evaluates model on unseen test set,
    and serializes the trained model bundle to models/sales_model.pkl.
    """
    os.makedirs(os.path.dirname(Config.MODEL_PATH), exist_ok=True)

    # Check if model already exists and we are not forcing retrain
    if not force_retrain and os.path.exists(Config.MODEL_PATH):
        try:
            bundle = joblib.load(Config.MODEL_PATH)
            return bundle
        except Exception:
            pass

    # Ensure daily sales data is loaded
    if not os.path.exists(Config.DAILY_SALES_CSV_PATH):
        aggregate_daily_sales()

    df = pd.read_csv(Config.DAILY_SALES_CSV_PATH)
    if len(df) < 30:
        raise ValueError("Insufficient daily sales data for reliable ML training (minimum 30 observations required).")

    # Sort strictly chronologically
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)

    # Prepare X and y
    X = df[FEATURE_COLUMNS]
    y = df[TARGET_COLUMN]

    # Chronological 80/20 split (NO shuffling!)
    split_idx = int(len(df) * (1 - Config.ML_TEST_SPLIT_RATIO))
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    dates_train = df['date'].iloc[:split_idx].dt.strftime('%Y-%m-%d').tolist()
    dates_test = df['date'].iloc[split_idx:].dt.strftime('%Y-%m-%d').tolist()

    # Train Multiple Linear Regression
    model = LinearRegression()
    model.fit(X_train, y_train)

    # Predict on unseen test set
    y_pred_test = model.predict(X_test)
    y_pred_test = np.maximum(0.0, np.round(y_pred_test, 2))

    # Calculate actual scikit-learn evaluation metrics
    mae = float(mean_absolute_error(y_test, y_pred_test))
    mse = float(mean_squared_error(y_test, y_pred_test))
    rmse = float(np.sqrt(mse))
    r2 = float(r2_score(y_test, y_pred_test))

    # Feature coefficients dictionary
    coefficients = {feat: round(float(coef), 4) for feat, coef in zip(FEATURE_COLUMNS, model.coef_)}
    intercept = round(float(model.intercept_), 4)

    # Test set comparison for visualization
    test_comparison = []
    for d, act, pred in zip(dates_test, y_test, y_pred_test):
        test_comparison.append({
            'date': d,
            'actual': round(float(act), 2),
            'predicted': round(float(pred), 2),
            'residual': round(float(act - pred), 2)
        })

    bundle = {
        'model': model,
        'algorithm': 'Multiple Linear Regression',
        'features': FEATURE_COLUMNS,
        'target': TARGET_COLUMN,
        'metrics': {
            'mae': round(mae, 2),
            'mse': round(mse, 2),
            'rmse': round(rmse, 2),
            'r2': round(r2, 4)
        },
        'coefficients': coefficients,
        'intercept': intercept,
        'total_samples': len(df),
        'train_samples': len(X_train),
        'test_samples': len(X_test),
        'trained_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'test_comparison': test_comparison
    }

    joblib.dump(bundle, Config.MODEL_PATH)
    return bundle

def load_sales_model():
    """Loads existing trained model bundle or trains a new one if missing."""
    if os.path.exists(Config.MODEL_PATH):
        try:
            return joblib.load(Config.MODEL_PATH)
        except Exception:
            pass
    return train_sales_model(force_retrain=True)

def generate_future_forecast(horizon_days=7):
    """
    Generates multi-step recursive future sales forecast for the next `horizon_days`
    using the trained Multiple Linear Regression model.
    Guarantees:
      - Uses actual historical sales values for the initial lag & rolling window.
      - Recursively updates lag and 7-day rolling average using predicted values.
      - Never fabricates numbers.
      - Saves forecast in predictions table.
    """
    if horizon_days < 1 or horizon_days > 60:
        horizon_days = Config.DEFAULT_FORECAST_HORIZON

    bundle = load_sales_model()
    model = bundle['model']

    # Load recent daily sales data
    if not os.path.exists(Config.DAILY_SALES_CSV_PATH):
        aggregate_daily_sales()

    df = pd.read_csv(Config.DAILY_SALES_CSV_PATH)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)

    last_row = df.iloc[-1]
    last_date = last_row['date']
    last_day_number = int(last_row['day_number'])

    # Keep a running list of recent sales (at least last 7 days) to compute rolling averages
    recent_sales = df['daily_sales'].tail(14).tolist()

    forecast_results = []
    conn = get_db()
    cursor = conn.cursor()

    try:
        # Clear previous predictions to keep table clean for current forecast session
        cursor.execute("DELETE FROM predictions")

        for i in range(1, horizon_days + 1):
            target_date = last_date + timedelta(days=i)
            target_date_str = target_date.strftime('%Y-%m-%d')

            day_number = last_day_number + i
            year = target_date.year
            month = target_date.month
            day_of_week = target_date.weekday()
            is_weekend = 1 if day_of_week in [5, 6] else 0

            # Lag features from recent sales window
            prev_day_sales = float(recent_sales[-1])
            prev_7_day_avg = float(np.mean(recent_sales[-7:]))

            X_future = pd.DataFrame([{
                'day_number': day_number,
                'year': year,
                'month': month,
                'day_of_week': day_of_week,
                'is_weekend': is_weekend,
                'previous_day_sales': prev_day_sales,
                'previous_7_day_average': prev_7_day_avg
            }])[FEATURE_COLUMNS]

            pred_val = float(model.predict(X_future)[0])
            pred_val = max(0.0, round(pred_val, 2))

            # Append to running window for recursive multi-step forecasting
            recent_sales.append(pred_val)

            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            forecast_item = {
                'date': target_date_str,
                'day_name': day_names[day_of_week],
                'predicted_sales': pred_val,
                'is_weekend': is_weekend,
                'lag_used': round(prev_day_sales, 2),
                'rolling_avg_used': round(prev_7_day_avg, 2),
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            forecast_results.append(forecast_item)

            # Persist to predictions table
            metric_str = f"R2={bundle['metrics']['r2']}, RMSE={bundle['metrics']['rmse']}"
            cursor.execute("""
                INSERT INTO predictions (prediction_date, predicted_sales, model_metric, algorithm, generated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                target_date_str,
                pred_val,
                metric_str,
                'Multiple Linear Regression',
                forecast_item['generated_at']
            ))

        conn.commit()
    finally:
        conn.close()

    return {
        'forecast': forecast_results,
        'model_info': {
            'algorithm': bundle['algorithm'],
            'metrics': bundle['metrics'],
            'trained_at': bundle['trained_at'],
            'coefficients': bundle['coefficients'],
            'intercept': bundle['intercept']
        }
    }

