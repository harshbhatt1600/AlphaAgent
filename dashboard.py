# dashboard.py
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
import sys
import os

# Make sure imports work from root
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.fetch_stock_data import fetch_stock_data
from tools.technical_indicators import calculate_indicators
from tools.anomaly_detection import detect_anomalies
from tools.news_sentiment import get_stock_news
from agent.brain import run_agent
from utils.db import get_recent_logs, test_connection

# --- Page Config ---
st.set_page_config(
    page_title="AlphaAgent",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Custom CSS (matching your mockup exactly) ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap');

* { font-family: 'JetBrains Mono', 'Courier New', monospace !important; }

.stApp { background-color: #0d1117; color: #e6edf3; }

section[data-testid="stSidebar"] { background-color: #0d1117; }

.topbar {
    display: flex; align-items: center; justify-content: space-between;
    padding: 12px 0; border-bottom: 0.5px solid #30363d; margin-bottom: 20px;
}
.logo { font-size: 18px; font-weight: 500; color: #58a6ff; letter-spacing: 3px; }
.logo span { color: #f0f6fc; }
.signal-buy { color: #3fb950; font-weight: 500; font-size: 13px; }
.signal-sell { color: #f85149; font-weight: 500; font-size: 13px; }
.signal-hold { color: #8b949e; font-weight: 500; font-size: 13px; }

div[data-testid="metric-container"] {
    background: #161b22 !important;
    border: 0.5px solid #30363d !important;
    border-radius: 8px !important;
    padding: 14px !important;
}
div[data-testid="metric-container"] label {
    font-size: 11px !important; color: #8b949e !important;
    text-transform: uppercase; letter-spacing: 1px;
}
div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
    font-size: 22px !important; color: #f0f6fc !important; font-weight: 500 !important;
}

.panel {
    background: #161b22; border: 0.5px solid #30363d;
    border-radius: 8px; padding: 16px; margin-bottom: 12px;
}
.panel-title {
    font-size: 11px; color: #8b949e; text-transform: uppercase;
    letter-spacing: 1px; margin-bottom: 12px;
}
.news-item {
    display: flex; justify-content: space-between; align-items: flex-start;
    gap: 8px; padding: 8px 0; border-bottom: 0.5px solid #21262d;
}
.news-text { font-size: 12px; color: #c9d1d9; line-height: 1.5; flex: 1; }
.badge { font-size: 10px; padding: 2px 8px; border-radius: 4px; white-space: nowrap; font-weight: 500; }
.badge-pos { background: #0d2818; color: #3fb950; border: 0.5px solid #238636; }
.badge-neg { background: #2d1117; color: #f85149; border: 0.5px solid #da3633; }
.badge-neu { background: #161b22; color: #8b949e; border: 0.5px solid #30363d; }

.ai-box {
    background: #0d1f38; border: 0.5px solid #1f6feb;
    border-radius: 8px; padding: 16px; margin-top: 12px;
}
.ai-title { font-size: 11px; color: #58a6ff; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; }
.ai-text { font-size: 13px; color: #c9d1d9; line-height: 1.8; }

.ind-row {
    display: flex; justify-content: space-between;
    padding: 5px 0; border-bottom: 0.5px solid #21262d;
}
.ind-label { font-size: 11px; color: #8b949e; }
.ind-val { font-size: 11px; color: #f0f6fc; font-weight: 500; }
.ind-up { color: #3fb950 !important; }
.ind-down { color: #f85149 !important; }

.log-row {
    padding: 8px 0; border-bottom: 0.5px solid #21262d;
    font-size: 11px; color: #8b949e;
}
.log-query { color: #c9d1d9; font-size: 12px; margin-bottom: 2px; }

div.stButton > button {
    background: #161b22; color: #58a6ff; border: 0.5px solid #30363d;
    border-radius: 6px; font-size: 13px; width: 100%;
    font-family: 'JetBrains Mono', monospace !important;
}
div.stButton > button:hover { border-color: #58a6ff; color: #f0f6fc; }

.stTextInput input, .stSelectbox select {
    background: #161b22 !important; color: #f0f6fc !important;
    border: 0.5px solid #30363d !important; border-radius: 6px !important;
    font-family: 'JetBrains Mono', monospace !important;
}
.stTextArea textarea {
    background: #161b22 !important; color: #f0f6fc !important;
    border: 0.5px solid #30363d !important; border-radius: 6px !important;
    font-family: 'JetBrains Mono', monospace !important;
}

hr { border-color: #30363d; }
</style>
""", unsafe_allow_html=True)


# --- Helper: Determine overall signal ---
def get_signal(indicators: dict) -> tuple:
    signals = []
    try:
        rsi = indicators.get("rsi", {}).get("value", 50)
        macd_sig = indicators.get("macd", {}).get("signal", "NEUTRAL")
        ma_sig = indicators.get("moving_averages", {}).get("signal", "NEUTRAL")

        if rsi < 30: signals.append("BULLISH")
        elif rsi > 70: signals.append("BEARISH")

        if "BULLISH" in str(macd_sig): signals.append("BULLISH")
        elif "BEARISH" in str(macd_sig): signals.append("BEARISH")

        if "BULLISH" in str(ma_sig): signals.append("BULLISH")
        elif "BEARISH" in str(ma_sig): signals.append("BEARISH")

        bull = signals.count("BULLISH")
        bear = signals.count("BEARISH")
        if bull > bear: return "▲ BUY SIGNAL", "signal-buy"
        elif bear > bull: return "▼ SELL SIGNAL", "signal-sell"
        else: return "◆ HOLD", "signal-hold"
    except:
        return "◆ HOLD", "signal-hold"


# --- Helper: Build Plotly price chart ---
def build_price_chart(stock_data: dict) -> go.Figure:
    history = stock_data.get("history", [])
    if not history:
        return go.Figure()

    dates = list(range(len(history)))
    closes = [h["Close"] for h in history]
    highs = [h["High"] for h in history]
    lows = [h["Low"] for h in history]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=dates, y=highs, name="BB Upper",
        line=dict(color="#30363d", width=1, dash="dot"),
        showlegend=True
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=lows, name="BB Lower",
        line=dict(color="#30363d", width=1, dash="dot"),
        fill="tonexty", fillcolor="rgba(48,54,61,0.15)",
        showlegend=True
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=closes, name="Price",
        line=dict(color="#58a6ff", width=2),
        showlegend=True
    ))

    fig.update_layout(
        paper_bgcolor="#161b22", plot_bgcolor="#161b22",
        margin=dict(l=10, r=10, t=10, b=10),
        height=200,
        legend=dict(
            orientation="h", y=1.1, x=0,
            font=dict(color="#8b949e", size=10),
            bgcolor="rgba(0,0,0,0)"
        ),
        xaxis=dict(showgrid=True, gridcolor="#21262d", color="#8b949e", tickfont=dict(size=10)),
        yaxis=dict(showgrid=True, gridcolor="#21262d", color="#8b949e", tickfont=dict(size=10)),
        font=dict(family="JetBrains Mono, Courier New", color="#8b949e")
    )
    return fig


# --- TOP BAR ---
st.markdown("""
<div class="topbar">
  <div class="logo">ALPHA<span>AGENT</span></div>
  <div style="font-size:11px;color:#8b949e;letter-spacing:1px;">AUTONOMOUS STOCK INTELLIGENCE</div>
</div>
""", unsafe_allow_html=True)


# --- TABS ---
tab1, tab2, tab3 = st.tabs(["📊  Analysis", "🤖  AI Agent", "🗃  Audit Logs"])


# ============================================================
# TAB 1 — ANALYSIS DASHBOARD
# ============================================================
with tab1:
    col_input, col_period = st.columns([3, 1])
    with col_input:
        ticker = st.text_input("", placeholder="Enter ticker — e.g. TCS.NS, RELIANCE.NS, AAPL", label_visibility="collapsed")
    with col_period:
        period = st.selectbox("", ["3mo", "1mo", "6mo", "1y"], label_visibility="collapsed")

    analyze = st.button("▶  RUN ANALYSIS")

    if analyze and ticker:
        with st.spinner("Fetching market data..."):
            stock = fetch_stock_data(ticker.strip(), period)
            indicators = calculate_indicators(ticker.strip(), period)
            anomalies = detect_anomalies(ticker.strip(), period)
            news = get_stock_news(ticker.strip(), ticker.strip().split(".")[0])

        if "error" in stock:
            st.error(f"Error: {stock['error']}")
        else:
            # --- Signal ---
            signal_text, signal_class = get_signal(indicators)
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
              <div style="font-size:13px;color:#8b949e;">
                <span style="color:#f0f6fc;font-weight:500;">{stock.get('company_name','')}</span>
                &nbsp;|&nbsp; {ticker.upper()} &nbsp;|&nbsp; {stock.get('currency','')}
              </div>
              <div class="{signal_class}">{signal_text}</div>
            </div>
            """, unsafe_allow_html=True)

            # --- Metric Cards ---
            m1, m2, m3, m4 = st.columns(4)
            price = stock.get("current_price", 0)
            change = stock.get("price_change_pct", 0)
            rsi_val = indicators.get("RSI", {}).get("value", "N/A")
            sentiment_score = 0
            anomaly_count = len(anomalies.get("anomalies", [])) if isinstance(anomalies, dict) else 0

            m1.metric("Current Price", f"₹{price:,.2f}" if stock.get("currency") == "INR" else f"${price:,.2f}", f"{change:+.2f}%")
            m2.metric("Articles Analyzed", str(news.get("articles_analyzed", 0)) if isinstance(news, dict) else "0")
            m3.metric("RSI (14)", f"{rsi_val:.1f}" if isinstance(rsi_val, float) else str(rsi_val))
            m4.metric("Anomalies", str(anomaly_count), "detected" if anomaly_count > 0 else "clean")

            st.markdown("<br>", unsafe_allow_html=True)

            # --- Chart + Indicators Row ---
            chart_col, ind_col = st.columns([2, 1])

            with chart_col:
                st.markdown('<div class="panel"><div class="panel-title">Price History + Bollinger Bands</div>', unsafe_allow_html=True)
                fig = build_price_chart(stock)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                st.markdown('</div>', unsafe_allow_html=True)

            with ind_col:
                st.markdown('<div class="panel"><div class="panel-title">Technical Indicators</div>', unsafe_allow_html=True)

                def ind_row(label, value, direction=None):
                    cls = "ind-up" if direction == "up" else "ind-down" if direction == "down" else ""
                    st.markdown(f'<div class="ind-row"><span class="ind-label">{label}</span><span class="ind-val {cls}">{value}</span></div>', unsafe_allow_html=True)

                try:
                    ma = indicators.get("moving_averages", {})
                    macd = indicators.get("MACD", {})
                    bb = indicators.get("bollinger_bands", {})

                    ind_row("MA 20", f"{ma.get('MA_20', 'N/A')}", "up" if ma.get("signal") == "BULLISH" else "down")
                    ind_row("MA 50", f"{ma.get('MA_50', 'N/A')}")
                    ind_row("MACD", f"{macd.get('macd', 'N/A')}", "up" if macd.get("signal") == "BULLISH" else "down")
                    ind_row("Signal Line", f"{macd.get('signal_line', 'N/A')}")
                    ind_row("BB Upper", f"{bb.get('upper', 'N/A')}")
                    ind_row("BB Lower", f"{bb.get('lower', 'N/A')}")
                    ind_row("RSI", f"{rsi_val}", "up" if isinstance(rsi_val, float) and rsi_val < 50 else "down")
                except:
                    st.markdown('<div style="color:#8b949e;font-size:12px;">Indicators unavailable</div>', unsafe_allow_html=True)

                st.markdown('</div>', unsafe_allow_html=True)

            # --- News Sentiment ---
            st.markdown('<div class="panel"><div class="panel-title">News Sentiment</div>', unsafe_allow_html=True)
            if isinstance(news, dict) and "latest_headlines" in news:
                for headline in news["latest_headlines"][:5]:
                    st.markdown(f"""
                    <div class="news-item">
                      <div class="news-text">{headline}</div>
                      <div class="badge badge-neu">NEWS</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown('<div style="color:#8b949e;font-size:12px;">No news data available</div>', unsafe_allow_html=True)

            # --- AI Recommendation Box ---
            rec_color = "#3fb950" if "BUY" in signal_text else "#f85149" if "SELL" in signal_text else "#8b949e"
            sentiment_text = news.get("sentiment_analysis", "No sentiment data.")[:300] + "..." if isinstance(news, dict) else "No sentiment data."
            st.markdown(f"""
            <div class="ai-box">
              <div class="ai-title">◆ AlphaAgent Recommendation</div>
              <div class="ai-text">
                Signal: <span style="color:{rec_color};font-weight:500;">{signal_text}</span> &nbsp;|&nbsp;
                RSI: <span style="color:#f0f6fc;">{rsi_val}</span> &nbsp;|&nbsp;
                Anomalies: <span style="color:#f0883e;">{anomaly_count} detected</span><br><br>
                {sentiment_text}
              </div>
            </div>
            """, unsafe_allow_html=True)

    elif analyze and not ticker:
        st.warning("Please enter a ticker symbol.")


# ============================================================
# TAB 2 — AI AGENT CHAT
# ============================================================
with tab2:
    st.markdown('<div class="panel-title" style="margin-bottom:16px;">Ask AlphaAgent anything about stocks</div>', unsafe_allow_html=True)

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "conv_history" not in st.session_state:
        st.session_state.conv_history = []

    user_query = st.text_area("", placeholder="e.g. Analyse TCS.NS and tell me if I should buy it today", height=80, label_visibility="collapsed")

    if st.button("▶  ASK ALPHAAGENT"):
        if user_query.strip():
            with st.spinner("AlphaAgent is reasoning..."):
                response = run_agent(user_query.strip(), st.session_state.conv_history)
            st.session_state.chat_history.append(("user", user_query.strip()))
            st.session_state.chat_history.append(("agent", response))
            st.session_state.conv_history.append({"role": "user", "content": user_query.strip()})
            st.session_state.conv_history.append({"role": "assistant", "content": response})
            if len(st.session_state.conv_history) > 20:
                st.session_state.conv_history = st.session_state.conv_history[-20:]

    for role, msg in reversed(st.session_state.chat_history):
        if role == "user":
            st.markdown(f'<div style="background:#161b22;border:0.5px solid #30363d;border-radius:8px;padding:12px;margin-bottom:8px;font-size:13px;color:#8b949e;">You: <span style="color:#f0f6fc;">{msg}</span></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="ai-box" style="margin-bottom:8px;"><div class="ai-title">◆ AlphaAgent</div><div class="ai-text">{msg}</div></div>', unsafe_allow_html=True)

    if st.session_state.chat_history:
        if st.button("Clear Chat"):
            st.session_state.chat_history = []
            st.session_state.conv_history = []
            st.rerun()


# ============================================================
# TAB 3 — AUDIT LOGS
# ============================================================
with tab3:
    st.markdown('<div class="panel-title" style="margin-bottom:16px;">Recent Agent Interactions — PostgreSQL</div>', unsafe_allow_html=True)

    logs = get_recent_logs(limit=20)

    if logs:
        for log in logs:
            ts = log.get("created_at", "")
            if hasattr(ts, "strftime"):
                ts = ts.strftime("%Y-%m-%d %H:%M:%S")
            st.markdown(f"""
            <div class="log-row">
              <div class="log-query">{log.get('user_query', '')}</div>
              <div>{ts} &nbsp;|&nbsp; Ticker: {log.get('ticker') or '—'}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown('<div style="color:#8b949e;font-size:12px;">No logs yet. Run the agent first.</div>', unsafe_allow_html=True)