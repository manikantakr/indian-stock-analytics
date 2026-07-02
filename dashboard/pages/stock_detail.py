import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from db import run_query

def render():
    st.title("🔍 Stock Deep-Dive")
    st.markdown("Detailed technical analysis for any tracked stock.")

    stocks_df = run_query("SELECT ticker, company FROM dim_stock ORDER BY ticker")
    stock_options = {
        row['ticker']: f"{row['ticker']} — {row['company']}"
        for _, row in stocks_df.iterrows()
    }

    selected_ticker = st.selectbox(
        "Select a Stock",
        options=list(stock_options.keys()),
        format_func=lambda x: stock_options[x]
    )

    st.markdown("---")
    st.subheader("📈 Price & Moving Averages")

    ma_df = run_query("""
        SELECT date, close, ma_20, ma_50
        FROM vw_moving_averages
        WHERE ticker = %s
        ORDER BY date
    """, params=(selected_ticker,))

    fig_ma = go.Figure()
    fig_ma.add_trace(go.Scatter(x=ma_df['date'], y=ma_df['close'], name='Close Price',
        line=dict(color='#636EFA', width=1.5)))
    fig_ma.add_trace(go.Scatter(x=ma_df['date'], y=ma_df['ma_20'], name='20-Day MA',
        line=dict(color='#FFA15A', width=1.5, dash='dot')))
    fig_ma.add_trace(go.Scatter(x=ma_df['date'], y=ma_df['ma_50'], name='50-Day MA',
        line=dict(color='#EF553B', width=1.5, dash='dash')))

    fig_ma.update_layout(height=450, xaxis_title="Date", yaxis_title="Price (₹)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified")
    st.plotly_chart(fig_ma, use_container_width=True)

    st.markdown("---")

    returns_df = run_query("""
        SELECT date, daily_return_pct
        FROM vw_daily_returns
        WHERE ticker = %s
        ORDER BY date
    """, params=(selected_ticker,))

    vol_df = run_query("""
        SELECT date, volatility_30d
        FROM vw_volatility
        WHERE ticker = %s
        ORDER BY date
    """, params=(selected_ticker,))

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Daily Returns Distribution")
        fig_hist = px.histogram(returns_df, x='daily_return_pct', nbins=60,
            color_discrete_sequence=['#636EFA'],
            labels={'daily_return_pct': 'Daily Return (%)'})
        fig_hist.update_layout(height=380, showlegend=False)
        st.plotly_chart(fig_hist, use_container_width=True)

    with col2:
        st.subheader("📉 Rolling 30-Day Volatility")
        if not vol_df.empty:
            fig_vol = px.line(vol_df, x='date', y='volatility_30d',
                color_discrete_sequence=['#EF553B'],
                labels={'volatility_30d': 'Volatility', 'date': 'Date'})
            fig_vol.update_layout(height=380)
            st.plotly_chart(fig_vol, use_container_width=True)
        else:
            st.info("Volatility data not available.")