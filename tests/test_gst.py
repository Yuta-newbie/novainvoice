import unittest
from utils.validators import calculate_gst_breakdown, round_currency

class TestGSTCalculations(unittest.TestCase):
    def test_intra_state_gst_5_percent(self):
        """Intra-state with 5% GST splits into 2.5% CGST and 2.5% SGST."""
        res = calculate_gst_breakdown(1000.0, 5.0, is_inter_state=False)
        self.assertEqual(res['taxable_amount'], 1000.0)
        self.assertEqual(res['cgst_amount'], 25.0)
        self.assertEqual(res['sgst_amount'], 25.0)
        self.assertEqual(res['igst_amount'], 0.0)
        self.assertEqual(res['tax_amount'], 50.0)
        self.assertEqual(res['total_amount'], 1050.0)

    def test_intra_state_gst_18_percent(self):
        """Intra-state with 18% GST splits into 9% CGST and 9% SGST."""
        res = calculate_gst_breakdown(2500.0, 18.0, is_inter_state=False)
        self.assertEqual(res['cgst_amount'], 225.0)
        self.assertEqual(res['sgst_amount'], 225.0)
        self.assertEqual(res['igst_amount'], 0.0)
        self.assertEqual(res['tax_amount'], 450.0)
        self.assertEqual(res['total_amount'], 2950.0)

    def test_inter_state_gst_18_percent(self):
        """Inter-state with 18% GST applies 18% IGST only."""
        res = calculate_gst_breakdown(2500.0, 18.0, is_inter_state=True)
        self.assertEqual(res['cgst_amount'], 0.0)
        self.assertEqual(res['sgst_amount'], 0.0)
        self.assertEqual(res['igst_amount'], 450.0)
        self.assertEqual(res['tax_amount'], 450.0)
        self.assertEqual(res['total_amount'], 2950.0)

    def test_inter_state_gst_12_percent(self):
        """Inter-state with 12% GST applies 12% IGST only."""
        res = calculate_gst_breakdown(1250.0, 12.0, is_inter_state=True)
        self.assertEqual(res['cgst_amount'], 0.0)
        self.assertEqual(res['sgst_amount'], 0.0)
        self.assertEqual(res['igst_amount'], 150.0)
        self.assertEqual(res['total_amount'], 1400.0)

    def test_decimal_rounding_precision(self):
        """Verifies rounding to 2 decimal places."""
        res = calculate_gst_breakdown(333.33, 18.0, is_inter_state=False)
        # 333.33 * 9% = 29.9997 -> rounds to 30.00
        self.assertEqual(res['cgst_amount'], 30.0)
        self.assertEqual(res['sgst_amount'], 30.0)
        self.assertEqual(res['tax_amount'], 60.0)
        self.assertEqual(res['total_amount'], 393.33)

if __name__ == '__main__':
    unittest.main()

