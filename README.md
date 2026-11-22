# NovaInvoice

## Smart Invoice Generator with Machine Learning-Based Future Sales Prediction

### Academic Mini-Project — Bachelor of Computer Applications (BCA)

---

## 1. Project Overview

NovaInvoice is an end-to-end web-based billing, inventory management, and sales forecasting software system designed for small and medium businesses, retail shops, and wholesale distributors in India.

The application integrates two essential business capabilities:
1. **Invoice & Business Operations:** Customer relationship management, real-time product inventory tracking with low-stock alerts, GST-compliant tax invoicing (supporting both Intra-State CGST+SGST and Inter-State IGST taxation), and server-side PDF invoice generation using ReportLab.
2. **Machine Learning Sales Intelligence:** A machine learning pipeline powered by `scikit-learn` that cleans historical billing records, aggregates transactions into daily sales observations, engineers calendar and lag features without lookahead data leakage, and trains a Multiple Linear Regression model (`LinearRegression`) on a chronological 80/20 train/test split to forecast future daily sales.

The software runs locally without requiring paid third-party APIs, external cloud dependencies, or remote accounts.

---

## 2. Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| Language | Python 3.14 / 3.x | Core programming language |
| Web Backend | Flask | Modular microframework with Blueprints |
| Database | SQLite 3 | Relational database with foreign key enforcement |
| Frontend | HTML5, CSS3, JavaScript | Responsive client interface |
| CSS Framework | Bootstrap 5.3 | Responsive grid system and utility classes |
| PDF Generation | ReportLab | Server-side printable GST tax invoice generator |
| Machine Learning | scikit-learn (`LinearRegression`) | Multiple Linear Regression model training & evaluation |
| Data Processing | pandas, NumPy | Chronological aggregation and feature engineering |
| Data Visualization | Chart.js | Interactive charts for sales trends and forecasts |
| Model Persistence | joblib | Serialization of trained regression bundle |

---

## 3. System Architecture & Directory Structure

```text
NovaInvoice/
│
├── app.py                      # Application entry point & factory
├── config.py                   # Centralized configuration & business profile
├── requirements.txt            # Python dependency specification
├── README.md                   # Academic project documentation
│
├── database/
│   ├── schema.sql              # Relational SQLite schema definition
│   ├── db.py                   # Database connection helper & seed manager
│   ├── seed_demo.py            # Script to seed demo invoices
│   └── invoice.db              # SQLite relational database file
│
├── data/
│   ├── historical_invoices.csv # Dataset A: 3,000 synthetic Indian invoice records (19 columns)
│   └── daily_sales.csv         # Dataset B: Chronological daily sales with lag features
│
├── models/
│   └── sales_model.pkl         # Serialized Multiple Linear Regression model bundle
│
├── utils/
│   ├── validators.py           # Phone, email, GSTIN, and GST calculation engine
│   ├── sales_data.py           # Dataset generator, aggregation, & feature engineering
│   ├── ml_model.py             # Model training, chronological evaluation, & forecasting
│   └── pdf_generator.py        # ReportLab GST Tax Invoice PDF generation
│
├── routes/
│   ├── dashboard.py            # KPI overview, recent records, and quick predictions
│   ├── customers.py            # Customer CRUD, search, and integrity protection
│   ├── products.py             # Product inventory CRUD and stock adjustment
│   ├── invoices.py             # Atomic invoice transactions & stock deduction
│   └── analytics.py            # Model metrics, regression weights, and forecast UI
│
├── templates/
│   ├── base.html               # Base layout with sidebar and dark mocha styling
│   ├── dashboard.html          # Executive dashboard with KPIs and mini trend chart
│   ├── customers.html          # Customer list and search
│   ├── customer_form.html      # Customer creation and editing form
│   ├── customer_view.html      # Customer profile and purchase history
│   ├── products.html           # Product catalog with stock levels and thresholds
│   ├── product_form.html       # Product creation and editing form
│   ├── invoices.html           # Invoice registry with date and status filters
│   ├── create_invoice.html     # Dynamic invoice generator with live GST calculation
│   ├── invoice_details.html    # Full invoice view with print and download options
│   ├── analytics.html          # Sales analytics and machine learning dashboard
│   ├── 404.html                # Not Found error page
│   └── 500.html                # Server Error error page
│
├── static/
│   ├── css/
│   │   └── style.css           # Dark warm mocha & bronze aesthetic stylesheet
│   └── js/
│       ├── main.js             # Dynamic invoice row calculator and UI events
│       └── charts.js           # Chart.js rendering for historical & predicted sales
│
├── generated_invoices/         # Saved PDF invoices
│
└── tests/
    ├── test_gst.py             # Unit tests for Intra/Inter-state GST calculations
    ├── test_customers.py       # Unit tests for customer validation and CRUD
    ├── test_products.py        # Unit tests for product inventory and stock limits
    ├── test_invoices.py        # Unit tests for atomic invoices and stock restoration
    ├── test_ml.py              # Unit tests for dataset structure and ML pipeline
    └── test_routes.py          # Integration tests for Flask endpoints
```

