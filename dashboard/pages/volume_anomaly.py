import streamlit as st
import plotly.express as px
from db import run_query

def render():
    st.title("🚨 Volume Anomalies")
    st.markdown("Days where trading volume was significantly above each stock's historical average.")

    df = run_query("""
        SELECT
            date,
            ticker,
            sector_name,
            actual_volume,
            avg_volume_20d,
            volume_ratio
        FROM vw_volume_anomaly
        ORDER BY date DESC
    """)

    if df.empty:
        st.warning("No volume anomalies found.")
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Anomaly Days", len(df))
    col2.metric("Stocks Affected", df['ticker'].nunique())
    col3.metric("Avg Spike Ratio", f"{df['volume_ratio'].mean():.2f}x")

    st.markdown("---")
    st.subheader("📊 Anomaly Count by Stock")

    count_df = df.groupby(['ticker', 'sector_name']).size().reset_index(name='anomaly_count')
    count_df = count_df.sort_values('anomaly_count', ascending=False)

    fig_bar = px.bar(count_df, x='ticker', y='anomaly_count', color='sector_name',
        labels={'ticker': 'Stock', 'anomaly_count': 'Anomaly Days', 'sector_name': 'Sector'},
        height=400)
    st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")
    st.subheader("📅 Anomaly Timeline")
    st.caption("Each dot is one anomaly day. Larger dots = higher volume spike ratio.")

    fig_scatter = px.scatter(df, x='date', y='ticker', size='volume_ratio',
        color='sector_name',
        hover_data={'actual_volume': True, 'avg_volume_20d': True, 'volume_ratio': ':.2f'},
        labels={'date': 'Date', 'ticker': 'Stock', 'sector_name': 'Sector', 'volume_ratio': 'Spike Ratio'},
        height=480)
    st.plotly_chart(fig_scatter, use_container_width=True)

    st.markdown("---")
    st.subheader("📋 Anomaly Detail Table")

    all_tickers = ['All'] + sorted(df['ticker'].unique().tolist())
    selected = st.selectbox("Filter by Stock", options=all_tickers)

    filtered = df if selected == 'All' else df[df['ticker'] == selected]
    filtered_display = filtered[['date', 'ticker', 'sector_name', 'actual_volume', 'avg_volume_20d', 'volume_ratio']].copy()
    filtered_display.columns = ['Date', 'Symbol', 'Sector', 'Volume', '20-Day Avg Volume', 'Spike Ratio']
    filtered_display['Spike Ratio'] = filtered_display['Spike Ratio'].round(2)
    st.dataframe(filtered_display, use_container_width=True)