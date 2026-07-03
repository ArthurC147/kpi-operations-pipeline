"""
main.py — KPI Operations Pipeline
----------------------------------
Runs the full pipeline end-to-end:
  1. Loads raw customer support ticket data
  2. Cleans and engineers KPI features
  3. Aggregates KPIs and exports the final file

Usage:
  python scripts/main.py

Output:
  data/processed/kpi_processed.csv
"""

# ── Imports ───────────────────────────────────────────────────────────────────
# pandas: the main library for working with tables (DataFrames) in Python
# numpy: used here only for np.nan (representing missing values)
# pathlib: handles file paths in a way that works on Windows, Mac, and Linux
# datetime: used to timestamp when the pipeline ran

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime


# ── Path setup ────────────────────────────────────────────────────────────────
# Path(__file__) is the location of THIS script
# .parent.parent goes up two folders → to the project root
# Then we build the paths to input and output files

PROJECT_ROOT = Path(__file__).parent.parent
RAW_PATH      = PROJECT_ROOT / "data" / "raw"   / "customer_support_tickets.csv"
PROCESSED_PATH= PROJECT_ROOT / "data" / "processed" / "kpi_processed.csv"

# SLA threshold: tickets resolved within this many hours are "within SLA"
# In a real telecom context this would come from a config file, not hardcoded
SLA_HOURS = 48


# ── Step 1: Load ──────────────────────────────────────────────────────────────
def load_data(path: Path) -> pd.DataFrame:
    """
    Reads the raw CSV and prints a quick diagnostic.
    
    Why we do this:
      Before touching any data, we want to know:
        - How many rows and columns?
        - What are the data types?
        - Are there missing values?
    This prevents surprises downstream.
    """
    print(f"\n[1/3] Loading data from: {path}")
    
    df = pd.read_csv(path)
    
    print(f"  → Shape: {df.shape[0]:,} rows × {df.shape[1]} columns")
    print(f"  → Columns: {list(df.columns)}")
    
    # Show missing value counts only for columns that actually have nulls
    nulls = df.isnull().sum()
    nulls = nulls[nulls > 0]
    if len(nulls) > 0:
        print(f"  → Missing values detected:\n{nulls.to_string()}")
    else:
        print("  → No missing values found")
    
    return df


