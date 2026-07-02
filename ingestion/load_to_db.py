"""
Phase 2: Load CSV into PostgreSQL
===================================
Reads the raw_prices.csv from Phase 1 and loads it into
the stock_analytics PostgreSQL database.

Run this after ingest.py has created the CSV.

Usage:
    python ingestion/load_to_db.py
"""

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
import os

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}

# Path to the CSV from Phase 1
RAW_PATH = os.path.join(os.path.dirname(__file__), "../data/raw/raw_prices.csv")

# Stock ticker → company name mapping
COMPANY_NAMES = {
    "RELIANCE.NS":   "Reliance Industries",
    "TCS.NS":        "Tata Consultancy Services",
    "INFY.NS":       "Infosys",
    "WIPRO.NS":      "Wipro",
    "HCLTECH.NS":    "HCL Technologies",
    "HDFCBANK.NS":   "HDFC Bank",
    "ICICIBANK.NS":  "ICICI Bank",
    "KOTAKBANK.NS":  "Kotak Mahindra Bank",
    "SBIN.NS":       "State Bank of India",
    "AXISBANK.NS":   "Axis Bank",
    "HINDUNILVR.NS": "Hindustan Unilever",
    "ITC.NS":        "ITC Limited",
    "NESTLEIND.NS":  "Nestle India",
    "SUNPHARMA.NS":  "Sun Pharmaceutical",
    "DRREDDY.NS":    "Dr. Reddys Laboratories",
}


def seed_dimensions(conn, df: pd.DataFrame):
    """Insert unique sectors and stocks into dimension tables."""
    cur = conn.cursor()

    # ── Seed dim_sector ──────────────────────────────────────
    sectors = df["sector"].unique().tolist()
    for sector in sectors:
        cur.execute("""
            INSERT INTO dim_sector (sector_name)
            VALUES (%s)
            ON CONFLICT (sector_name) DO NOTHING
        """, (sector,))

    # ── Seed dim_stock ───────────────────────────────────────
    for _, row in df[["ticker", "sector"]].drop_duplicates().iterrows():
        cur.execute("""
            INSERT INTO dim_stock (ticker, company, sector_id)
            VALUES (
                %s, %s,
                (SELECT sector_id FROM dim_sector WHERE sector_name = %s)
            )
            ON CONFLICT (ticker) DO NOTHING
        """, (row["ticker"], COMPANY_NAMES.get(row["ticker"], row["ticker"]), row["sector"]))

    conn.commit()
    cur.close()
    print(f"  ✅ Seeded {len(sectors)} sectors and {df['ticker'].nunique()} stocks")


def load_prices(conn, df: pd.DataFrame):
    """Insert all price rows into fact_prices."""
    cur = conn.cursor()

    # Get stock_id lookup from DB
    cur.execute("SELECT ticker, stock_id FROM dim_stock")
    stock_map = {row[0]: row[1] for row in cur.fetchall()}

    rows = []
    skipped = 0

    for _, row in df.iterrows():
        sid = stock_map.get(row["ticker"])
        if not sid:
            skipped += 1
            continue
        rows.append((
            sid,
            str(row["date"]),
            round(float(row["open"]),  2),
            round(float(row["high"]),  2),
            round(float(row["low"]),   2),
            round(float(row["close"]), 2),
            int(row["volume"]),
        ))

    sql = """
        INSERT INTO fact_prices (stock_id, date, open, high, low, close, volume)
        VALUES %s
        ON CONFLICT (stock_id, date) DO NOTHING
    """
    execute_values(cur, sql, rows, page_size=500)
    conn.commit()
    cur.close()

    print(f"  ✅ Inserted {len(rows):,} price rows  |  Skipped {skipped} unknowns")


def verify(conn):
    """Quick sanity check — print row counts from each table."""
    cur = conn.cursor()
    for table in ["dim_sector", "dim_stock", "fact_prices"]:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f"  {table:<20} → {count:,} rows")
    cur.close()


def run_load():
    print()
    print("=" * 52)
    print("  Stock Market Analytics — Phase 2: Load to DB")
    print("=" * 52)
    print(f"  Reading : {RAW_PATH}")
    print()

    # Read CSV
    df = pd.read_csv(RAW_PATH)
    print(f"  CSV rows : {len(df):,}")
    print()

    # Connect to PostgreSQL
    print("  Connecting to PostgreSQL...")
    conn = psycopg2.connect(**DB_CONFIG)
    print("  Connected ✅")
    print()

    # Load data
    print("  Seeding dimension tables...")
    seed_dimensions(conn, df)

    print("  Loading price data...")
    load_prices(conn, df)

    print()
    print("  Verifying row counts:")
    verify(conn)

    conn.close()

    print()
    print("=" * 52)
    print("  ✅ Phase 2 Complete — Database is ready!")
    print("=" * 52)
    print()
    print("  Next step → run:  python sql/create_views.py")
    print()


if __name__ == "__main__":
    run_load()