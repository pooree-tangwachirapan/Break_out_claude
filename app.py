"""
Multi-Strategy Trading Dashboard — Streamlit App
==================================================
6 Strategies:
  1. Gap Fill Strategy          (Daily — FMP)
  2. Opening Range Breakout     (Intraday — yfinance)
  3. Oops Strategy              (Daily — FMP)
  4. PBD (Consolidation Break)  (Intraday — yfinance)
  5. Rule of 4 (Post-Event)     (Intraday — yfinance)
  6. VP Breakout Zones          (Intraday — yfinance)

Data Sources:
  - FMP Stable API  → daily OHLCV (free tier OK)
  - yfinance        → intraday OHLCV (free, no key needed)
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import yfinance as yf
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
.stTabs [aria-selected="true"] { background: #1e293b; border-color: #3b82f6; }
.metric-card {
    background: linear-gradient(135deg,#1a1a2e,#16213e);
    border-radius: 12px; padding: 0.9rem; text-align: center;
    border: 1px solid #0f3460;
}
.metric-label { color: #8899aa; font-size: 0.7rem; text-transform: uppercase; }
.metric-value { color: #e0e0e0; font-size: 1.2rem; font-weight: 700; }
.zone-box { border-radius: 8px; padding: 0.6rem 1rem; margin-bottom: 0.5rem; font-size: 0.82rem; }
.zone-upper { background: rgba(239,83,80,0.08); border-left: 4px solid #ef5350; }
.zone-lower { background: rgba(38,166,154,0.08); border-left: 4px solid #26a69a; }
.src-badge {
    display: inline-block; font-size: 0.6rem; padding: 2px 8px;
    border-radius: 10px; font-weight: 600; margin-left: 6px;
}
.src-fmp { background: #0f3460; color: #60a5fa; }
.src-yf  { background: #1a3a1a; color: #6ee7b7; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# DATA FETCHING
# ══════════════════════════════════════════════════════════════════════════════
FMP_BASE = "https://financialmodelingprep.com/stable"

# ── yfinance interval mapping ──
YF_INTERVAL_MAP = {
    "1min": "1m",
    "5min": "5m",
    "15min": "15m",
    "30min": "30m",
    "1hour": "1h",
}

# yfinance max period per interval
YF_MAX_DAYS = {
    "1m": 7,
    "5m": 60,
    "15m": 60,
    "30m": 60,
    "1h": 730,
}


@st.cache_data(ttl=300)
def fetch_intraday_yf(symbol: str, interval: str = "5min", days_back: int = 15) -> pd.DataFrame:
    """Fetch intraday data from yfinance (FREE, no API key)."""
    yf_interval = YF_INTERVAL_MAP.get(interval, "5m")
    max_days = YF_MAX_DAYS.get(yf_interval, 60)
    actual_days = min(days_back, max_days)

    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=f"{actual_days}d", interval=yf_interval)

        if df.empty:
            return pd.DataFrame()

        df = df.reset_index()

        # Normalize column names (yfinance capitalizes them)
        rename_map = {}
        for col in df.columns:
            lower = col.lower()
            if lower in ("date", "datetime"):
                rename_map[col] = "date"
            elif lower in ("open", "high", "low", "close", "volume"):
                rename_map[col] = lower
        df = df.rename(columns=rename_map)

        # Ensure date column exists
        if "date" not in df.columns:
            # Try index
            df = df.reset_index()
            for col in df.columns:
                if "date" in col.lower() or "time" in col.lower():
                    df = df.rename(columns={col: "date"})
                    break

        if "date" not in df.columns:
            return pd.DataFrame()

        df["date"] = pd.to_datetime(df["date"])
        # Remove timezone info if present
        if df["date"].dt.tz is not None:
            df["date"] = df["date"].dt.tz_localize(None)

        cols = [c for c in ["date", "open", "high", "low", "close", "volume"] if c in df.columns]
        df = df[cols].sort_values("date").reset_index(drop=True)
        return df

    except Exception as e:
        st.error(f"yfinance error: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def fetch_daily_fmp(symbol: str, api_key: str, days: int = 60) -> pd.DataFrame:
    """Fetch daily data from FMP stable API (free tier OK)."""
    if not api_key:
        st.warning("FMP API Key not set — trying yfinance for daily data too.")
        return fetch_daily_yf(symbol, days)

    url = f"{FMP_BASE}/historical-price-eod/full"
    try:
        r = requests.get(url, params={"symbol": symbol, "apikey": api_key}, timeout=15)
        r.raise_for_status()
        data = r.json()
        if not data or isinstance(data, dict):
            st.warning("FMP returned no daily data — falling back to yfinance.")
            return fetch_daily_yf(symbol, days)

        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        cols = [c for c in ["date", "open", "high", "low", "close", "volume"] if c in df.columns]
        return df[cols].tail(days).reset_index(drop=True)
    except Exception as e:
        st.warning(f"FMP error ({e}) — falling back to yfinance.")
        return fetch_daily_yf(symbol, days)


@st.cache_data(ttl=300)
def fetch_daily_yf(symbol: str, days: int = 60) -> pd.DataFrame:
    """Fallback: fetch daily data from yfinance."""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=f"{days}d", interval="1d")
        if df.empty:
            return pd.DataFrame()
        df = df.reset_index()
        rename_map = {}
        for col in df.columns:
            lower = col.lower()
            if lower in ("date", "datetime"):
                rename_map[col] = "date"
            elif lower in ("open", "high", "low", "close", "volume"):
                rename_map[col] = lower
        df = df.rename(columns=rename_map)
        if "date" not in df.columns:
            df = df.reset_index()
            for col in df.columns:
                if "date" in col.lower():
                    df = df.rename(columns={col: "date"})
                    break
        df["date"] = pd.to_datetime(df["date"])
        if df["date"].dt.tz is not None:
            df["date"] = df["date"].dt.tz_localize(None)
        cols = [c for c in ["date", "open", "high", "low", "close", "volume"] if c in df.columns]
        return df[cols].sort_values("date").reset_index(drop=True)
    except Exception as e:
        st.error(f"yfinance daily error: {e}")
        return pd.DataFrame()


# ══════════════════════════════════════════════════════════════════════════════
# STRATEGY 1: GAP FILL  (Daily data)
# ══════════════════════════════════════════════════════════════════════════════
def detect_gap_fill(daily_df, min_gap_pts=10):
    if len(daily_df) < 2:
        return pd.DataFrame()
    signals = []
    for i in range(1, len(daily_df)):
        prev = daily_df.iloc[i - 1]
        curr = daily_df.iloc[i]
        gap = curr["open"] - prev["close"]
        if abs(gap) < min_gap_pts:
            continue
        if gap < 0:
            filled = curr["high"] >= prev["close"]
            signals.append({
                "date": curr["date"], "type": "GAP DOWN → BUY",
                "gap_size": round(abs(gap), 2),
                "prev_close": round(prev["close"], 2),
                "open": round(curr["open"], 2),
                "filled": filled,
                "status": "FILLED ✅" if filled else "NOT FILLED ❌",
                "direction": "buy",
                "close": round(curr["close"], 2),
            })
        else:
            filled = curr["low"] <= prev["close"]
            signals.append({
                "date": curr["date"], "type": "GAP UP → SELL",
                "gap_size": round(abs(gap), 2),
                "prev_close": round(prev["close"], 2),
                "open": round(curr["open"], 2),
                "filled": filled,
                "status": "FILLED ✅" if filled else "NOT FILLED ❌",
                "direction": "sell",
                "close": round(curr["close"], 2),
            })
    return pd.DataFrame(signals)


# ══════════════════════════════════════════════════════════════════════════════
# STRATEGY 2: OPENING RANGE BREAKOUT  (Intraday data)
# ══════════════════════════════════════════════════════════════════════════════
def detect_orb(intraday_df, or_minutes=15):
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

        found = False
        for _, bar in after_or.iterrows():
            if not found:
                if bar["close"] > or_high:
                    signals.append({
                        "date": bar["date"], "trade_date": trade_date,
                        "type": "ORB BREAKOUT ↑",
                        "price": round(bar["close"], 2),
                        "or_high": round(or_high, 2),
                        "or_low": round(or_low, 2),
                        "direction": "buy", "status": "SIGNAL",
                    })
                    found = True
                elif bar["close"] < or_low:
                    signals.append({
                        "date": bar["date"], "trade_date": trade_date,
                        "type": "ORB BREAKOUT ↓",
                        "price": round(bar["close"], 2),
                        "or_high": round(or_high, 2),
                        "or_low": round(or_low, 2),
                        "direction": "sell", "status": "SIGNAL",
                    })
                    found = True
    return pd.DataFrame(signals), or_levels


# ══════════════════════════════════════════════════════════════════════════════
# STRATEGY 3: OOPS  (Daily data)
# ══════════════════════════════════════════════════════════════════════════════
def detect_oops(daily_df, min_gap_pts=15):
    if len(daily_df) < 2:
        return pd.DataFrame()
    signals = []
    for i in range(1, len(daily_df)):
        prev = daily_df.iloc[i - 1]
        curr = daily_df.iloc[i]
        gap = curr["open"] - prev["close"]
        prev_green = prev["close"] > prev["open"]
        prev_red = prev["close"] < prev["open"]

        if prev_green and gap >= min_gap_pts:
            triggered = curr["low"] <= prev["high"]
            signals.append({
                "date": curr["date"], "type": "OOPS SELL",
                "gap_size": round(gap, 2),
                "prev_high": round(prev["high"], 2),
                "prev_low": round(prev["low"], 2),
                "prev_close": round(prev["close"], 2),
                "open": round(curr["open"], 2),
                "triggered": triggered,
                "status": "TRIGGERED ✅" if triggered else "NO TRIGGER ❌",
                "direction": "sell",
            })
        if prev_red and gap <= -min_gap_pts:
            triggered = curr["high"] >= prev["low"]
            signals.append({
                "date": curr["date"], "type": "OOPS BUY",
                "gap_size": round(abs(gap), 2),
                "prev_high": round(prev["high"], 2),
                "prev_low": round(prev["low"], 2),
                "prev_close": round(prev["close"], 2),
                "open": round(curr["open"], 2),
                "triggered": triggered,
                "status": "TRIGGERED ✅" if triggered else "NO TRIGGER ❌",
                "direction": "buy",
            })
    return pd.DataFrame(signals)


# ══════════════════════════════════════════════════════════════════════════════
# STRATEGY 4: PBD  (Intraday data)
# ══════════════════════════════════════════════════════════════════════════════
def detect_pbd(intraday_df, lookback=20, consolidation_bars=6,
               range_pct_threshold=0.5):
    if len(intraday_df) < lookback + consolidation_bars:
        return pd.DataFrame(), []
    df = intraday_df.copy()
    df["bar_range"] = df["high"] - df["low"]
    avg_range = df["bar_range"].rolling(lookback).mean()

    signals = []
    consol_zones = []
    i = consolidation_bars
    while i < len(df):
        window = df.iloc[i - consolidation_bars:i]
        wh = window["high"].max()
        wl = window["low"].min()
        wr = wh - wl
        ar = avg_range.iloc[i] if pd.notna(avg_range.iloc[i]) else df["bar_range"].mean()

        if wr < ar * consolidation_bars * range_pct_threshold:
            consol_zones.append({
                "start_date": window["date"].iloc[0],
                "end_date": window["date"].iloc[-1],
                "high": wh, "low": wl,
            })
            for j in range(i, min(i + 10, len(df))):
                bar = df.iloc[j]
                if bar["close"] > wh:
                    signals.append({
                        "date": bar["date"], "type": "PBD BREAKOUT ↑",
                        "price": round(bar["close"], 2),
                        "range_high": round(wh, 2), "range_low": round(wl, 2),
                        "direction": "buy", "status": "BREAKOUT",
                    })
                    i = j + 1; break
                elif bar["close"] < wl:
                    signals.append({
                        "date": bar["date"], "type": "PBD BREAKDOWN ↓",
                        "price": round(bar["close"], 2),
                        "range_high": round(wh, 2), "range_low": round(wl, 2),
                        "direction": "sell", "status": "BREAKDOWN",
                    })
                    i = j + 1; break
            else:
                i += 1
        else:
            i += 1
    return pd.DataFrame(signals), consol_zones


# ══════════════════════════════════════════════════════════════════════════════
# STRATEGY 5: RULE OF 4  (Intraday data)
# ══════════════════════════════════════════════════════════════════════════════
def detect_rule_of_4(intraday_df, event_dates=None, n_bars=4):
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
        rh = first_n["high"].max()
        rl = first_n["low"].min()
        r4_zones.append({
            "date": td, "start": first_n["date"].iloc[0],
            "end": first_n["date"].iloc[-1], "high": rh, "low": rl,
        })
        found = False
        for _, bar in after_n.iterrows():
            if not found:
                if bar["close"] > rh:
                    signals.append({
                        "date": bar["date"], "trade_date": td,
                        "type": "RULE OF 4 → BUY ↑",
                        "price": round(bar["close"], 2),
                        "r4_high": round(rh, 2), "r4_low": round(rl, 2),
                        "direction": "buy",
                    })
                    found = True
                elif bar["close"] < rl:
                    signals.append({
                        "date": bar["date"], "trade_date": td,
                        "type": "RULE OF 4 → SELL ↓",
                        "price": round(bar["close"], 2),
                        "r4_high": round(rh, 2), "r4_low": round(rl, 2),
                        "direction": "sell",
                    })
                    found = True
    return pd.DataFrame(signals), r4_zones


# ══════════════════════════════════════════════════════════════════════════════
# STRATEGY 6: VOLUME PROFILE BREAKOUT ZONES  (Intraday data)
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
            w = 1 - (d / md) * 0.5; w /= w.sum()
            vap[mask] += row["volume"] * w
    poc_idx = np.argmax(vap); poc = centers[poc_idx]; total = vap.sum()
    target = total * va_pct; va_vol = vap[poc_idx]; ui, li = poc_idx, poc_idx
    while va_vol < target:
        cu = ui < num_bins - 1; cd = li > 0
        vu = vap[ui + 1] if cu else 0; vd = vap[li - 1] if cd else 0
        if not cu and not cd: break
        if vu >= vd and cu: ui += 1; va_vol += vap[ui]
        elif cd: li -= 1; va_vol += vap[li]
        else: ui += 1; va_vol += vap[ui]
    vah, val = centers[ui], centers[li]
    avg = vap.mean(); thresh = avg * lvn_sensitivity
    lvns = []
    for i in range(1, num_bins - 1):
        lm = vap[i] < vap[i-1] and vap[i] < vap[i+1]
        lo = vap[i] < thresh
        if lm or lo:
            lvns.append({"price": centers[i], "volume": vap[i], "index": i})
    lu = [l for l in lvns if l["price"] > vah]
    lvn_upper = min(lu, key=lambda x: x["price"])["price"] if lu else vah + bw * 3
    ll = [l for l in lvns if l["price"] < val]
    lvn_lower = max(ll, key=lambda x: x["price"])["price"] if ll else val - bw * 3
    return {
        "price_levels": centers, "volume_at_price": vap,
        "poc": poc, "vah": vah, "val": val,
        "lvn_upper": lvn_upper, "lvn_lower": lvn_lower,
        "all_lvns": lvns, "total_volume": total,
        "va_volume_pct": va_vol / total * 100, "bin_width": bw,
    }


def detect_vp_breakout_zones(df, vah, val, lvn_upper, lvn_lower):
    if df.empty: return pd.DataFrame()
    signals = []; prev = None
    for _, row in df.iterrows():
        c = row["close"]
        if c > lvn_upper: s = "breakout_up"
        elif c > vah: s = "upper_zone"
        elif c < lvn_lower: s = "breakout_down"
        elif c < val: s = "lower_zone"
        else: s = "inside"
        if prev:
            if s == "breakout_up" and prev in ("inside", "upper_zone"):
                signals.append({"date": row["date"], "price": c, "type": "VP CONFIRMED ↑", "direction": "buy", "confirmed": True})
            elif s == "upper_zone" and prev == "inside":
                signals.append({"date": row["date"], "price": c, "type": "VP PENDING ↑", "direction": "buy", "confirmed": False})
            elif s == "inside" and prev == "upper_zone":
                signals.append({"date": row["date"], "price": c, "type": "VP REJECTED ↑", "direction": "none", "confirmed": False})
            if s == "breakout_down" and prev in ("inside", "lower_zone"):
                signals.append({"date": row["date"], "price": c, "type": "VP CONFIRMED ↓", "direction": "sell", "confirmed": True})
            elif s == "lower_zone" and prev == "inside":
                signals.append({"date": row["date"], "price": c, "type": "VP PENDING ↓", "direction": "sell", "confirmed": False})
            elif s == "inside" and prev == "lower_zone":
                signals.append({"date": row["date"], "price": c, "type": "VP REJECTED ↓", "direction": "none", "confirmed": False})
        prev = s
    return pd.DataFrame(signals)


def detect_balance(df, vah, val, threshold=0.70):
    if df.empty: return {"is_balanced": False, "pct_inside": 0}
    inside = ((df["close"] >= val) & (df["close"] <= vah)).sum()
    pct = inside / len(df)
    return {"is_balanced": pct >= threshold, "pct_inside": pct * 100,
            "bars_inside": inside, "total_bars": len(df)}


def filter_vp_period(df, period):
    if df.empty: return df, df
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
        d = df[df["date"].dt.date >= cws]; return d, d


# ══════════════════════════════════════════════════════════════════════════════
# CHART HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def add_candles_simple(fig, df):
    fig.add_trace(go.Candlestick(
        x=df["date"], open=df["open"], high=df["high"],
        low=df["low"], close=df["close"], name="Price",
        increasing_line_color="#10b981", decreasing_line_color="#ef4444",
    ))


def add_markers(fig, signals_df, row=1, col=1):
    if signals_df.empty: return
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
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=1,
                    xanchor="right", font=dict(size=9)),
        margin=dict(l=50, r=20, t=60, b=30),
    )


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    st.markdown("## 📊 Multi-Strategy Trading Dashboard")
    st.caption("Daily data → FMP API  |  Intraday data → yfinance (free)")

    # API key
    try:
        api_key = st.secrets["FMP_API_KEY"]
    except Exception:
        api_key = ""

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        symbol = st.text_input("Symbol", value="SPY").upper().strip()

        st.divider()
        st.markdown("**Intraday** <span class='src-badge src-yf'>yfinance</span>",
                    unsafe_allow_html=True)
        interval = st.selectbox("Interval", ["1min", "5min", "15min", "30min", "1hour"], index=1)
        days_back_intra = st.number_input("Intraday Days", 1, 60, 10,
                                          help="yfinance: 1m→7d max, 5m/15m/30m→60d max")

        st.divider()
        st.markdown("**Daily** <span class='src-badge src-fmp'>FMP</span>",
                    unsafe_allow_html=True)
        days_back_daily = st.number_input("Daily Days", 10, 365, 60)

        if not api_key:
            st.info("💡 FMP key not set — daily data will use yfinance fallback.")

        st.divider()
        run = st.button("🚀 Run All Strategies", type="primary", use_container_width=True)

    if not run:
        st.info("Configure settings and click **🚀 Run All Strategies**")
        return

    # ── Fetch Data ──
    with st.spinner(f"Fetching intraday {interval} for {symbol} via yfinance..."):
        intra = fetch_intraday_yf(symbol, interval, days_back_intra)

    with st.spinner(f"Fetching daily for {symbol}..."):
        daily = fetch_daily_fmp(symbol, api_key, days_back_daily)

    if intra.empty and daily.empty:
        st.error("No data returned. Check symbol and try again.")
        return

    # Status bar
    src_intra = "yfinance"
    src_daily = "FMP" if api_key else "yfinance"
    intra_txt = f"Intraday ({src_intra}): **{len(intra):,}** bars" if not intra.empty else f"Intraday: N/A"
    daily_txt = f"Daily ({src_daily}): **{len(daily):,}** bars" if not daily.empty else "Daily: N/A"
    st.success(f"{intra_txt}  |  {daily_txt}")

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
    # TAB 1: GAP FILL (Daily → FMP)
    # ═══════════════════════════════════════
    with tabs[0]:
        st.subheader("📉 Gap Fill Strategy")
        st.caption(f"Data: Daily ({src_daily})")
        if daily.empty:
            st.warning("No daily data available.")
        else:
            gc1, _ = st.columns([1, 3])
            with gc1:
                gap_min = st.slider("Min Gap (pts)", 0.5, 30.0, 3.0, 0.5, key="gap_min")
            gap_signals = detect_gap_fill(daily, min_gap_pts=gap_min)

            if gap_signals.empty:
                st.info(f"No gaps ≥ {gap_min} pts found in {len(daily)} daily bars.")
            else:
                filled = gap_signals["filled"].sum()
                total = len(gap_signals)
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Total Gaps", total)
                m2.metric("Filled", filled)
                m3.metric("Fill Rate", f"{filled/total*100:.1f}%")
                m4.metric("Not Filled", total - filled)

                last = gap_signals.iloc[-1]
                last_idx = daily[daily["date"] == last["date"]].index[0]
                chart_df = daily.iloc[max(0, last_idx - 5):last_idx + 2]
                fig = go.Figure()
                add_candles_simple(fig, chart_df)
                fig.add_hline(y=last["prev_close"], line_color="#3b82f6", line_dash="dash",
                              annotation_text=f"Prev Close {last['prev_close']}")
                fig.add_hline(y=last["open"], line_color="#f59e0b", line_dash="dot",
                              annotation_text=f"Gap Open {last['open']}")
                fig.add_hrect(y0=min(last["prev_close"], last["open"]),
                              y1=max(last["prev_close"], last["open"]),
                              fillcolor="rgba(59,130,246,0.08)",
                              line=dict(color="rgba(59,130,246,0.3)", dash="dash"))
                base_layout(fig, f"Gap Fill — {last['type']} | {last['status']}")
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(gap_signals.sort_values("date", ascending=False),
                             use_container_width=True, hide_index=True)

    # ═══════════════════════════════════════
    # TAB 2: ORB (Intraday → yfinance)
    # ═══════════════════════════════════════
    with tabs[1]:
        st.subheader("⏰ Opening Range Breakout")
        st.caption("Data: Intraday (yfinance)")
        if intra.empty:
            st.warning("No intraday data available.")
        else:
            oc1, _ = st.columns([1, 3])
            with oc1:
                or_mins = st.selectbox("OR Period (min)", [5, 15, 30], index=1, key="or_min")
            orb_signals, or_levels = detect_orb(intra, or_minutes=or_mins)

            if orb_signals.empty:
                st.info("No ORB signals found.")
            else:
                buy_n = len(orb_signals[orb_signals["direction"] == "buy"])
                sell_n = len(orb_signals[orb_signals["direction"] == "sell"])
                m1, m2, m3 = st.columns(3)
                m1.metric("Total ORB", len(orb_signals))
                m2.metric("Breakout Up", buy_n)
                m3.metric("Breakout Down", sell_n)

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
    # TAB 3: OOPS (Daily → FMP)
    # ═══════════════════════════════════════
    with tabs[2]:
        st.subheader("😲 Oops Strategy")
        st.caption(f"Data: Daily ({src_daily})")
        if daily.empty:
            st.warning("No daily data available.")
        else:
            oc1, _ = st.columns([1, 3])
            with oc1:
                oops_gap = st.slider("Min Gap (pts)", 1.0, 30.0, 5.0, 0.5, key="oops_gap")
            oops_signals = detect_oops(daily, min_gap_pts=oops_gap)

            if oops_signals.empty:
                st.info(f"No Oops signals (gap ≥ {oops_gap} pts).")
            else:
                triggered = oops_signals["triggered"].sum()
                total = len(oops_signals)
                m1, m2, m3 = st.columns(3)
                m1.metric("Total Oops", total)
                m2.metric("Triggered", triggered)
                m3.metric("Rate", f"{triggered/total*100:.1f}%")

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
    # TAB 4: PBD (Intraday → yfinance)
    # ═══════════════════════════════════════
    with tabs[3]:
        st.subheader("📐 PBD Strategy (Consolidation Breakout)")
        st.caption("Data: Intraday (yfinance)")
        if intra.empty:
            st.warning("No intraday data available.")
        else:
            pc1, pc2, _ = st.columns(3)
            with pc1:
                pbd_bars = st.slider("Consolidation Bars", 4, 20, 6, key="pbd_bars")
            with pc2:
                pbd_thresh = st.slider("Range Threshold", 0.2, 1.0, 0.5, 0.05, key="pbd_thresh")

            pbd_signals, consol = detect_pbd(intra, consolidation_bars=pbd_bars,
                                             range_pct_threshold=pbd_thresh)
            if pbd_signals.empty:
                st.info("No PBD signals. Try adjusting threshold.")
            else:
                buy_n = len(pbd_signals[pbd_signals["direction"] == "buy"])
                sell_n = len(pbd_signals[pbd_signals["direction"] == "sell"])
                m1, m2, m3 = st.columns(3)
                m1.metric("Total PBD", len(pbd_signals))
                m2.metric("Breakout ↑", buy_n)
                m3.metric("Breakdown ↓", sell_n)

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
    # TAB 5: RULE OF 4 (Intraday → yfinance)
    # ═══════════════════════════════════════
    with tabs[4]:
        st.subheader("4️⃣ Rule of 4")
        st.caption("Data: Intraday (yfinance) — รอ N แท่งแรก แล้วเทรด breakout")
        if intra.empty:
            st.warning("No intraday data available.")
        else:
            rc1, _ = st.columns([1, 3])
            with rc1:
                r4_n = st.slider("N Bars", 3, 8, 4, key="r4_n")
                r4_all = st.checkbox("Apply all days", value=True, key="r4_all")

            evts = None if r4_all else []
            r4_signals, r4_zones = detect_rule_of_4(intra, event_dates=evts, n_bars=r4_n)

            if r4_signals.empty:
                st.info("No Rule of 4 signals.")
            else:
                buy_n = len(r4_signals[r4_signals["direction"] == "buy"])
                sell_n = len(r4_signals[r4_signals["direction"] == "sell"])
                m1, m2, m3 = st.columns(3)
                m1.metric("Total R4", len(r4_signals))
                m2.metric("Buy ↑", buy_n)
                m3.metric("Sell ↓", sell_n)

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
    # TAB 6: VP BREAKOUT ZONES (Intraday → yfinance)
    # ═══════════════════════════════════════
    with tabs[5]:
        st.subheader("📊 Volume Profile Breakout Zones")
        st.caption("Data: Intraday (yfinance)")
        if intra.empty:
            st.warning("No intraday data. VP Zones requires intraday bars.")
        else:
            vc1, vc2, vc3 = st.columns(3)
            with vc1:
                vp_period = st.selectbox("VP Period",
                                         ["Previous Day", "Previous Week", "Current Week"],
                                         key="vp_period")
            with vc2:
                vp_bins = st.slider("Bins", 20, 100, 50, key="vp_bins")
            with vc3:
                vp_va = st.slider("VA %", 50, 90, 70, key="vp_va")

            profile_df, current_df = filter_vp_period(intra, vp_period)
            if profile_df.empty or current_df.empty:
                st.warning("Not enough data for selected VP period.")
            else:
                vp = calculate_volume_profile(profile_df, vp_bins, vp_va / 100)
                if vp is None:
                    st.error("Cannot compute Volume Profile.")
                else:
                    balance = detect_balance(current_df, vp["vah"], vp["val"])
                    vp_sigs = detect_vp_breakout_zones(
                        current_df, vp["vah"], vp["val"],
                        vp["lvn_upper"], vp["lvn_lower"])

                    cols = st.columns(7)
                    for c, l, v in zip(cols[:5],
                                       ["LVN↑", "VAH", "POC", "VAL", "LVN↓"],
                                       [vp["lvn_upper"], vp["vah"], vp["poc"],
                                        vp["val"], vp["lvn_lower"]]):
                        c.metric(l, f"{v:.2f}")
                    cols[5].metric("Balance", f"{balance['pct_inside']:.0f}%")
                    cols[6].metric("Signals", len(vp_sigs))

                    z1, z2 = st.columns(2)
                    z1.markdown(
                        f'<div class="zone-box zone-upper">'
                        f'🔴 Upper: VAH {vp["vah"]:.2f} → LVN {vp["lvn_upper"]:.2f}'
                        f' ({vp["lvn_upper"]-vp["vah"]:.2f})</div>',
                        unsafe_allow_html=True)
                    z2.markdown(
                        f'<div class="zone-box zone-lower">'
                        f'🟢 Lower: VAL {vp["val"]:.2f} → LVN {vp["lvn_lower"]:.2f}'
                        f' ({vp["val"]-vp["lvn_lower"]:.2f})</div>',
                        unsafe_allow_html=True)

                    # Chart
                    fig = make_subplots(rows=1, cols=2, column_widths=[0.8, 0.2],
                                        shared_yaxes=True, horizontal_spacing=0.02)
                    fig.add_trace(go.Candlestick(
                        x=current_df["date"], open=current_df["open"],
                        high=current_df["high"], low=current_df["low"],
                        close=current_df["close"], name="Price",
                        increasing_line_color="#10b981",
                        decreasing_line_color="#ef4444",
                    ), row=1, col=1)

                    xr = [current_df["date"].min(), current_df["date"].max()]
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
                                  fillcolor="rgba(245,158,11,0.04)",
                                  line=dict(width=0), row=1, col=1)

                    for price, label, clr, dash in [
                        (vp["lvn_upper"], "LVN↑", "#a855f7", "dot"),
                        (vp["vah"], "VAH", "#ef4444", "solid"),
                        (vp["poc"], "POC", "#f59e0b", "dash"),
                        (vp["val"], "VAL", "#10b981", "solid"),
                        (vp["lvn_lower"], "LVN↓", "#a855f7", "dot"),
                    ]:
                        fig.add_trace(go.Scatter(
                            x=xr, y=[price]*2, mode="lines",
                            name=f"{label} {price:.2f}",
                            line=dict(color=clr,
                                      width=1.5 if "LVN" not in label else 1,
                                      dash=dash),
                        ), row=1, col=1)

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

                    if not vp_sigs.empty:
                        add_markers(fig, vp_sigs, row=1, col=1)

                    base_layout(fig, f"VP Zones — {symbol} ({vp_period})", height=650)
                    fig.update_yaxes(showticklabels=False, row=1, col=2)
                    st.plotly_chart(fig, use_container_width=True)

                    if not vp_sigs.empty:
                        st.dataframe(vp_sigs.sort_values("date", ascending=False),
                                     use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
