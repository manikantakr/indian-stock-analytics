"""
Phase 1: Data Ingestion
========================
Downloads 2 years of daily stock price data for 15 Nifty 50 stocks
using yfinance and saves it as a CSV file.

Run this once to get historical data.
After that, run it daily to keep the data fresh.

Usage:
    python ingest.py
"""

import yfinance as yf
import pandas as pd
import os
from datetime import datetime, timedelta


# ── CONFIGURATION ───────────────────────────────────────────
# 15 Nifty 50 stocks across 5 sectors
STOCKS = {
    "RELIANCE.NS":   "Energy",
    "TCS.NS":        "IT",
    "INFY.NS":       "IT",
    "WIPRO.NS":      "IT",
    "HCLTECH.NS":    "IT",
    "HDFCBANK.NS":   "Banking",
    "ICICIBANK.NS":  "Banking",
    "KOTAKBANK.NS":  "Banking",
    "SBIN.NS":       "Banking",
    "AXISBANK.NS":   "Banking",
    "HINDUNILVR.NS": "FMCG",
    "ITC.NS":        "FMCG",
    "NESTLEIND.NS":  "FMCG",
    "SUNPHARMA.NS":  "Pharma",
    "DRREDDY.NS":    "Pharma",
}

# Date range: last 2 years up to today
END_DATE   = datetime.today().strftime("%Y-%m-%d")
START_DATE = (datetime.today() - timedelta(days=730)).strftime("%Y-%m-%d")

# Where to save the CSV
RAW_DIR  = os.path.join(os.path.dirname(__file__), "../data/raw")
OUT_FILE = os.path.join(RAW_DIR, "raw_prices.csv")


# ── FETCH ONE STOCK ─────────────────────────────────────────
def fetch_stock(ticker: str, sector: str) -> pd.DataFrame:
    """
    Downloads OHLCV data for one ticker from Yahoo Finance.
    OHLCV = Open, High, Low, Close price + Volume (daily).
    Returns a clean DataFrame with consistent column names.
    """
    print(f"  Downloading {ticker} ...")

    df = yf.download(
        ticker,
        start=START_DATE,
        end=END_DATE,
        progress=False,   # suppress yfinance progress bar
        auto_adjust=True, # adjusts for stock splits/dividends automatically
    )

    if df.empty:
        print(f"  [WARNING] No data returned for {ticker} — skipping.")
        return pd.DataFrame()

    # yfinance returns multi-level columns sometimes — flatten them
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]

    # Reset index so 'Date' becomes a regular column
    df.reset_index(inplace=True)

    # Rename to clean lowercase names
    df.rename(columns={
        "Date":   "date",
        "Open":   "open",
        "High":   "high",
        "Low":    "low",
        "Close":  "close",
        "Volume": "volume",
    }, inplace=True)

    # Tag each row with the stock info
    df["ticker"] = ticker
    df["sector"] = sector

    # Drop any extra columns yfinance may return
    keep = ["date", "ticker", "sector", "open", "high", "low", "close", "volume"]
    df = df[[c for c in keep if c in df.columns]]

    return df


# ── MAIN INGESTION FUNCTION ─────────────────────────────────
def run_ingestion():
    print()
    print("=" * 52)
    print("  Stock Market Analytics — Phase 1: Ingestion")
    print("=" * 52)
    print(f"  Period : {START_DATE}  →  {END_DATE}")
    print(f"  Stocks : {len(STOCKS)} across {len(set(STOCKS.values()))} sectors")
    print()

    os.makedirs(RAW_DIR, exist_ok=True)

    all_frames = []
    failed     = []

    for ticker, sector in STOCKS.items():
        try:
            df = fetch_stock(ticker, sector)
            if not df.empty:
                all_frames.append(df)
        except Exception as e:
            print(f"  [ERROR] {ticker} failed: {e}")
            failed.append(ticker)

    if not all_frames:
        print("\n[ERROR] No data was downloaded. Check your internet connection.")
        return

    # Combine all stocks into one DataFrame
    combined = pd.concat(all_frames, ignore_index=True)

    # Ensure date column is clean
    combined["date"] = pd.to_datetime(combined["date"]).dt.date

    # Round prices to 2 decimal places
    for col in ["open", "high", "low", "close"]:
        combined[col] = combined[col].round(2)

    # Save to CSV
    combined.to_csv(OUT_FILE, index=False)

    # ── Summary ──────────────────────────────────────────────
    print()
    print("=" * 52)
    print("  ✅ Ingestion Complete")
    print("=" * 52)
    print(f"  Total rows   : {len(combined):,}")
    print(f"  Stocks saved : {combined['ticker'].nunique()}")
    print(f"  Date range   : {combined['date'].min()}  →  {combined['date'].max()}")
    print(f"  Saved to     : {OUT_FILE}")

    if failed:
        print(f"\n  ⚠  Failed tickers: {', '.join(failed)}")

    print()
    print("  Next step → run:  python ingestion/load_to_db.py")
    print()

    return combined


# ── ENTRY POINT ─────────────────────────────────────────────
if __name__ == "__main__":
    run_ingestion()
