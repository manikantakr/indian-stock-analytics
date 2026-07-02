import streamlit as st
import plotly.express as px
from db import run_query

def render():
    st.title("🏭 Sector Comparison")
    st.markdown("Compare sector-level performance and risk over time.")

    df = run_query("""
        SELECT f.date, f.close, sec.sector_name
        FROM fact_prices f
        JOIN dim_stock s ON f.stock_id = s.stock_id
        JOIN dim_sector sec ON s.sector_id = sec.sector_id
        ORDER BY sec.sector_name, f.date
    """)

    df = df.sort_values(['sector_name', 'date'])
    sector_avg = df.groupby(['sector_name', 'date'])['close'].mean().reset_index()
    sector_avg.columns = ['Sector', 'Date', 'Avg Close']

    first_prices = sector_avg.groupby('Sector')['Avg Close'].transform('first')
    sector_avg['Normalized'] = (sector_avg['Avg Close'] / first_prices) * 100

    st.subheader("📈 Normalized Sector Performance (Base = 100)")
    st.caption("All sectors start at 100 so growth rates are directly comparable regardless of price level.")

    fig_line = px.line(sector_avg, x='Date', y='Normalized', color='Sector',
        labels={'Normalized': 'Indexed Price (Base 100)', 'Date': 'Date'}, height=480)
    fig_line.update_layout(hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig_line, use_container_width=True)

    st.markdown("---")
    st.subheader("📊 Sector Volatility Comparison")
    st.caption("Average annualised volatility across all stocks in each sector.")

    vol_df = run_query("""
        SELECT
            sec.sector_name,
            ROUND(CAST(AVG(v.volatility_30d) * SQRT(252) AS numeric), 4) AS avg_annualised_volatility
        FROM vw_volatility v
        JOIN dim_stock s ON v.ticker = s.ticker
        JOIN dim_sector sec ON s.sector_id = sec.sector_id
        WHERE v.volatility_30d IS NOT NULL
        GROUP BY sec.sector_name
        ORDER BY avg_annualised_volatility DESC
    """)

    if not vol_df.empty:
        fig_vol = px.bar(vol_df, x='sector_name', y='avg_annualised_volatility',
            color='avg_annualised_volatility', color_continuous_scale='Reds',
            labels={'sector_name': 'Sector', 'avg_annualised_volatility': 'Annualised Volatility'},
            text=vol_df['avg_annualised_volatility'].astype(str))
        fig_vol.update_traces(textposition='outside')
        fig_vol.update_layout(coloraxis_showscale=False, height=400)
        st.plotly_chart(fig_vol, use_container_width=True)
    else:
        st.info("Volatility data not available.")