# ── Step 2: Clean & engineer features ────────────────────────────────────────
def clean_and_engineer(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans raw data and creates the KPI columns we need.
    
    Key decisions made here:
      - Column names → standardized to snake_case (no spaces, all lowercase)
      - Dates → parsed to datetime so we can do date math
      - Resolution time → calculated in hours (needed for MTTR and SLA)
      - SLA flag → boolean column: True if resolved within SLA_HOURS
      - CSAT bins → categorical grouping of satisfaction scores (Low/Mid/High)
    """
    print(f"\n[2/3] Cleaning and engineering features...")
    
    # ── 2a. Standardize column names ──────────────────────────────────────────
    # Removes spaces and special characters from column names
    # "Customer ID" → "customer_id", "Ticket Status" → "ticket_status"
    # This makes it much easier to write df.ticket_status instead of df["Ticket Status"]
    
    df.columns = (
        df.columns
          .str.strip()           # remove leading/trailing spaces
          .str.lower()           # TICKET STATUS → ticket status
          .str.replace(" ", "_") # ticket status → ticket_status
          .str.replace(r"[^a-z0-9_]", "", regex=True)  # remove any remaining special chars
    )
    
    print(f"  → Columns after renaming: {list(df.columns)}")
    
    # ── 2b. Parse date columns ────────────────────────────────────────────────
    # We need dates as actual datetime objects, not strings
    # pd.to_datetime() converts "2023-01-15" → Timestamp('2023-01-15 00:00:00')
    # errors="coerce" means: if a value can't be parsed, turn it into NaT (Not a Time)
    # instead of crashing the whole pipeline
    
    date_cols = [c for c in df.columns if "date" in c]
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors="coerce")
        print(f"  → Parsed '{col}' as datetime")
    
    # ── 2c. Calculate resolution time (hours) ─────────────────────────────────
    # We look for a "first response" or "resolution" date and a "created" date
    # The difference gives us how long it took to resolve each ticket
    
    # Try different column name patterns that Kaggle datasets commonly use
    possible_open  = ["date_of_purchase", "created_at", "ticket_created", "first_response_time"]
    possible_close = ["resolution_date", "closed_at", "ticket_resolved", "time_to_resolution"]
    
    open_col  = next((c for c in possible_open  if c in df.columns), None)
    close_col = next((c for c in possible_close if c in df.columns), None)
    
    if open_col and close_col:
        # timedelta in hours: (close_date - open_date) → hours
        df["resolution_hours"] = (
            (df[close_col] - df[open_col])
            .dt.total_seconds() / 3600   # convert seconds → hours
        )
        print(f"  → Calculated 'resolution_hours' from '{open_col}' → '{close_col}'")
    elif "time_to_resolution" in df.columns:
        # The Kaggle dataset stores resolution time as strings like "0 days 15:24:00"
        # pd.to_timedelta() parses this format into a Timedelta object
        # .dt.total_seconds() converts it to float seconds, then we divide by 3600
        raw = df["time_to_resolution"].astype(str)
        df["resolution_hours"] = (
            pd.to_timedelta(raw, errors="coerce").dt.total_seconds() / 3600
        )
        print("  → Parsed 'time_to_resolution' via pd.to_timedelta → resolution_hours")
    else:
        # Fallback: simulate resolution time so the rest of the pipeline still works
        # In a real project, you'd log this as a data quality issue
        print("  → WARNING: Could not find date columns. Simulating resolution_hours.")
        np.random.seed(42)  # seed = reproducible results
        df["resolution_hours"] = np.random.exponential(scale=36, size=len(df))
    
    # ── 2d. SLA compliance flag ────────────────────────────────────────────────
    # A ticket is "within SLA" if it was resolved within SLA_HOURS (default: 48h)
    # This creates a boolean column: True = compliant, False = breach
    # We'll use this to calculate SLA compliance rate in Step 3
    
    df["sla_met"] = df["resolution_hours"] <= SLA_HOURS
    sla_rate = df["sla_met"].mean() * 100
    print(f"  → SLA compliance rate: {sla_rate:.1f}% of tickets resolved within {SLA_HOURS}h")
    
    # ── 2e. CSAT bins ─────────────────────────────────────────────────────────
    # Customer Satisfaction scores (usually 1–5) are more useful as categories
    # for segmentation analysis than as raw numbers
    # pd.cut() divides a continuous variable into labeled buckets
    
    csat_col = next((c for c in df.columns if "satisfaction" in c or "csat" in c or "rating" in c), None)
    
    if csat_col:
        df["csat_bin"] = pd.cut(
            df[csat_col],
            bins=[0, 2, 3, 5],               # 0-2: Low, 3: Mid, 4-5: High
            labels=["Low", "Mid", "High"],
            right=True
        )
        print(f"  → Created 'csat_bin' from '{csat_col}'")
    
    # ── 2f. Handle remaining nulls ────────────────────────────────────────────
    # For numeric columns: fill NaN with the column median (less sensitive to outliers than mean)
    # For text columns: fill NaN with "Unknown" to avoid groupby issues later
    
    for col in df.select_dtypes(include="number").columns:
        if df[col].isnull().any():
            df[col].fillna(df[col].median(), inplace=True)
    
    for col in df.select_dtypes(include="object").columns:
        if df[col].isnull().any():
            df[col].fillna("Unknown", inplace=True)
    
    print(f"  → Nulls after cleaning: {df.isnull().sum().sum()}")
    
    return df


# ── Step 3: Aggregate & export ────────────────────────────────────────────────
def aggregate_and_export(df: pd.DataFrame, output_path: Path) -> pd.DataFrame:
    """
    Computes the final KPI table and saves it to CSV.
    
    The aggregation groups tickets by a dimension (product type or ticket channel)
    and calculates per-group KPIs:
      - MTTR: average resolution time
      - CSAT: average satisfaction score
      - SLA rate: % of tickets within SLA
      - Volume: total tickets in the period
    
    This is the file Power BI will read.
    """
    print(f"\n[3/3] Aggregating KPIs and exporting...")
    
    # Find the best grouping column available in the dataset
    group_candidates = ["product_purchased", "ticket_type", "ticket_channel", "ticket_subject"]
    group_col = next((c for c in group_candidates if c in df.columns), None)
    
    if group_col is None:
        print("  → WARNING: No suitable grouping column found. Exporting cleaned data as-is.")
        df.to_csv(output_path, index=False)
        return df
    
    # Find the CSAT column
    csat_col = next((c for c in df.columns if "satisfaction" in c or "csat" in c or "rating" in c), None)
    
    # Build the aggregation dictionary dynamically based on what columns exist
    # Each key is the new column name, each value is (source_column, aggregation_function)
    agg_dict = {
        "ticket_volume":    ("resolution_hours", "count"),    # count of rows = ticket volume
        "mttr_hours":       ("resolution_hours", "mean"),     # MTTR = mean resolution time
        "sla_compliance":   ("sla_met",          "mean"),     # mean of True/False = compliance rate
    }
    
    if csat_col:
        agg_dict["avg_csat"] = (csat_col, "mean")
    
    # pandas .agg() with named aggregations — cleaner than .groupby().agg({})
    kpi_df = (
        df
        .groupby(group_col)
        .agg(**agg_dict)
        .reset_index()
        .rename(columns={group_col: "dimension"})
    )
    
    # Round numeric columns to 2 decimal places for readability
    numeric_cols = kpi_df.select_dtypes(include="number").columns
    kpi_df[numeric_cols] = kpi_df[numeric_cols].round(2)
    
    # Convert SLA compliance from 0-1 to 0-100 percentage
    kpi_df["sla_compliance"] = (kpi_df["sla_compliance"] * 100).round(1)
    
    # Add a timestamp so we know when this file was generated
    kpi_df["pipeline_run_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Save to CSV
    output_path.parent.mkdir(parents=True, exist_ok=True)
    kpi_df.to_csv(output_path, index=False)
    
    print(f"  → Exported {len(kpi_df)} rows × {len(kpi_df.columns)} columns")
    print(f"  → Output: {output_path}")
    print(f"\n  Preview:\n{kpi_df.to_string(index=False)}")
    
    return kpi_df


# ── Entry point ───────────────────────────────────────────────────────────────
# This block only runs when you execute the file directly:
#   python scripts/main.py
#
# It does NOT run when another file imports this module
# This is a Python best practice for keeping scripts reusable

if __name__ == "__main__":
    print("=" * 60)
    print("  KPI Operations Pipeline")
    print(f"  Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Check that the raw file exists before starting
    if not RAW_PATH.exists():
        print(f"\n ERROR: Raw data file not found at:\n  {RAW_PATH}")
        print("\n Download it from Kaggle:")
        print("  https://www.kaggle.com/datasets/suraj520/customer-support-ticket-dataset")
        print("  Place the CSV in: data/raw/customer_support_tickets.csv\n")
        raise FileNotFoundError(f"Missing: {RAW_PATH}")
    
    # Run the three pipeline steps
    raw_df       = load_data(RAW_PATH)
    clean_df     = clean_and_engineer(raw_df)
    kpi_df       = aggregate_and_export(clean_df, PROCESSED_PATH)
    
    print("\n" + "=" * 60)
    print("  Pipeline completed successfully!")
    print(f"  Output: {PROCESSED_PATH}")
    print("=" * 60 + "\n")