---

## 4. Database Schema Design

The SQLite database enforces foreign key constraints (`PRAGMA foreign_keys = ON;`) across seven core relational tables:

1. **`customers`**: Stores client contact details, state, and 15-character GSTIN.
2. **`products`**: Stores product details, taxable unit price, GST rate, stock quantity, and minimum stock threshold.
3. **`invoices`**: Stores unique invoice numbers, customer reference, invoice date, inter-state flag, taxable subtotal, CGST, SGST, IGST, grand total, payment status, and payment mode.
4. **`invoice_items`**: Child table referencing `invoices` with cascading deletion. Stores product reference, quantity, price, GST rate, taxable amount, tax amount, and line total.
5. **`sales_data`**: Stores daily aggregated taxable sales, invoice counts, calendar features, and engineered lag/rolling features.
6. **`predictions`**: Stores future sales forecasts generated by the trained regression model with timestamp and algorithm metadata.
7. **`company_settings`**: Stores company name, address, GSTIN, and base state for tax jurisdiction determination.

---

## 5. Machine Learning Methodology

### 5.1 Problem Classification
- **Type:** Supervised Regression.
- **Target Variable ($y$):** Daily taxable sales amount in Indian Rupees (INR).
- **Algorithm:** Multiple Linear Regression (`sklearn.linear_model.LinearRegression`).

### 5.2 Datasets
- **Dataset A (`data/historical_invoices.csv`):** Exactly 3,000 synthetic Indian invoice-level records across 19 meaningful fields (Invoice ID, Customer ID, Customer Name, Customer State, GSTIN, Invoice Date, Product Category, Item Count, Total Quantity, Taxable Amount, GST Rate, Inter-State Flag, CGST Amount, SGST Amount, IGST Amount, Total Tax, Invoice Total, Payment Status, Payment Method).
- **Dataset B (`data/daily_sales.csv`):** Daily aggregated observation records sorted chronologically over ~700 days.

### 5.3 Feature Engineering (Data Leakage Prevention)
To ensure the model never uses future information to predict the present:
- `day_number`: Sequential integer day index.
- `year`: Calendar year.
- `month`: Calendar month (1–12) for seasonality.
- `day_of_week`: Day index (0 for Monday, ..., 6 for Sunday).
- `is_weekend`: Binary flag (1 if Saturday or Sunday, else 0).
- `previous_day_sales`: Daily taxable sales strictly shifted by 1 day ($y_{t-1}$).
- `previous_7_day_average`: 7-day rolling average of sales strictly shifted by 1 day ($\frac{1}{7} \sum_{i=1}^{7} y_{t-i}$).

### 5.4 Chronological Train/Test Partitioning
Sales data is chronological time-series data. Random shuffling is strictly avoided because it causes temporal data leakage. An 80% chronological training partition is used for model training, and the final 20% unseen chronological observations are used exclusively for testing.

### 5.5 Model Evaluation Metrics
Evaluated on the unseen test set using standard scikit-learn metrics:
- **Mean Absolute Error (MAE):** Average magnitude of prediction errors in Rupees.
- **Mean Squared Error (MSE):** Average of squared prediction errors.
- **Root Mean Squared Error (RMSE):** Standard deviation of prediction residuals in Rupees.
- **R-Squared ($R^2$):** Coefficient of determination measuring proportion of sales variance captured.

### 5.6 Recursive Multi-Step Future Forecasting
For forecasting future days $t = 1 \dots H$:
1. Calendar features (`day_number`, `year`, `month`, `day_of_week`, `is_weekend`) are derived from the future calendar date.
2. For day 1, actual last-known sales and historical 7-day rolling averages are used.
3. For subsequent days $t \ge 2$, previous predicted sales are recursively fed into the lag and rolling window.
4. Non-negative constraints (`max(0.0, prediction)`) ensure realistic predictions.

---

## 6. Installation & Execution Guide (Windows)

### Prerequisites
- Python 3.10+ (Python 3.12, 3.13, or 3.14 supported).
- Windows Command Prompt or PowerShell.

### Step 1: Clone or Navigate to Project Directory
```powershell
cd "c:\Users\Gaurav Jaiswal\Desktop\BCA 5th Semester\Invoice generator final"
```

### Step 2: Create and Activate Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\activate
```

### Step 3: Install Required Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Run the Application
```powershell
python app.py
```
Upon startup, NovaInvoice automatically:
1. Creates database tables if they do not exist.
2. Seeds initial demo products and customers if tables are empty.
3. Verifies or generates Dataset A (3,000 records, 19 fields).
4. Aggregates Dataset B and syncs daily sales into the database.
5. Trains the Multiple Linear Regression model and prepares default forecasts.

### Step 5: Access the Web Interface
Open your web browser and navigate to:
```text
http://127.0.0.1:5000
```

---

## 7. Running the Automated Test Suite

To run all 20 automated unit and integration tests:

```powershell
.\venv\Scripts\python.exe -m unittest discover tests
```

Expected output:
```text
....................
----------------------------------------------------------------------
Ran 20 tests in 1.083s

