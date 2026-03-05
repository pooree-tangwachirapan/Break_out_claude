"""
Multi-Strategy Trading Dashboard — Streamlit App
==================================================
6 Strategies:
  1. Gap Fill Strategy
  2. Opening Range Breakout (ORB)
  3. Oops Strategy
  4. PBD (Price Breakout/Breakdown from Consolidation)
  5. Rule of 4 (Post-Event)
  6. Volume Profile Breakout Zones (VAH→LVN / VAL→LVN)

Data: FMP API (intraday + daily)
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime, timedelta, time as dtime

# ══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(page_title="Multi-Strategy Dashboard", page_icon="📊",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
.stTabs [data-baseweb="tab-list"] { gap: 4px; }
.stTabs [data-baseweb="tab"] {
    background: #0d1117; border: 1px solid #1e293b; border-radius: 8px;
    padding: 8px 16px; font-size: 0.85rem;
}
.stTabs [aria-selected="true"] {
    background: #1e293b; border-color: #3b82f6;
}
.metric-card {
    background: linear-gradient(135deg,#1a1a2e,#16213e);
    border-radius: 12px; padding: 0.9rem; text-align: center;
    border: 1px solid #0f3460;
}
.metric-label { color: #8899aa; font-size: 0.7rem; text-transform: uppercase; }
.metric-value { color: #e0e0e0; font-size: 1.2rem; font-weight: 700; }
.signal-buy { color: #10b981; }
.signal-sell { color: #ef4444; }
.signal-pending { color: #f59e0b; }
.signal-rejected { color: #6b7280; }
.zone-box { border-radius: 8px; padding: 0.6rem 1rem; margin-bottom: 0.5rem; font-size: 0.82rem; }
.zone-upper { background: rgba(239,83,80,0.08); border-left: 4px solid #ef5350; }
.zone-lower { background: rgba(38,166,154,0.08); border-left: 4px solid #26a69a; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# FMP API
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=300)
def fetch_intraday(symbol, api_key, interval="5min", days_back=15):
    url = f"https://financialmodelingprep.com/api/v3/historical-chart/{interval}/{symbol}"
    try:
        r = requests.get(url, params={"apikey": api_key}, timeout=15)
        r.raise_for_status()
        data = r.json()
        if not data or isinstance(data, dict):
            return pd.DataFrame()
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        cutoff = datetime.now() - timedelta(days=days_back)
        return df[df["date"] >= cutoff].reset_index(drop=True)
    except Exception as e:
        st.error(f"API error: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def fetch_daily(symbol, api_key, days=60):
    url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}"
    try:
        r = requests.get(url, params={"apikey": api_key, "timeseries": days}, timeout=15)
        r.raise_for_status()
        data = r.json()
        if "historical" not in data:
            return pd.DataFrame()
        df = pd.DataFrame(data["historical"])
        df["date"] = pd.to_datetime(df["date"])
        return df.sort_values("date").reset_index(drop=True)
    except Exception as e:
        st.error(f"API error: {e}")
        return pd.DataFrame()


# ══════════════════════════════════════════════════════════════════════════════
# STRATEGY 1: GAP FILL
# ══════════════════════════════════════════════════════════════════════════════
def detect_gap_fill(daily_df, min_gap_pts=10):
    """Detect gap fill opportunities from daily data."""
    if len(daily_df) < 2:
        return pd.DataFrame()

    signals = []
    for i in range(1, len(daily_df)):
        prev = daily_df.iloc[i - 1]
        curr = daily_df.iloc[i]
        prev_close = prev["close"]
        curr_open = curr["open"]
        gap = curr_open - prev_close

        if abs(gap) < min_gap_pts:
            continue

        # Check if gap was filled (price reached prev_close during the day)
        if gap < 0:  # Gap Down
            filled = curr["high"] >= prev_close
            signals.append({
                "date": curr["date"],
                "type": "GAP DOWN → BUY",
                "gap_size": round(abs(gap), 2),
                "prev_close": round(prev_close, 2),
                "open": round(curr_open, 2),
                "filled": filled,
                "status": "FILLED ✅" if filled else "NOT FILLED ❌",
                "direction": "buy",
                "close": round(curr["close"], 2),
            })
        else:  # Gap Up
            filled = curr["low"] <= prev_close
            signals.append({
                "date": curr["date"],
                "type": "GAP UP → SELL",
                "gap_size": round(abs(gap), 2),
                "prev_close": round(prev_close, 2),
                "open": round(curr_open, 2),
                "filled": filled,
                "status": "FILLED ✅" if filled else "NOT FILLED ❌",
                "direction": "sell",
                "close": round(curr["close"], 2),
            })

    return pd.DataFrame(signals)


# ══════════════════════════════════════════════════════════════════════════════
# STRATEGY 2: OPENING RANGE BREAKOUT
# ══════════════════════════════════════════════════════════════════════════════
def detect_orb(intraday_df, or_minutes=15):
    """Detect Opening Range Breakout signals."""
    if intraday_df.empty:
        return pd.DataFrame(), {}

    df = intraday_df.copy()
    df["trade_date"] = df["date"].dt.date
    signals = []
    or_levels = {}

    for trade_date, day_df in df.groupby("trade_date"):
        day_df = day_df.sort_values("date")
        if len(day_df) < 3:
            continue

        market_open = day_df["date"].iloc[0]
        or_end = market_open + timedelta(minutes=or_minutes)

        or_bars = day_df[day_df["date"] <= or_end]
        after_or = day_df[day_df["date"] > or_end]

        if or_bars.empty or after_or.empty:
            continue

        or_high = or_bars["high"].max()
        or_low = or_bars["low"].min()
        or_levels[trade_date] = {"high": or_high, "low": or_low}

        breakout_detected = False
        for _, bar in after_or.iterrows():
            if not breakout_detected:
                if bar["close"] > or_high:
                    signals.append({
                        "date": bar["date"], "trade_date": trade_date,
                        "type": "ORB BREAKOUT ↑",
                        "price": round(bar["close"], 2),
                        "or_high": round(or_high, 2),
                        "or_low": round(or_low, 2),
                        "direction": "buy",
                        "status": "SIGNAL",
                    })
                    breakout_detected = True
                elif bar["close"] < or_low:
                    signals.append({
                        "date": bar["date"], "trade_date": trade_date,
                        "type": "ORB BREAKOUT ↓",
                        "price": round(bar["close"], 2),
                        "or_high": round(or_high, 2),
                        "or_low": round(or_low, 2),
                        "direction": "sell",
                        "status": "SIGNAL",
                    })
                    breakout_detected = True

    return pd.DataFrame(signals), or_levels


# ══════════════════════════════════════════════════════════════════════════════
# STRATEGY 3: OOPS STRATEGY
# ══════════════════════════════════════════════════════════════════════════════
def detect_oops(daily_df, min_gap_pts=15):
    """Detect Oops reversal signals."""
    if len(daily_df) < 2:
        return pd.DataFrame()

    signals = []
    for i in range(1, len(daily_df)):
        prev = daily_df.iloc[i - 1]
        curr = daily_df.iloc[i]

        prev_was_green = prev["close"] > prev["open"]
        prev_was_red = prev["close"] < prev["open"]
        gap = curr["open"] - prev["close"]

        # Oops Sell: prev green + gap up ≥15
        if prev_was_green and gap >= min_gap_pts:
            # Check if price came back to prev high (sell trigger)
            reached_prev_high = curr["low"] <= prev["high"]
            signals.append({
                "date": curr["date"],
                "type": "OOPS SELL",
                "gap_size": round(gap, 2),
                "prev_high": round(prev["high"], 2),
                "prev_low": round(prev["low"], 2),
                "prev_close": round(prev["close"], 2),
                "open": round(curr["open"], 2),
                "triggered": reached_prev_high,
                "status": "TRIGGERED ✅" if reached_prev_high else "NO TRIGGER ❌",
                "direction": "sell",
            })

        # Oops Buy: prev red + gap down ≥15
        if prev_was_red and gap <= -min_gap_pts:
            reached_prev_low = curr["high"] >= prev["low"]
            signals.append({
                "date": curr["date"],
                "type": "OOPS BUY",
                "gap_size": round(abs(gap), 2),
                "prev_high": round(prev["high"], 2),
                "prev_low": round(prev["low"], 2),
                "prev_close": round(prev["close"], 2),
                "open": round(curr["open"], 2),
                "triggered": reached_prev_low,
                "status": "TRIGGERED ✅" if reached_prev_low else "NO TRIGGER ❌",
                "direction": "buy",
            })

    return pd.DataFrame(signals)


# ══════════════════════════════════════════════════════════════════════════════
# STRATEGY 4: PBD (Price Breakout/Breakdown from Consolidation)
# ══════════════════════════════════════════════════════════════════════════════
def detect_pbd(intraday_df, lookback=20, consolidation_bars=6,
               range_pct_threshold=0.5):
    """
    Detect PBD: consolidation range then breakout.
    Consolidation = when the range of N bars is < threshold % of avg bar range.
    """
    if len(intraday_df) < lookback + consolidation_bars:
        return pd.DataFrame(), []

    df = intraday_df.copy()
    df["bar_range"] = df["high"] - df["low"]
    avg_range = df["bar_range"].rolling(lookback).mean()

    signals = []
    consolidation_zones = []

    i = consolidation_bars
    while i < len(df):
        window = df.iloc[i - consolidation_bars:i]
        window_high = window["high"].max()
        window_low = window["low"].min()
        window_range = window_high - window_low

        avg_r = avg_range.iloc[i] if pd.notna(avg_range.iloc[i]) else df["bar_range"].mean()

        # Is this a tight consolidation?
        is_consol = window_range < avg_r * consolidation_bars * range_pct_threshold

        if is_consol:
            consolidation_zones.append({
                "start_date": window["date"].iloc[0],
                "end_date": window["date"].iloc[-1],
                "high": window_high,
                "low": window_low,
            })

            # Look for breakout in next bars
            for j in range(i, min(i + 10, len(df))):
                bar = df.iloc[j]
                if bar["close"] > window_high:
                    signals.append({
                        "date": bar["date"],
                        "type": "PBD BREAKOUT ↑",
                        "price": round(bar["close"], 2),
                        "range_high": round(window_high, 2),
                        "range_low": round(window_low, 2),
                        "direction": "buy",
                        "status": "BREAKOUT",
                    })
                    i = j + 1
                    break
                elif bar["close"] < window_low:
                    signals.append({
                        "date": bar["date"],
                        "type": "PBD BREAKDOWN ↓",
                        "price": round(bar["close"], 2),
                        "range_high": round(window_high, 2),
                        "range_low": round(window_low, 2),
                        "direction": "sell",
                        "status": "BREAKDOWN",
                    })
                    i = j + 1
                    break
            else:
                i += 1
        else:
            i += 1

    return pd.DataFrame(signals), consolidation_zones


# ══════════════════════════════════════════════════════════════════════════════
# STRATEGY 5: RULE OF 4
# ══════════════════════════════════════════════════════════════════════════════
def detect_rule_of_4(intraday_df, event_dates=None, n_bars=4):
    """
    After event (NFP/FOMC), take first N bars, then trade breakout of that range.
    If event_dates not provided, use each day's first N bars as a proxy.
    """
    if intraday_df.empty:
        return pd.DataFrame(), []

    df = intraday_df.copy()
    df["trade_date"] = df["date"].dt.date
    signals = []
    r4_zones = []

    target_dates = event_dates if event_dates else df["trade_date"].unique()

    for td in target_dates:
        day_df = df[df["trade_date"] == td].sort_values("date")
        if len(day_df) < n_bars + 2:
            continue

        first_n = day_df.iloc[:n_bars]
        after_n = day_df.iloc[n_bars:]

        r4_high = first_n["high"].max()
        r4_low = first_n["low"].min()

        r4_zones.append({
            "date": td,
            "start": first_n["date"].iloc[0],
            "end": first_n["date"].iloc[-1],
            "high": r4_high,
            "low": r4_low,
        })

        breakout_found = False
        for _, bar in after_n.iterrows():
            if not breakout_found:
                if bar["close"] > r4_high:
                    signals.append({
                        "date": bar["date"], "trade_date": td,
                        "type": "RULE OF 4 → BUY ↑",
                        "price": round(bar["close"], 2),
                        "r4_high": round(r4_high, 2),
                        "r4_low": round(r4_low, 2),
                        "direction": "buy",
                    })
                    breakout_found = True
                elif bar["close"] < r4_low:
                    signals.append({
                        "date": bar["date"], "trade_date": td,
                        "type": "RULE OF 4 → SELL ↓",
                        "price": round(bar["close"], 2),
                        "r4_high": round(r4_high, 2),
                        "r4_low": round(r4_low, 2),
                        "direction": "sell",
                    })
                    breakout_found = True

    return pd.DataFrame(signals), r4_zones


# ══════════════════════════════════════════════════════════════════════════════
# STRATEGY 6: VOLUME PROFILE BREAKOUT ZONES
# ══════════════════════════════════════════════════════════════════════════════
def calculate_volume_profile(df, num_bins=50, va_pct=0.70, lvn_sensitivity=0.40):
    if df.empty or len(df) < 2:
        return None
    pmin, pmax = df["low"].min(), df["high"].max()
    if pmin == pmax:
        return None

    edges = np.linspace(pmin, pmax, num_bins + 1)
    centers = (edges[:-1] + edges[1:]) / 2
    bw = edges[1] - edges[0]
    vap = np.zeros(num_bins)

    for _, row in df.iterrows():
        tp = (row["high"] + row["low"] + row["close"]) / 3
        mask = (centers >= row["low"]) & (centers <= row["high"])
        n = mask.sum()
        if n > 0:
            d = np.abs(centers[mask] - tp)
            md = max(d.max(), 1e-9)
            w = 1 - (d / md) * 0.5
            w /= w.sum()
            vap[mask] += row["volume"] * w

    poc_idx = np.argmax(vap)
    poc = centers[poc_idx]
    total = vap.sum()

    target = total * va_pct
    va_vol = vap[poc_idx]
    ui, li = poc_idx, poc_idx
    while va_vol < target:
        cu = ui < num_bins - 1
        cd = li > 0
        vu = vap[ui + 1] if cu else 0
        vd = vap[li - 1] if cd else 0
        if not cu and not cd:
            break
        if vu >= vd and cu:
            ui += 1; va_vol += vap[ui]
        elif cd:
            li -= 1; va_vol += vap[li]
        else:
            ui += 1; va_vol += vap[ui]

    vah, val = centers[ui], centers[li]

    # LVN detection
    avg = vap.mean()
    thresh = avg * lvn_sensitivity
    lvns = []
    for i in range(1, num_bins - 1):
        lm = vap[i] < vap[i-1] and vap[i] < vap[i+1]
        lo = vap[i] < thresh
        if lm or lo:
            lvns.append({"price": centers[i], "volume": vap[i], "index": i})

    lu_cands = [l for l in lvns if l["price"] > vah]
    lvn_upper = min(lu_cands, key=lambda x: x["price"])["price"] if lu_cands else vah + bw * 3

    ll_cands = [l for l in lvns if l["price"] < val]
    lvn_lower = max(ll_cands, key=lambda x: x["price"])["price"] if ll_cands else val - bw * 3

    return {
        "price_levels": centers, "volume_at_price": vap,
        "poc": poc, "vah": vah, "val": val,
        "lvn_upper": lvn_upper, "lvn_lower": lvn_lower,
        "all_lvns": lvns, "total_volume": total,
        "va_volume_pct": va_vol / total * 100, "bin_width": bw,
    }


def detect_vp_breakout_zones(df, vah, val, lvn_upper, lvn_lower):
    if df.empty:
        return pd.DataFrame()
    signals = []
    prev = None
    for _, row in df.iterrows():
        c = row["close"]
        if c > lvn_upper: s = "breakout_up"
        elif c > vah: s = "upper_zone"
        elif c < lvn_lower: s = "breakout_down"
        elif c < val: s = "lower_zone"
        else: s = "inside"

        if prev:
            if s == "breakout_up" and prev in ("inside", "upper_zone"):
                signals.append({"date": row["date"], "price": c, "type": "VP CONFIRMED ↑",
                                "direction": "buy", "confirmed": True})
            elif s == "upper_zone" and prev == "inside":
                signals.append({"date": row["date"], "price": c, "type": "VP PENDING ↑",
                                "direction": "buy", "confirmed": False})
            elif s == "inside" and prev == "upper_zone":
                signals.append({"date": row["date"], "price": c, "type": "VP REJECTED ↑",
                                "direction": "none", "confirmed": False})
            if s == "breakout_down" and prev in ("inside", "lower_zone"):
                signals.append({"date": row["date"], "price": c, "type": "VP CONFIRMED ↓",
                                "direction": "sell", "confirmed": True})
            elif s == "lower_zone" and prev == "inside":
                signals.append({"date": row["date"], "price": c, "type": "VP PENDING ↓",
                                "direction": "sell", "confirmed": False})
            elif s == "inside" and prev == "lower_zone":
                signals.append({"date": row["date"], "price": c, "type": "VP REJECTED ↓",
                                "direction": "none", "confirmed": False})
        prev = s
    return pd.DataFrame(signals)


def detect_balance(df, vah, val, threshold=0.70):
    if df.empty:
        return {"is_balanced": False, "pct_inside": 0}
    inside = ((df["close"] >= val) & (df["close"] <= vah)).sum()
    pct = inside / len(df)
    return {"is_balanced": pct >= threshold, "pct_inside": pct * 100,
            "bars_inside": inside, "total_bars": len(df)}


def filter_vp_period(df, period):
    if df.empty:
        return df, df
    today = df["date"].max().date()
    if period == "Previous Day":
        ds = sorted(df["date"].dt.date.unique())
        if len(ds) < 2: return df, df
        return df[df["date"].dt.date == ds[-2]], df[df["date"].dt.date == ds[-1]]
    elif period == "Previous Week":
        cws = today - timedelta(days=today.weekday())
        pws = cws - timedelta(days=7)
        return df[(df["date"].dt.date >= pws) & (df["date"].dt.date < cws)], \
               df[df["date"].dt.date >= cws]
    else:
        cws = today - timedelta(days=today.weekday())
        d = df[df["date"].dt.date >= cws]
        return d, d


# ══════════════════════════════════════════════════════════════════════════════
# CHART HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def add_candles(fig, df, row=1, col=1):
    fig.add_trace(go.Candlestick(
        x=df["date"], open=df["open"], high=df["high"],
        low=df["low"], close=df["close"], name="Price",
        increasing_line_color="#10b981", decreasing_line_color="#ef4444",
    ), row=row, col=col)


def add_hline(fig, y, color, name, dash="solid", width=1.5, row=1, col=1):
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode="lines", name=f"{name} ({y:.2f})",
        line=dict(color=color, width=width, dash=dash), showlegend=True,
    ), row=row, col=col)
    fig.add_hline(y=y, line_color=color, line_width=width, line_dash=dash,
                  row=row, col=col)


def add_markers(fig, signals_df, row=1, col=1):
    if signals_df.empty:
        return
    for _, s in signals_df.iterrows():
        d = s.get("direction", "")
        color = "#10b981" if d == "buy" else "#ef4444" if d == "sell" else "#f59e0b"
        sym = "triangle-up" if d == "buy" else "triangle-down" if d == "sell" else "diamond"
        fig.add_trace(go.Scatter(
            x=[s["date"]], y=[s["price"]],
            mode="markers", marker=dict(size=12, color=color, symbol=sym,
                                        line=dict(width=1, color="white")),
            name=s["type"], showlegend=False,
        ), row=row, col=col)


def base_layout(fig, title, height=600):
    fig.update_layout(
        title=title, template="plotly_dark", height=height,
        xaxis_rangeslider_visible=False, showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=1, xanchor="right",
                    font=dict(size=9)),
        margin=dict(l=50, r=20, t=60, b=30),
    )


# ══════════════════════════════════════════════════════════════════════════════
# MAIN UI
# ══════════════════════════════════════════════════════════════════════════════
def main():
    st.markdown("## 📊 Multi-Strategy Trading Dashboard")

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        api_key = st.text_input("FMP API Key", type="password")
        st.divider()
        symbol = st.text_input("Symbol", value="SPY").upper().strip()
        interval = st.selectbox("Intraday Interval", ["1min","5min","15min","30min","1hour"], index=1)
        days_back = st.number_input("Days of Data", 5, 60, 15)
        st.divider()
        run = st.button("🚀 Run All Strategies", type="primary", use_container_width=True)

    if not api_key:
        st.info("👈 Enter your **FMP API Key** to start. All 6 strategies will run at once.")
        return
    if not run:
        st.info("Click **🚀 Run All Strategies**")
        return

    # Fetch data
    with st.spinner(f"Fetching data for {symbol}..."):
        intra = fetch_intraday(symbol, api_key, interval, days_back)
        daily = fetch_daily(symbol, api_key, days=max(days_back * 2, 60))

    if intra.empty and daily.empty:
        st.error("No data. Check API key / symbol.")
        return

    if not intra.empty:
        st.success(f"Intraday: **{len(intra):,}** bars | Daily: **{len(daily):,}** bars")

    # ── TABS ──
    tabs = st.tabs([
        "📉 Gap Fill",
        "⏰ ORB",
        "😲 Oops",
        "📐 PBD",
        "4️⃣ Rule of 4",
        "📊 VP Zones",
    ])

    # ═══════════════════════════════════════
    # TAB 1: GAP FILL
    # ═══════════════════════════════════════
    with tabs[0]:
        st.subheader("📉 Gap Fill Strategy")
        gc1, gc2 = st.columns([1, 3])
        with gc1:
            gap_min = st.slider("Min Gap (pts)", 1.0, 30.0, 10.0, 0.5, key="gap_min")
        gap_signals = detect_gap_fill(daily, min_gap_pts=gap_min)

        if gap_signals.empty:
            st.info(f"No gaps ≥ {gap_min} pts found.")
        else:
            filled = gap_signals["filled"].sum()
            total = len(gap_signals)
            fill_rate = filled / total * 100

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Gaps", total)
            m2.metric("Filled", f"{filled}")
            m3.metric("Fill Rate", f"{fill_rate:.1f}%")
            m4.metric("Not Filled", f"{total - filled}")

            # Chart: last gap
            last = gap_signals.iloc[-1]
            last_idx = daily[daily["date"] == last["date"]].index[0]
            chart_df = daily.iloc[max(0, last_idx - 5):last_idx + 2]

            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=chart_df["date"], open=chart_df["open"],
                high=chart_df["high"], low=chart_df["low"], close=chart_df["close"],
                increasing_line_color="#10b981", decreasing_line_color="#ef4444",
            ))
            fig.add_hline(y=last["prev_close"], line_color="#3b82f6", line_dash="dash",
                          annotation_text=f"Prev Close {last['prev_close']}")
            fig.add_hline(y=last["open"], line_color="#f59e0b", line_dash="dot",
                          annotation_text=f"Gap Open {last['open']}")
            # Gap zone
            fig.add_hrect(y0=min(last["prev_close"], last["open"]),
                          y1=max(last["prev_close"], last["open"]),
                          fillcolor="rgba(59,130,246,0.08)",
                          line=dict(color="rgba(59,130,246,0.3)", dash="dash"))
            base_layout(fig, f"Gap Fill — Latest: {last['type']} | {last['status']}")
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(gap_signals.sort_values("date", ascending=False),
                         use_container_width=True, hide_index=True)

    # ═══════════════════════════════════════
    # TAB 2: ORB
    # ═══════════════════════════════════════
    with tabs[1]:
        st.subheader("⏰ Opening Range Breakout")
        oc1, oc2 = st.columns([1, 3])
        with oc1:
            or_mins = st.selectbox("OR Period (min)", [5, 15, 30], index=1, key="or_min")
        orb_signals, or_levels = detect_orb(intra, or_minutes=or_mins)

        if orb_signals.empty:
            st.info("No ORB signals found.")
        else:
            buy_n = len(orb_signals[orb_signals["direction"] == "buy"])
            sell_n = len(orb_signals[orb_signals["direction"] == "sell"])
            m1, m2, m3 = st.columns(3)
            m1.metric("Total ORB Signals", len(orb_signals))
            m2.metric("Breakout Up", buy_n)
            m3.metric("Breakout Down", sell_n)

            # Chart last day with ORB
            last_sig = orb_signals.iloc[-1]
            last_td = last_sig["trade_date"]
            day_data = intra[intra["date"].dt.date == last_td]
            orl = or_levels.get(last_td, {})

            fig = go.Figure()
            add_candles_simple(fig, day_data)
            if orl:
                fig.add_hline(y=orl["high"], line_color="#06b6d4", line_dash="dash",
                              annotation_text=f"OR High {orl['high']:.2f}")
                fig.add_hline(y=orl["low"], line_color="#06b6d4", line_dash="dash",
                              annotation_text=f"OR Low {orl['low']:.2f}")
                fig.add_hrect(y0=orl["low"], y1=orl["high"],
                              fillcolor="rgba(6,182,212,0.06)",
                              line=dict(color="rgba(6,182,212,0.2)", dash="dash"))
            # Signal marker
            color = "#10b981" if last_sig["direction"] == "buy" else "#ef4444"
            sym = "triangle-up" if last_sig["direction"] == "buy" else "triangle-down"
            fig.add_trace(go.Scatter(
                x=[last_sig["date"]], y=[last_sig["price"]],
                mode="markers", marker=dict(size=14, color=color, symbol=sym),
                name=last_sig["type"],
            ))
            base_layout(fig, f"ORB — {last_td} | {last_sig['type']}")
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(orb_signals.sort_values("date", ascending=False),
                         use_container_width=True, hide_index=True)

    # ═══════════════════════════════════════
    # TAB 3: OOPS
    # ═══════════════════════════════════════
    with tabs[2]:
        st.subheader("😲 Oops Strategy")
        oopc1, oopc2 = st.columns([1, 3])
        with oopc1:
            oops_gap = st.slider("Min Gap (pts)", 5.0, 30.0, 15.0, 1.0, key="oops_gap")
        oops_signals = detect_oops(daily, min_gap_pts=oops_gap)

        if oops_signals.empty:
            st.info(f"No Oops signals (gap ≥ {oops_gap} pts).")
        else:
            triggered = oops_signals["triggered"].sum()
            total = len(oops_signals)
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Oops", total)
            m2.metric("Triggered", f"{triggered}")
            m3.metric("Trigger Rate", f"{triggered/total*100:.1f}%")

            # Chart
            last = oops_signals.iloc[-1]
            idx = daily[daily["date"] == last["date"]].index[0]
            chart_df = daily.iloc[max(0, idx - 3):idx + 2]

            fig = go.Figure()
            add_candles_simple(fig, chart_df)
            fig.add_hline(y=last["prev_high"], line_color="#ec4899", line_dash="dash",
                          annotation_text=f"Prev High {last['prev_high']}")
            fig.add_hline(y=last["prev_low"], line_color="#ec4899", line_dash="dot",
                          annotation_text=f"Prev Low {last['prev_low']}")
            fig.add_hline(y=last["prev_close"], line_color="#3b82f6", line_dash="dash",
                          annotation_text=f"Prev Close {last['prev_close']}")
            base_layout(fig, f"Oops — {last['type']} | {last['status']}")
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(oops_signals.sort_values("date", ascending=False),
                         use_container_width=True, hide_index=True)

    # ═══════════════════════════════════════
    # TAB 4: PBD
    # ═══════════════════════════════════════
    with tabs[3]:
        st.subheader("📐 PBD Strategy (Consolidation Breakout)")
        pc1, pc2, pc3 = st.columns(3)
        with pc1:
            pbd_bars = st.slider("Consolidation Bars", 4, 20, 6, key="pbd_bars")
        with pc2:
            pbd_threshold = st.slider("Range Threshold", 0.2, 1.0, 0.5, 0.05, key="pbd_thresh")

        pbd_signals, consol_zones = detect_pbd(intra, consolidation_bars=pbd_bars,
                                                range_pct_threshold=pbd_threshold)
        if pbd_signals.empty:
            st.info("No PBD signals found. Try adjusting threshold.")
        else:
            buy_n = len(pbd_signals[pbd_signals["direction"] == "buy"])
            sell_n = len(pbd_signals[pbd_signals["direction"] == "sell"])
            m1, m2, m3 = st.columns(3)
            m1.metric("Total PBD", len(pbd_signals))
            m2.metric("Breakout ↑", buy_n)
            m3.metric("Breakdown ↓", sell_n)

            # Chart last signal
            last = pbd_signals.iloc[-1]
            nearby = intra[(intra["date"] >= last["date"] - timedelta(hours=4)) &
                           (intra["date"] <= last["date"] + timedelta(hours=1))]

            fig = go.Figure()
            add_candles_simple(fig, nearby)
            fig.add_hline(y=last["range_high"], line_color="#a855f7", line_dash="dash",
                          annotation_text=f"Range H {last['range_high']}")
            fig.add_hline(y=last["range_low"], line_color="#a855f7", line_dash="dash",
                          annotation_text=f"Range L {last['range_low']}")
            fig.add_hrect(y0=last["range_low"], y1=last["range_high"],
                          fillcolor="rgba(168,85,247,0.06)",
                          line=dict(color="rgba(168,85,247,0.2)", dash="dash"))
            color = "#10b981" if last["direction"] == "buy" else "#ef4444"
            sym = "triangle-up" if last["direction"] == "buy" else "triangle-down"
            fig.add_trace(go.Scatter(
                x=[last["date"]], y=[last["price"]],
                mode="markers", marker=dict(size=14, color=color, symbol=sym),
                name=last["type"],
            ))
            base_layout(fig, f"PBD — {last['type']}")
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(pbd_signals.sort_values("date", ascending=False),
                         use_container_width=True, hide_index=True)

    # ═══════════════════════════════════════
    # TAB 5: RULE OF 4
    # ═══════════════════════════════════════
    with tabs[4]:
        st.subheader("4️⃣ Rule of 4")
        st.caption("หลังเหตุการณ์สำคัญ (NFP/FOMC) — รอ 4 แท่งแรก แล้วเทรด breakout")
        rc1, rc2 = st.columns([1, 3])
        with rc1:
            r4_n = st.slider("N Bars", 3, 8, 4, key="r4_n")
            r4_all = st.checkbox("Apply to all days", value=True, key="r4_all")

        event_dates = None if r4_all else []
        r4_signals, r4_zones = detect_rule_of_4(intra, event_dates=event_dates, n_bars=r4_n)

        if r4_signals.empty:
            st.info("No Rule of 4 signals.")
        else:
            buy_n = len(r4_signals[r4_signals["direction"] == "buy"])
            sell_n = len(r4_signals[r4_signals["direction"] == "sell"])
            m1, m2, m3 = st.columns(3)
            m1.metric("Total R4 Signals", len(r4_signals))
            m2.metric("Buy ↑", buy_n)
            m3.metric("Sell ↓", sell_n)

            # Chart
            last = r4_signals.iloc[-1]
            day_data = intra[intra["date"].dt.date == last["trade_date"]]

            fig = go.Figure()
            add_candles_simple(fig, day_data)
            fig.add_hline(y=last["r4_high"], line_color="#f97316", line_dash="dash",
                          annotation_text=f"4-Bar High {last['r4_high']}")
            fig.add_hline(y=last["r4_low"], line_color="#f97316", line_dash="dash",
                          annotation_text=f"4-Bar Low {last['r4_low']}")
            fig.add_hrect(y0=last["r4_low"], y1=last["r4_high"],
                          fillcolor="rgba(249,115,22,0.06)",
                          line=dict(color="rgba(249,115,22,0.2)", dash="dash"))
            color = "#10b981" if last["direction"] == "buy" else "#ef4444"
            sym = "triangle-up" if last["direction"] == "buy" else "triangle-down"
            fig.add_trace(go.Scatter(
                x=[last["date"]], y=[last["price"]],
                mode="markers", marker=dict(size=14, color=color, symbol=sym),
                name=last["type"],
            ))
            base_layout(fig, f"Rule of 4 — {last['type']}")
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(r4_signals.sort_values("date", ascending=False).head(20),
                         use_container_width=True, hide_index=True)

    # ═══════════════════════════════════════
    # TAB 6: VP BREAKOUT ZONES
    # ═══════════════════════════════════════
    with tabs[5]:
        st.subheader("📊 Volume Profile Breakout Zones")
        vc1, vc2, vc3 = st.columns(3)
        with vc1:
            vp_period = st.selectbox("VP Period", ["Previous Day","Previous Week","Current Week"],
                                     key="vp_period")
        with vc2:
            vp_bins = st.slider("Bins", 20, 100, 50, key="vp_bins")
        with vc3:
            vp_va = st.slider("VA %", 50, 90, 70, key="vp_va")

        profile_df, current_df = filter_vp_period(intra, vp_period)
        if profile_df.empty or current_df.empty:
            st.warning("Not enough data for VP period.")
        else:
            vp = calculate_volume_profile(profile_df, vp_bins, vp_va / 100)
            if vp is None:
                st.error("Cannot compute VP.")
            else:
                balance = detect_balance(current_df, vp["vah"], vp["val"])
                vp_sigs = detect_vp_breakout_zones(current_df, vp["vah"], vp["val"],
                                                    vp["lvn_upper"], vp["lvn_lower"])

                # Metrics
                cols = st.columns(7)
                labels = ["LVN↑","VAH","POC","VAL","LVN↓","Balance","Signals"]
                vals = [vp["lvn_upper"], vp["vah"], vp["poc"], vp["val"], vp["lvn_lower"]]
                for c, l, v in zip(cols[:5], labels[:5], vals):
                    c.metric(l, f"{v:.2f}")
                cols[5].metric("Balance", f"{balance['pct_inside']:.0f}%")
                cols[6].metric("Signals", len(vp_sigs))

                # Zone info
                z1, z2 = st.columns(2)
                z1.markdown(f'<div class="zone-box zone-upper">'
                            f'🔴 Upper Zone: VAH {vp["vah"]:.2f} → LVN {vp["lvn_upper"]:.2f}'
                            f' ({vp["lvn_upper"]-vp["vah"]:.2f} pts)</div>',
                            unsafe_allow_html=True)
                z2.markdown(f'<div class="zone-box zone-lower">'
                            f'🟢 Lower Zone: VAL {vp["val"]:.2f} → LVN {vp["lvn_lower"]:.2f}'
                            f' ({vp["val"]-vp["lvn_lower"]:.2f} pts)</div>',
                            unsafe_allow_html=True)

                # Chart with VP
                fig = make_subplots(rows=1, cols=2, column_widths=[0.8, 0.2],
                                    shared_yaxes=True, horizontal_spacing=0.02)
                fig.add_trace(go.Candlestick(
                    x=current_df["date"], open=current_df["open"],
                    high=current_df["high"], low=current_df["low"], close=current_df["close"],
                    increasing_line_color="#10b981", decreasing_line_color="#ef4444",
                    name="Price",
                ), row=1, col=1)

                xr = [current_df["date"].min(), current_df["date"].max()]
                # Zones
                fig.add_shape(type="rect", x0=xr[0], x1=xr[1],
                              y0=vp["vah"], y1=vp["lvn_upper"],
                              fillcolor="rgba(239,83,80,0.08)",
                              line=dict(color="rgba(239,83,80,0.4)", dash="dash"),
                              row=1, col=1)
                fig.add_shape(type="rect", x0=xr[0], x1=xr[1],
                              y0=vp["lvn_lower"], y1=vp["val"],
                              fillcolor="rgba(16,185,129,0.08)",
                              line=dict(color="rgba(16,185,129,0.4)", dash="dash"),
                              row=1, col=1)
                fig.add_shape(type="rect", x0=xr[0], x1=xr[1],
                              y0=vp["val"], y1=vp["vah"],
                              fillcolor="rgba(245,158,11,0.04)", line=dict(width=0),
                              row=1, col=1)

                # Lines
                for price, label, color, dash in [
                    (vp["lvn_upper"], "LVN↑", "#a855f7", "dot"),
                    (vp["vah"], "VAH", "#ef4444", "solid"),
                    (vp["poc"], "POC", "#f59e0b", "dash"),
                    (vp["val"], "VAL", "#10b981", "solid"),
                    (vp["lvn_lower"], "LVN↓", "#a855f7", "dot"),
                ]:
                    fig.add_trace(go.Scatter(
                        x=xr, y=[price]*2, mode="lines",
                        name=f"{label} {price:.2f}",
                        line=dict(color=color, width=1.5 if "LVN" not in label else 1, dash=dash),
                    ), row=1, col=1)

                # VP histogram
                vp_colors = []
                for p in vp["price_levels"]:
                    if vp["val"] <= p <= vp["vah"]:
                        vp_colors.append("rgba(245,158,11,0.5)")
                    elif vp["vah"] < p <= vp["lvn_upper"]:
                        vp_colors.append("rgba(239,83,80,0.3)")
                    elif vp["lvn_lower"] <= p < vp["val"]:
                        vp_colors.append("rgba(16,185,129,0.3)")
                    else:
                        vp_colors.append("rgba(100,100,100,0.2)")

                fig.add_trace(go.Bar(
                    x=vp["volume_at_price"], y=vp["price_levels"],
                    orientation="h", marker_color=vp_colors, showlegend=False,
                ), row=1, col=2)

                # Signal markers
                if not vp_sigs.empty:
                    add_markers(fig, vp_sigs, row=1, col=1)

                base_layout(fig, f"VP Zones — {symbol} ({vp_period})", height=650)
                fig.update_yaxes(showticklabels=False, row=1, col=2)
                st.plotly_chart(fig, use_container_width=True)

                if not vp_sigs.empty:
                    st.dataframe(vp_sigs.sort_values("date", ascending=False),
                                 use_container_width=True, hide_index=True)


def add_candles_simple(fig, df):
    """Add candlestick to a simple go.Figure."""
    fig.add_trace(go.Candlestick(
        x=df["date"], open=df["open"], high=df["high"],
        low=df["low"], close=df["close"],
        increasing_line_color="#10b981", decreasing_line_color="#ef4444",
        name="Price",
    ))


if __name__ == "__main__":
    main()
