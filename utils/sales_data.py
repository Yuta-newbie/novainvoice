import os
import random
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from config import Config
from database.db import get_db

def generate_historical_dataset(csv_path=None, num_records=3000, seed=42):
    """
    Generates a reproducible synthetic dataset of Indian invoice records.
    Contains exactly num_records (default 3000) and exactly 19 meaningful columns.
    Saves to data/historical_invoices.csv (Dataset A).
    """
    if csv_path is None:
        csv_path = Config.HISTORICAL_CSV_PATH
        
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    
    # If file already exists and has num_records, preserve it
    if os.path.exists(csv_path):
        try:
            existing_df = pd.read_csv(csv_path)
            if len(existing_df) == num_records and len(existing_df.columns) >= 18:
                return existing_df
        except Exception:
            pass

    random.seed(seed)
    np.random.seed(seed)

    indian_companies = [
        ("Sharma Retail & General Store", "Uttar Pradesh", "09AABCS1429B1Z1"),
        ("Verma Provision Store", "Delhi", "07AAECV3456C1Z4"),
        ("Gupta Wholesale Mart", "Uttar Pradesh", "09AADCG9876E1Z8"),
        ("Sunrise Mart & Supermarket", "Haryana", "06AALCS5678H1Z2"),
        ("Patel Kirana & Provisions", "Gujarat", "24AAACP4567M1Z6"),
        ("Reddy Spices & Staples", "Telangana", "36AABCR1234N1Z7"),
        ("Mehta Brothers Trading Co.", "Maharashtra", "27AAECM7890P1Z9"),
        ("Nair Organic & Agro Foods", "Kerala", "32AAACN5432Q1Z3"),
        ("Singh Agri & Grain Traders", "Punjab", "03AAECS6789R1Z5"),
        ("Agarwal Sweets & Dry Fruits", "Rajasthan", "08AAACA9876S1Z1"),
        ("Choudhury Commercials", "West Bengal", "19AAACC4321T1Z4"),
        ("Kalyan Departmental Store", "Tamil Nadu", "33AAECK8765U1Z8"),
        ("Bansal Provisions & Flour", "Uttar Pradesh", "09AAECB1122V1Z2"),
        ("Apex Daily Needs Supermart", "Delhi", "07AAACA3344W1Z9"),
        ("Goyal Food Distributors", "Uttar Pradesh", "09AAACG5566X1Z3")
    ]

    categories = [
        "Groceries & Staples",
        "Edible Oils & Dairy",
        "Beverages & Spices",
        "Dry Fruits & Premium Nuts",
        "Organic & Specialty Foods"
    ]
    
    gst_rates = [5.0, 12.0, 18.0]
    payment_statuses = ["Paid", "Paid", "Paid", "Pending", "Partial"]
    payment_methods = ["UPI", "UPI", "Bank Transfer", "Cash", "Credit Card"]

    # Spanning 700 days from 2024-01-01 to ~2025-12-01
    start_date = datetime(2024, 1, 1)
    total_days = 700

    # Distribute 3000 invoices chronologically across total_days with slight weekly seasonal variation
    date_pool = []
    current_dt = start_date
    for day_idx in range(total_days):
        dt = start_date + timedelta(days=day_idx)
        # Weekends have slightly more transactions
        weight = 5 if dt.weekday() in (5, 6) else 4
        # Seasonality: month end or festive season (Oct, Nov) has slight boost
        if dt.month in (10, 11):
            weight += 1
        date_pool.extend([dt] * weight)
        
    sampled_dates = sorted(random.choices(date_pool, k=num_records))

    rows = []
    base_state = Config.COMPANY_STATE

    for i in range(num_records):
        inv_id = f"INV-HIST-{i+1:04d}"
        cust_idx = i % len(indian_companies)
        cust_name, cust_state, cust_gstin = indian_companies[cust_idx]
        cust_id = f"CUST-{(cust_idx + 101):03d}"
        inv_date = sampled_dates[i].strftime("%Y-%m-%d")
        category = random.choice(categories)
        item_count = random.randint(1, 8)
        total_quantity = item_count * random.randint(2, 6)
        
        # Base taxable amount with realistic variance and weekly pattern
        day_of_week = sampled_dates[i].weekday()
        weekend_boost = 1.25 if day_of_week in (5, 6) else 1.0
        taxable_amt = round(random.uniform(2500, 18000) * weekend_boost, 2)
        
        gst_rate = random.choice(gst_rates)
        is_inter_state = 1 if cust_state != base_state else 0
        
        if is_inter_state == 1:
            cgst = 0.0
            sgst = 0.0
            igst = round(taxable_amt * (gst_rate / 100.0), 2)
        else:
            cgst = round(taxable_amt * (gst_rate / 200.0), 2)
            sgst = round(taxable_amt * (gst_rate / 200.0), 2)
            igst = 0.0
            
        total_tax = round(cgst + sgst + igst, 2)
        inv_total = round(taxable_amt + total_tax, 2)
        
        status = random.choice(payment_statuses)
        method = random.choice(payment_methods)

        # 19 columns exactly
        rows.append({
            "invoice_id": inv_id,
            "customer_id": cust_id,
            "customer_name": cust_name,
            "customer_state": cust_state,
            "customer_gstin": cust_gstin,
            "invoice_date": inv_date,
            "product_category": category,
            "item_count": item_count,
            "total_quantity": total_quantity,
            "taxable_amount": taxable_amt,
            "gst_rate_avg": gst_rate,
            "is_inter_state": is_inter_state,
            "cgst_amount": cgst,
            "sgst_amount": sgst,
            "igst_amount": igst,
            "total_tax": total_tax,
            "invoice_total": inv_total,
            "payment_status": status,
            "payment_method": method
        })

    df = pd.DataFrame(rows)
    df.to_csv(csv_path, index=False)
    return df

