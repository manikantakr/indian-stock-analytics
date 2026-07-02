-- =============================================================
-- Phase 3: Analytical Views — Indian Stock Market Analytics
-- Database: stock_analytics
-- Run this file once to create all 5 views.
-- =============================================================


-- =============================================================
-- VIEW 1: Moving Averages (20-day and 50-day)
-- Shows the short-term and medium-term price trend for each stock.
-- The dashboard will use this to plot price vs MA lines.
-- =============================================================

CREATE OR REPLACE VIEW vw_moving_averages AS
SELECT
    f.date,
    s.ticker,
    s.company_name,
    sec.sector_name,
    f.close,

    -- 20-day moving average: average of last 20 closing prices for this stock
    ROUND(
        AVG(f.close) OVER (
            PARTITION BY f.stock_id          -- restart calculation for each stock
            ORDER BY f.date            -- go in chronological order
            ROWS BETWEEN 19 PRECEDING AND CURRENT ROW  -- window = today + last 19 days
        )::NUMERIC, 2
    ) AS ma_20,

    -- 50-day moving average: same idea but wider window = smoother trend line
    ROUND(
        AVG(f.close) OVER (
            PARTITION BY f.stock_id
            ORDER BY f.date
            ROWS BETWEEN 49 PRECEDING AND CURRENT ROW  -- window = today + last 49 days
        )::NUMERIC, 2
    ) AS ma_50

FROM fact_prices f
JOIN dim_stock s   ON f.stock_id  = s.stock_id
JOIN dim_sector sec ON s.sector_id = sec.sector_id;


-- =============================================================
-- VIEW 2: Daily Returns
-- Calculates the % change in close price from the previous trading day.
-- Formula: ((today - yesterday) / yesterday) * 100
-- =============================================================

CREATE OR REPLACE VIEW vw_daily_returns AS
SELECT
    f.date,
    s.ticker,
    s.company_name,
    sec.sector_name,
    f.close,

    -- LAG() looks at the previous row's close price for the same stock
    LAG(f.close) OVER (
        PARTITION BY f.stock_id
        ORDER BY f.date
    ) AS prev_close_price,

    -- Daily return in percentage; NULL on the very first row (no previous day)
    ROUND(
        (
            (f.close - LAG(f.close) OVER (
                PARTITION BY f.stock_id
                ORDER BY f.date
            ))
            /
            NULLIF(
                LAG(f.close) OVER (
                    PARTITION BY f.stock_id
                    ORDER BY f.date
                ),
                0  -- NULLIF prevents division-by-zero if prev price is 0
            )
        ) * 100
    , 4) AS daily_return_pct

FROM fact_prices f
JOIN dim_stock s    ON f.stock_id  = s.stock_id
JOIN dim_sector sec ON s.sector_id = sec.sector_id;


-- =============================================================
-- VIEW 3: Rolling Volatility (30-day)
-- Measures how much a stock's daily returns vary over the last 30 days.
-- High std dev = high risk. Built on top of the returns logic above.
-- =============================================================

CREATE OR REPLACE VIEW vw_volatility AS
SELECT
    f.date,
    s.ticker,
    s.company_name,
    sec.sector_name,

    -- Rolling 30-day standard deviation of daily returns
    ROUND(
        STDDEV(
            (f.close - LAG(f.close) OVER (
                PARTITION BY f.stock_id ORDER BY f.date
            ))
            /
            NULLIF(
                LAG(f.close) OVER (
                    PARTITION BY f.stock_id ORDER BY f.date
                ),
                0
            ) * 100
        ) OVER (
            PARTITION BY f.stock_id
            ORDER BY f.date
            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW  -- 30-day window
        )::NUMERIC, 4
    ) AS volatility_30d

FROM fact_prices f
JOIN dim_stock s    ON f.stock_id  = s.stock_id
JOIN dim_sector sec ON s.sector_id = sec.sector_id;


-- =============================================================
-- VIEW 4: Sector Performance
-- Averages daily returns across all stocks in each sector per day.
-- Lets you compare: "On this day, did IT outperform Banking?"
-- =============================================================

CREATE OR REPLACE VIEW vw_sector_performance AS
SELECT
    f.date,
    sec.sector_name,

    -- Count of stocks contributing to this sector's average that day
    COUNT(DISTINCT f.stock_id) AS stock_count,

    -- Average daily return across all stocks in the sector
    ROUND(
        AVG(
            (f.close - LAG(f.close) OVER (
                PARTITION BY f.stock_id ORDER BY f.date
            ))
            /
            NULLIF(
                LAG(f.close) OVER (
                    PARTITION BY f.stock_id ORDER BY f.date
                ),
                0
            ) * 100
        )::NUMERIC, 4
    ) AS avg_daily_return_pct,

    -- Average closing price across the sector (for context)
    ROUND(AVG(f.close)::NUMERIC, 2) AS avg_close

FROM fact_prices f
JOIN dim_stock s    ON f.stock_id  = s.stock_id
JOIN dim_sector sec ON s.sector_id = sec.sector_id
GROUP BY f.date, sec.sector_name
ORDER BY f.date, sec.sector_name;


-- =============================================================
-- VIEW 5: Volume Anomaly Detection
-- Flags days where a stock's volume is 2x its 20-day average volume.
-- These spikes often signal major news, institutional activity, or earnings.
-- =============================================================

CREATE OR REPLACE VIEW vw_volume_anomaly AS
SELECT
    f.date,
    s.ticker,
    s.company_name,
    sec.sector_name,
    f.volume AS actual_volume,

    -- 20-day rolling average volume for this stock
    ROUND(
        AVG(f.volume) OVER (
            PARTITION BY f.stock_id
            ORDER BY f.date
            ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
        )::NUMERIC, 0
    ) AS avg_volume_20d,

    -- Ratio: how many times larger is today's volume vs the 20-day average?
    ROUND(
        (f.volume::NUMERIC)
        /
        NULLIF(
            AVG(f.volume) OVER (
                PARTITION BY f.stock_id
                ORDER BY f.date
                ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
            ),
            0
        )
    , 2) AS volume_ratio,

    -- Flag: TRUE if volume is more than 2x the 20-day average
    CASE
        WHEN f.volume > 2 * AVG(f.volume) OVER (
            PARTITION BY f.stock_id
            ORDER BY f.date
            ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
        )
        THEN TRUE
        ELSE FALSE
    END AS is_volume_spike,

    f.close,
    f.high,
    f.low

FROM fact_prices f
JOIN dim_stock s    ON f.stock_id  = s.stock_id
JOIN dim_sector sec ON s.sector_id = sec.sector_id;


-- =============================================================
-- Quick sanity checks — run these after creating the views
-- to confirm everything is working correctly.
-- =============================================================

-- Check moving averages for one stock
-- SELECT * FROM vw_moving_averages WHERE ticker = 'INFY' ORDER BY date LIMIT 10;

-- Check daily returns
-- SELECT * FROM vw_daily_returns WHERE ticker = 'HDFCBANK' ORDER BY date LIMIT 10;

-- Check volatility
-- SELECT * FROM vw_volatility WHERE ticker = 'RELIANCE' ORDER BY date DESC LIMIT 10;

-- Check sector performance for the last 30 days
-- SELECT * FROM vw_sector_performance ORDER BY date DESC LIMIT 30;

-- Check volume spikes only
-- SELECT * FROM vw_volume_anomaly WHERE is_volume_spike = TRUE ORDER BY date DESC LIMIT 20;