OK
```

The test suite validates:
- `test_gst.py`: Intra-state 5%, intra-state 18%, inter-state 18%, inter-state 12%, and 2-decimal rounding.
- `test_customers.py`: Phone validation, email validation, GSTIN format, and customer CRUD.
- `test_products.py`: Product creation, stock adjustments, and low-stock threshold detection.
- `test_invoices.py`: Atomic invoice creation, stock deduction, ReportLab PDF generation, and stock restoration on invoice deletion.
- `test_ml.py`: Dataset A structure (3,000 rows, 19 columns), Dataset B feature engineering, non-leaking lag features, LinearRegression model training, evaluation metrics, and recursive future prediction.
- `test_routes.py`: Flask HTTP endpoints for Dashboard, Customers, Products, Invoices, Analytics, and Chart.js JSON APIs.

---

## 8. Module Walkthrough

### 8.1 Dashboard
- Real-time summary cards: Total Sales, Total Invoices, Total Customers, Total Products, Low Stock Watchlist, and Pending Payments.
- Interactive sales trend chart powered by Chart.js.
- Machine Learning Snapshot card displaying model $R^2$, RMSE error, and next-day predicted sales.
- Recent Invoices table with direct PDF download shortcuts.
- Low-Stock Watchlist alerting users when items reach or drop below their minimum stock threshold.

### 8.2 Customer Management
- List all customers with instant search by name, phone, email, or GSTIN.
- Add or edit customer profile with state selection for GST jurisdiction.
- Delete customer with database integrity protection: prevents deletion if invoices depend on the customer.
- Customer Profile view showing client details and complete invoice purchase history.

### 8.3 Product & Inventory Management
- Real-time product inventory tracking with stock levels and minimum stock thresholds.
- Add and edit products with taxable unit price, GST rate (0%, 5%, 12%, 18%, 28%), and stock thresholds.
- Quick Stock Adjustment modal to add incoming inventory or record stock changes.
- Low-stock filter toggle to view items requiring replenishment.
- Deletion integrity protection: prevents deleting items referenced in existing invoices.

### 8.4 Invoice Generation (Core Module)
- Select customer with automatic detection of customer state vs supplier state (Uttar Pradesh).
- Intra-State vs Inter-State GST logic:
  - If Customer State == Supplier State: Splits GST equally into CGST (Rate/2) and SGST (Rate/2).
  - If Customer State != Supplier State: Applies full GST as IGST.
- Add multiple products dynamically with live client-side price, GST rate, available stock display, and quantity validation.
- Overselling protection: prevents creating invoices exceeding available inventory.
- Server-side recalculation: Python independently validates every amount and rounds with 2-decimal precision.
- Single atomic database transaction: inserts invoice, inserts items, and decrements stock. If any step fails, the transaction rolls back.
- Automatic PDF invoice generation using ReportLab immediately upon invoice creation.

### 8.5 Invoice Registry & History
- Complete invoice registry with search by invoice number or customer name.
- Filter by payment status (Paid, Pending, Partial) and date range.
- View detailed invoice page formatted like a professional tax invoice.
- Download or print PDF invoice.
- Delete invoice with automatic stock restoration: restores purchased product quantities back into inventory within a single atomic database transaction.

### 8.6 Sales Analytics & Machine Learning Dashboard
- Display model evaluation metrics: MAE, MSE, RMSE, and $R^2$.
- Chart 1: Historical daily sales trend from actual billing records.
- Chart 2: Future sales forecast curve with recursive multi-step daily predictions.
- Chart 3: Model Evaluation: Actual vs. Predicted comparison on the 20% unseen test partition.
- Upcoming Predicted Daily Sales table displaying forecast date, predicted sales, and lag metrics.
- Feature Weights and Regression Formula table showing individual coefficients for each feature.
- Retrain Model button to re-aggregate records and re-fit the model.
- Forecast Horizon selector allowing users to generate 7-day, 14-day, or 30-day future forecasts.

---

## 9. Academic Viva Talking Points

When presenting this project for evaluation:
1. **Separation of Concerns:** Notice how the system maintains two separate datasets: Dataset A for invoice-level historical audits, and Dataset B for daily aggregated machine learning.
2. **Preventing Data Leakage:** Lag features and 7-day rolling averages are shifted by 1 day so that today's target $y_t$ is never present in the independent features $X_t$.
3. **Chronological Splitting:** Rather than using random train/test splits that leak future trends into past data, the project strictly uses the first 80% of days for training and the final 20% of unseen days for testing.
4. **Inter-State vs Intra-State GST:** The backend checks the customer's state against the supplier's state to determine whether to compute CGST + SGST or IGST.
5. **Inventory Consistency:** Stock deduction upon invoice creation and stock restoration upon invoice deletion are executed within atomic SQLite transactions.

---

## 10. License

This project was built for academic evaluation purposes as a BCA Mini-Project. Free and open-source dependencies only.

