import streamlit as st
import plotly.express as px
from db import run_query

def render():
    st.title("🏠 Market Overview")
    st.markdown("A snapshot of all tracked Nifty 50 stocks across sectors.")

    df = run_query("""
        SELECT
            f.date,
            f.close,
            f.volume,
            s.ticker,
            s.company,
            sec.sector_name
        FROM fact_prices f
        JOIN dim_stock s ON f.stock_id = s.stock_id
        JOIN dim_sector sec ON s.sector_id = sec.sector_id
        ORDER BY s.ticker, f.date
    """)

    df['date'] = df['date'].astype(str)

    col1, col2, col3 = st.columns(3)
    col1.metric("Stocks Tracked", df['ticker'].nunique())
    col2.metric("Sectors", df['sector_name'].nunique())
    col3.metric("Date Range", f"{df['date'].min()} → {df['date'].max()}")

    st.markdown("---")
    st.subheader("📊 Average Return by Sector")

    sector_df = df.sort_values('date').groupby(['sector_name', 'ticker']).agg(
        first_close=('close', 'first'),
        last_close=('close', 'last')
    ).reset_index()

    sector_df['total_return_pct'] = (
        (sector_df['last_close'] - sector_df['first_close']) / sector_df['first_close']
    ) * 100

    sector_avg = sector_df.groupby('sector_name')['total_return_pct'].mean().reset_index()
    sector_avg.columns = ['Sector', 'Avg Return (%)']
    sector_avg = sector_avg.sort_values('Avg Return (%)', ascending=False)

    fig = px.bar(
        sector_avg,
        x='Sector',
        y='Avg Return (%)',
        color='Avg Return (%)',
        color_continuous_scale='RdYlGn',
        text=sector_avg['Avg Return (%)'].round(1).astype(str) + '%'
    )
    fig.update_traces(textposition='outside')
    fig.update_layout(coloraxis_showscale=False, height=400)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("📋 Stock Summary")

    summary = sector_df[['ticker', 'sector_name', 'first_close', 'last_close', 'total_return_pct']].copy()
    summary.columns = ['Symbol', 'Sector', 'Start Price (₹)', 'Latest Price (₹)', 'Total Return (%)']
    summary['Start Price (₹)'] = summary['Start Price (₹)'].round(2)
    summary['Latest Price (₹)'] = summary['Latest Price (₹)'].round(2)
    summary['Total Return (%)'] = summary['Total Return (%)'].round(2)
    summary = summary.sort_values('Total Return (%)', ascending=False).reset_index(drop=True)

    st.dataframe(
        summary.style.background_gradient(subset=['Total Return (%)'], cmap='RdYlGn'),
        use_container_width=True
    )