import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# --- Configuration & Constants ---
st.set_page_config(
    page_title="Global Market Watch",
    page_icon="📈",
    layout="wide"
)

# Custom CSS to decrease whitespace at top
st.markdown("""
        <style>
               .block-container {
                    padding-top: 2rem;
                    padding-bottom: 1rem;
                }
        </style>
        """, unsafe_allow_html=True)

# Dictionary of assets to track
# Format: { 'Label': 'Ticker Symbol' }
ASSETS = {
    "Equities - US": {
        "S&P 500": "^GSPC",
        "Nasdaq 100": "^NDX",
        "Dow Jones": "^DJI"
    },
    "Equities - Europe": {
        "Euro Stoxx 50": "^STOXX50E",
        "DAX (Germany)": "^GDAXI",
        "CAC 40 (France)": "^FCHI"
    },
    "Equities - Asia": {
        "Nikkei 225 (Japan)": "^N225",
        "Hang Seng (HK)": "^HSI",
        "Nifty 50 (India)": "^NSEI"
    },
    "Currencies (vs USD)": {
        "EUR/USD": "EURUSD=X",
        "GBP/USD": "GBPUSD=X",
        "USD/JPY": "JPY=X",
        "BTC/USD": "BTC-USD"
    },
    "Commodities": {
        "Gold": "GC=F",
        "Crude Oil (WTI)": "CL=F",
        "Corn": "ZC=F",
        "Copper": "HG=F"
    },
    "Fixed Income (Yields)": {
        "US 10Y Treasury": "^TNX",
        "US 2Y Treasury": "^IRX",
        "German Bund 10Y": "TMBMKDE-10Y"
    }
}

# --- Data Fetching Engine ---

@st.cache_data(ttl=300)  # Cache data for 5 minutes
def get_market_data(tickers: List[str], period: str = "1y") -> pd.DataFrame:
    """Fetches historical market data in bulk."""
    if not tickers: return pd.DataFrame()
    try:
        data = yf.download(
            tickers, period=period, group_by='ticker', 
            auto_adjust=True, prepost=True, threads=True
        )
        return data
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

def calculate_metrics(df_ticker: pd.DataFrame) -> Dict:
    """Calculates latest price and daily change."""
    if df_ticker.empty or len(df_ticker) < 2:
        return {"price": 0.0, "delta": 0.0, "delta_pct": 0.0}

    series = df_ticker['Close'].dropna()
    if series.empty: return {"price": 0.0, "delta": 0.0, "delta_pct": 0.0}

    latest_price = series.iloc[-1]
    prev_price = series.iloc[-2]
    delta = latest_price - prev_price
    delta_pct = (delta / prev_price) * 100
    
    return {"price": latest_price, "delta": delta, "delta_pct": delta_pct}

# --- UPDATED Visualization Component ---

def plot_price_history(df: pd.Series, title: str, color: str = "#2962FF"):
    """
    Creates a minimalist LINE chart with dynamic scaling.
    """
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df.index, 
        y=df.values,
        mode='lines',
        # Removed fill='tozeroy' here to make it a pure line chart
        line=dict(color=color, width=2.5), 
        name=title
    ))
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=14)),
        margin=dict(l=0, r=0, t=30, b=10),
        height=200,
        # Add a subtle base line for the X axis
        xaxis=dict(showgrid=False, showline=True, linecolor='rgba(200,200,200,0.5)'),
        # Crucial change for scaling: autorange=True and zeroline=False
        yaxis=dict(
            showgrid=True, 
            gridcolor='rgba(200,200,200,0.1)',
            autorange=True,
            zeroline=False 
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False,
        hovermode="x unified" # Better hover interaction
    )
    
    return fig

# --- Main Dashboard Logic ---

def main():
    st.title("🏦 Global Market Watch")
    st.markdown(f"*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    st.markdown("---")

    # Sidebar controls
    st.sidebar.header("Settings")
    time_range = st.sidebar.select_slider(
        "Historical Period",
        options=["1mo", "3mo", "6mo", "1y", "2y", "5y"],
        value="1y"
    )
    
    if st.sidebar.button("Refresh Data"):
        st.cache_data.clear()

    # Flatten all tickers to fetch in one batch
    all_tickers = []
    for category in ASSETS.values():
        all_tickers.extend(category.values())
    all_tickers = list(set(all_tickers))
    
    with st.spinner('Fetching market data...'):
        market_data = get_market_data(all_tickers, period=time_range)

    # Render Sections
    if market_data.empty:
         st.error("Failed to fetch market data. Please try refreshing.")
         st.stop()

    for category_name, assets in ASSETS.items():
        st.subheader(category_name)
        cols = st.columns(len(assets))
        
        for idx, (asset_label, ticker) in enumerate(assets.items()):
            with cols[idx]:
                try:
                    if len(all_tickers) > 1: ticker_df = market_data[ticker]
                    else: ticker_df = market_data
                    
                    metrics = calculate_metrics(ticker_df)
                    is_positive = metrics['delta'] >= 0
                    color_hex = "#00C805" if is_positive else "#FF5000"
                    
                    st.metric(
                        label=asset_label,
                        value=f"{metrics['price']:,.2f}",
                        delta=f"{metrics['delta']:,.2f} ({metrics['delta_pct']:.2f}%)"
                    )
                    
                    if not ticker_df['Close'].empty:
                        st.plotly_chart(
                            plot_price_history(ticker_df['Close'], asset_label, color_hex),
                            use_container_width=True,
                            config={'displayModeBar': False, 'staticPlot': False}
                        )
                except KeyError:
                    st.warning(f"Data N/A for {asset_label}")
        st.markdown("---")
        
    st.caption("Data source: Yahoo Finance. For demonstration purposes only.")

if __name__ == "__main__":
    main()