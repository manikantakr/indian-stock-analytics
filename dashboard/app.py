import streamlit as st

st.set_page_config(
    page_title="Indian Stock Market Analytics",
    page_icon="📈",
    layout="wide"
)

st.sidebar.title("📊 Stock Analytics")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigate",
    options=[
        "🏠 Overview",
        "🔍 Stock Deep-Dive",
        "🏭 Sector Comparison",
        "🚨 Volume Anomalies"
    ]
)

st.sidebar.markdown("---")
st.sidebar.caption("Data: NSE via yfinance | DB: PostgreSQL")

if page == "🏠 Overview":
    from pages import overview
    overview.render()

elif page == "🔍 Stock Deep-Dive":
    from pages import stock_detail
    stock_detail.render()

elif page == "🏭 Sector Comparison":
    from pages import sector_compare
    sector_compare.render()

elif page == "🚨 Volume Anomalies":
    from pages import volume_anomaly
    volume_anomaly.render()
