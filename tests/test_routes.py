import unittest
from app import create_app

class TestFlaskRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()

    def test_dashboard_route(self):
        """Dashboard page loads with status 200."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'NovaInvoice', response.data)
        self.assertIn(b'Executive Dashboard', response.data)

    def test_customers_routes(self):
        """Customer list and form routes load with status 200."""
        resp = self.client.get('/customers/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Customer Directory', resp.data)

        resp_add = self.client.get('/customers/add')
        self.assertEqual(resp_add.status_code, 200)
        self.assertIn(b'Add Customer', resp_add.data)

    def test_products_routes(self):
        """Product list and form routes load with status 200."""
        resp = self.client.get('/products/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Product', resp.data)
        self.assertIn(b'Inventory Catalog', resp.data)

        resp_add = self.client.get('/products/add')
        self.assertEqual(resp_add.status_code, 200)
        self.assertIn(b'Add Product', resp_add.data)

    def test_invoices_routes(self):
        """Invoice list and create routes load with status 200."""
        resp = self.client.get('/invoices/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Invoice Registry', resp.data)

        resp_create = self.client.get('/invoices/create')
        self.assertEqual(resp_create.status_code, 200)
        self.assertIn(b'Create Tax Invoice', resp_create.data)

    def test_analytics_and_api_routes(self):
        """Analytics page and Chart.js JSON API return 200."""
        resp = self.client.get('/analytics/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Sales Analytics', resp.data)
        self.assertIn(b'Multiple Linear Regression', resp.data)

        resp_api = self.client.get('/analytics/api/chart-data')
        self.assertEqual(resp_api.status_code, 200)
        self.assertIn('historical', resp_api.json)
        self.assertIn('forecast', resp_api.json)
        self.assertIn('evaluation', resp_api.json)

    def test_dataset_download_routes(self):
        """Dataset A and B CSV download endpoints return valid CSV files."""
        resp_a = self.client.get('/analytics/download/historical-dataset')
        self.assertEqual(resp_a.status_code, 200)
        self.assertEqual(resp_a.mimetype, 'text/csv')
        self.assertTrue(b'invoice_id' in resp_a.data or b'invoice_number' in resp_a.data)

        resp_b = self.client.get('/analytics/download/daily-dataset')
        self.assertEqual(resp_b.status_code, 200)
        self.assertEqual(resp_b.mimetype, 'text/csv')
        self.assertIn(b'daily_sales', resp_b.data)

if __name__ == '__main__':
    unittest.main()
