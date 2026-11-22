import unittest
import os
import pandas as pd
from utils.sales_data import generate_historical_dataset, aggregate_daily_sales
from utils.ml_model import train_sales_model, generate_future_forecast, FEATURE_COLUMNS
from config import Config

class TestMachineLearningModule(unittest.TestCase):
    def test_historical_dataset_structure(self):
        """Dataset A must contain exactly 3,000 records and exactly 19 columns."""
        df = generate_historical_dataset()
        self.assertEqual(len(df), 3000, f"Expected 3000 records, got {len(df)}")
        self.assertEqual(len(df.columns), 19, f"Expected 19 columns, got {len(df.columns)}")

        # Verify key fields (accepting either schema variant)
        id_field_present = ('invoice_id' in df.columns) or ('invoice_number' in df.columns)
        self.assertTrue(id_field_present, "Missing invoice identifier column (invoice_id or invoice_number)")
        self.assertIn('customer_id', df.columns)
        self.assertIn('customer_name', df.columns)
        self.assertIn('customer_gstin', df.columns)
        self.assertIn('invoice_date', df.columns)
        taxable_present = ('taxable_amount' in df.columns) or ('taxable_amount_inr' in df.columns)
        self.assertTrue(taxable_present, "Missing taxable amount column")
        total_present = ('invoice_total' in df.columns) or ('invoice_total_inr' in df.columns)
        self.assertTrue(total_present, "Missing invoice total column")
        self.assertIn('payment_status', df.columns)
        self.assertIn('payment_method', df.columns)

    def test_daily_sales_aggregation_and_features(self):
        """Dataset B must contain chronological daily sales and non-leaking features."""
        df = aggregate_daily_sales()
        self.assertGreater(len(df), 100)

        # Check required ML feature columns
        for col in FEATURE_COLUMNS:
            self.assertIn(col, df.columns, f"Feature {col} missing from daily sales dataset")

        # Verify lag_sales is shifted by 1 (no lookahead leakage)
        # For any row i > 0: previous_day_sales[i] should equal daily_sales[i-1]
        for i in range(1, min(10, len(df))):
            self.assertAlmostEqual(df.iloc[i]['previous_day_sales'], df.iloc[i-1]['daily_sales'], places=1)

    def test_model_training_and_evaluation_metrics(self):
        """LinearRegression must train on chronological split and return actual metrics."""
        bundle = train_sales_model(force_retrain=True)
        self.assertIsNotNone(bundle)
        self.assertEqual(bundle['algorithm'], 'Multiple Linear Regression')

        metrics = bundle['metrics']
        self.assertIn('mae', metrics)
        self.assertIn('mse', metrics)
        self.assertIn('rmse', metrics)
        self.assertIn('r2', metrics)

        # Verify metrics are real non-zero numbers
        self.assertGreater(metrics['mae'], 0)
        self.assertGreater(metrics['rmse'], 0)
        self.assertIsInstance(metrics['r2'], float)

    def test_future_sales_forecasting(self):
        """Forecast function must generate 7 non-negative daily predictions."""
        result = generate_future_forecast(horizon_days=7)
        forecast = result['forecast']
        self.assertEqual(len(forecast), 7)

        for item in forecast:
            self.assertIn('date', item)
            self.assertIn('predicted_sales', item)
            self.assertGreaterEqual(item['predicted_sales'], 0.0)

if __name__ == '__main__':
    unittest.main()

