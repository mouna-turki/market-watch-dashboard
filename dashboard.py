import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# --- Configuration & Constants ---
st.set_page_config(
    page_title="Global Market Watch",
    page_icon="📈",
    layout="wide"
)

st.markdown("""
        <style>
               .block-container { padding-top: 2rem; padding-bottom: 1rem; }
        </style>
        """, unsafe_allow_html=True)

# Extended Asset Dictionary
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
    "ETFs (Thematic)": {
        "Tech (XLK)": "XLK",
        "Energy (XLE)": "XLE",
        "Financials (XLF)": "XLF",
        "Clean Energy (ICLN)": "ICLN"
    },
    "Currencies (vs USD)": {
        "EUR/USD": "EURUSD=X",
        "USD/JPY": "JPY=X",
        "BTC/USD": "BTC-USD"
    },
    "Commodities": {
        "Gold": "GC=F",
        "Crude Oil": "CL=F",
        "Copper": "HG=F"
    },
    "Fixed Income (Yields)": {
        "US 10Y Treasury": "^TNX",
        "German Bund 10Y": "TMBMKDE-10Y"
    }
}

# --- Data Engine ---

@st.cache_data(ttl=300)
def get_market_data(tickers: List[str], period: str = "1y") -> pd.DataFrame:
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
    if df_ticker.empty or len(df_ticker) < 2:
        return {"price": 0.0, "delta": 0.0, "delta_pct": 0.0}

    series = df_ticker['Close'].dropna()
    if series.empty: return {"price": 0.0, "delta": 0.0, "delta_pct": 0.0}

    latest = series.iloc[-1]
    prev = series.iloc[-2]
    delta = latest - prev
    delta_pct = (delta / prev) * 100
    
    return {"price": latest, "delta": delta, "delta_pct": delta_pct}

# --- Advanced Visualization ---

def plot_price_history(df: pd.Series, title: str, color: str = "#2962FF"):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index, y=df.values, mode='lines',
        line=dict(color=color, width=2), name=title
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=12)),
        margin=dict(l=0, r=0, t=30, b=0), height=150,
        xaxis=dict(showgrid=False, showline=False, showticklabels=False), # Minimalist
        yaxis=dict(showgrid=False, showticklabels=False, autorange=True),
        showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        hovermode="x unified"
    )
    return fig

def plot_relative_performance(df_multi: pd.DataFrame, assets: List[str]):
    """Normalize multiple assets to start at 0% for comparison"""
    fig = go.Figure()
    
    for ticker, name in assets:
        if ticker in df_multi.columns:
            # Multi-level column handling
            series = df_multi[ticker]['Close'] if isinstance(df_multi.columns, pd.MultiIndex) else df_multi['Close']
            
            # New robust version
            first_valid_idx = series.first_valid_index() # Find the first actual data point
            if first_valid_idx is not None:
                start_price = series.loc[first_valid_idx]
                if start_price > 0:
                    normalized = ((series / start_price) - 1) * 100
                    fig.add_trace(go.Scatter(
                        x=normalized.index, 
                        y=normalized, 
                        mode='lines', 
                        name=name
                    ))

    fig.update_layout(
        title="Relative Performance Comparison (%)",
        yaxis_title="Return (%)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

# --- Main Logic ---

def main():
    st.title("🏦 Global Market Watch Pro")
    st.markdown(f"*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    
    # Sidebar
    st.sidebar.header("Settings")
    time_range = st.sidebar.select_slider("Period", options=["1mo", "3mo", "6mo", "1y", "2y"], value="1y")
    
    if st.sidebar.button("Refresh Data"): st.cache_data.clear()

    # 1. Fetch Data
    all_tickers = []
    ticker_map = {} # Map Symbol -> Readable Name
    for cat, items in ASSETS.items():
        for name, sym in items.items():
            all_tickers.append(sym)
            ticker_map[sym] = name
            
    with st.spinner('Fetching market data...'):
        raw_data = get_market_data(list(set(all_tickers)), period=time_range)

    if raw_data.empty:
        st.error("No data received.")
        st.stop()

    # 2. Main Dashboard Grid
    for category_name, assets in ASSETS.items():
        st.subheader(category_name)
        cols = st.columns(len(assets))
        for idx, (asset_label, ticker) in enumerate(assets.items()):
            with cols[idx]:
                try:
                    # Safe extraction
                    df_t = raw_data[ticker] if len(all_tickers) > 1 else raw_data
                    
                    metrics = calculate_metrics(df_t)
                    color = "#00C805" if metrics['delta'] >= 0 else "#FF5000"
                    
                    st.metric(
                        label=asset_label, 
                        value=f"{metrics['price']:,.2f}", 
                        delta=f"{metrics['delta']:,.2f} ({metrics['delta_pct']:.2f}%)"
                    )
                    st.plotly_chart(
                        plot_price_history(df_t['Close'], asset_label, color), 
                        use_container_width=True, config={'staticPlot': True}
                    )
                except Exception:
                    st.warning(f"N/A {asset_label}")
        st.divider()

    # 3. Portfolio & Analysis Section
    st.header("📊 Portfolio & Analysis")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Compare Assets")
        # Dropdown to select assets to compare
        compare_list = st.multiselect(
            "Select assets to compare returns:", 
            options=ticker_map.keys(),
            format_func=lambda x: ticker_map[x],
            default=[ASSETS["Equities - US"]["S&P 500"], ASSETS["Commodities"]["Gold"]]
        )
        
        if compare_list:
            # Prepare list of (Ticker, Name) tuples
            assets_to_plot = [(t, ticker_map[t]) for t in compare_list]
            st.plotly_chart(plot_relative_performance(raw_data, assets_to_plot), use_container_width=True)

    with col2:
        st.subheader("Cumulative Portfolio Return")
        st.caption("Hypothetical Equal-Weighted Portfolio (Excluding Yields/Forex)")
        
        # Calculate Equal Weighted Index
        valid_tickers = [
            t for t in all_tickers 
            if t not in ASSETS["Fixed Income (Yields)"].values() 
            and t not in ASSETS["Currencies (vs USD)"].values()
        ]
        
        portfolio_df = pd.DataFrame()
        
        for t in valid_tickers:
            try:
                # Normalize every asset to start at 100
                df_t = raw_data[t]['Close'] if len(all_tickers) > 1 else raw_data['Close']
                df_t = df_t.dropna()
                if not df_t.empty:
                    normalized = (df_t / df_t.iloc[0]) * 100
                    portfolio_df[t] = normalized
            except:
                pass
        
        if not portfolio_df.empty:
            # Average across columns to get portfolio index
            portfolio_index = portfolio_df.mean(axis=1)
            
            # Calculate return %
            total_return = portfolio_index.iloc[-1] - 100
            
            st.metric("Total Return (Equal Weight)", f"{total_return:.2f}%")
            
            fig_port = px.area(portfolio_index, title="Portfolio Value (Base 100)")
            fig_port.update_layout(showlegend=False, yaxis_title="Index Value")
            st.plotly_chart(fig_port, use_container_width=True)

if __name__ == "__main__":
    main()