# 📊 Multi-Strategy Trading Dashboard

Streamlit app with **6 trading strategies**, using dual data sources for reliability.

## Data Sources

| Data Type | Source | Cost | Used By |
|-----------|--------|------|---------|
| **Daily OHLCV** | FMP Stable API | Free tier OK | Gap Fill, Oops |
| **Intraday OHLCV** | yfinance | Free (no key) | ORB, PBD, Rule of 4, VP Zones |

> FMP free tier returns 402 for intraday — so all intraday strategies use yfinance instead.
> If FMP key is not set, daily data also falls back to yfinance automatically.

## Strategies

1. **📉 Gap Fill** — Trade gap reversals (daily data)
2. **⏰ ORB** — Opening Range Breakout from first 15min (intraday)
3. **😲 Oops** — Gap reversal when gap opposes prior day (daily)
4. **📐 PBD** — Consolidation breakout/breakdown (intraday)
5. **4️⃣ Rule of 4** — Post-event N-bar range breakout (intraday)
6. **📊 VP Zones** — Volume Profile with VAH→LVN / VAL→LVN boxes (intraday)

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy to Streamlit Cloud

1. Push to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Set main file: `app.py`
4. Optional: Add `FMP_API_KEY` in Streamlit Secrets (daily data improves with it)

```toml
# .streamlit/secrets.toml
FMP_API_KEY = "your_key_here"
```

## yfinance Interval Limits

| Interval | Max History |
|----------|-------------|
| 1min | 7 days |
| 5min | 60 days |
| 15min | 60 days |
| 30min | 60 days |
| 1hour | 730 days |

## Disclaimer

For **educational and research purposes only**. Not financial advice.