def aggregate_daily_sales(invoice_df=None, output_csv_path=None):
    """
    Transforms invoice-level records into chronological daily sales observations (Dataset B).
    Performs feature engineering strictly without data leakage:
      - day_number: sequential integer day
      - year: calendar year
      - month: calendar month
      - day_of_week: 0=Mon, ..., 6=Sun
      - is_weekend: 1 if Saturday/Sunday else 0
      - previous_day_sales: lag 1 shifted by 1 day
      - previous_7_day_average: 7-day rolling average shifted by 1 day
    Saves to data/daily_sales.csv and syncs into database table sales_data.
    """
    if invoice_df is None:
        if not os.path.exists(Config.HISTORICAL_CSV_PATH):
            generate_historical_dataset()
        invoice_df = pd.read_csv(Config.HISTORICAL_CSV_PATH)
        
    if output_csv_path is None:
        output_csv_path = Config.DAILY_SALES_CSV_PATH

    # Clean and validate dates
    df = invoice_df.copy()
    
    # Dynamic column mapping to accommodate synthetic dataset variations
    date_col = 'invoice_date' if 'invoice_date' in df.columns else 'date'
    taxable_col = 'taxable_amount_inr' if 'taxable_amount_inr' in df.columns else (
        'taxable_amount' if 'taxable_amount' in df.columns else (
            'invoice_total_inr' if 'invoice_total_inr' in df.columns else 'invoice_total'
        )
    )
    id_col = 'invoice_number' if 'invoice_number' in df.columns else (
        'invoice_id' if 'invoice_id' in df.columns else df.columns[0]
    )

    df['parsed_date'] = pd.to_datetime(df[date_col], errors='coerce')
    df = df.dropna(subset=['parsed_date', taxable_col])
    
    # Aggregate by date
    daily = df.groupby('parsed_date').agg(
        daily_sales=(taxable_col, 'sum'),
        invoice_count=(id_col, 'count')
    ).reset_index()

    daily = daily.sort_values('parsed_date').reset_index(drop=True)

    # Reindex over complete date range so missing days are represented with 0 sales
    full_idx = pd.date_range(start=daily['parsed_date'].min(), end=daily['parsed_date'].max(), freq='D')
    daily = daily.set_index('parsed_date').reindex(full_idx, fill_value=0).reset_index()
    daily = daily.rename(columns={'index': 'date'})
    daily['date_str'] = daily['date'].dt.strftime('%Y-%m-%d')

    # Calendar features
    daily['day_number'] = np.arange(1, len(daily) + 1)
    daily['year'] = daily['date'].dt.year
    daily['month'] = daily['date'].dt.month
    try:
        daily['day_of_week'] = daily['date'].dt.day_of_week
    except AttributeError:
        daily['day_of_week'] = daily['date'].dt.dayofweek
    daily['is_weekend'] = daily['day_of_week'].apply(lambda x: 1 if x in [5, 6] else 0)

    # STRICT LAG & ROLLING FEATURES (Shifted by 1 to prevent data leakage)
    daily['previous_day_sales'] = daily['daily_sales'].shift(1)
    daily['previous_7_day_average'] = daily['daily_sales'].shift(1).rolling(window=7, min_periods=1).mean()

    # Drop the initial row with NaN from lag-1
    daily_clean = daily.dropna().copy().reset_index(drop=True)
    
    # Round numerical metrics
    daily_clean['daily_sales'] = daily_clean['daily_sales'].round(2)
    daily_clean['previous_day_sales'] = daily_clean['previous_day_sales'].round(2)
    daily_clean['previous_7_day_average'] = daily_clean['previous_7_day_average'].round(2)

    # Save to Dataset B CSV
    export_df = daily_clean[[
        'date_str', 'daily_sales', 'invoice_count', 'day_of_week', 
        'is_weekend', 'day_number', 'year', 'month', 
        'previous_day_sales', 'previous_7_day_average'
    ]].rename(columns={'date_str': 'date'})
    
    export_df.to_csv(output_csv_path, index=False)

    # Sync into SQLite database sales_data table
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sales_data")
        records = [
            (
                row['date'], float(row['daily_sales']), int(row['invoice_count']),
                int(row['day_of_week']), int(row['is_weekend']), int(row['day_number']),
                int(row['year']), int(row['month']), float(row['previous_day_sales']),
                float(row['previous_7_day_average'])
            )
            for _, row in export_df.iterrows()
        ]
        cursor.executemany("""
            INSERT OR REPLACE INTO sales_data 
            (date, daily_sales, invoice_count, day_of_week, is_weekend, day_number, year, month, lag_sales, rolling_avg)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, records)
        conn.commit()
    finally:
        conn.close()

    return export_df
