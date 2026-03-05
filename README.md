# 📊 Volume Profile Breakout Strategy

Streamlit app that detects **balanced markets** and **breakout signals** using Volume Profile analysis with VAH/VAL/POC levels.

## Features

- **Volume Profile** with configurable price bins and 70% Value Area
- **VAH** (Value Area High) — upper breakout resistance line
- **VAL** (Value Area Low) — lower breakout support line
- **POC** (Point of Control) — highest volume price level
- **Balance Detection** — identifies when market trades within Value Area
- **Breakout Signals** — alerts when price crosses VAH or VAL
- **Multiple Periods** — Previous Day / Previous Week / Current Week profiles
- Interactive Plotly charts with dark theme

## Data Source

Uses [Financial Modeling Prep (FMP) API](https://financialmodelingprep.com/developer) for intraday and daily price data.

Get a free API key at: https://financialmodelingprep.com/developer/docs

## Quick Start

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/volume-profile-breakout.git
cd volume-profile-breakout

# Install
pip install -r requirements.txt

# Run
streamlit run app.py
```

## Deploy to Streamlit Cloud

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Set main file path: `app.py`
5. (Optional) Add `FMP_API_KEY` in Streamlit Cloud Secrets

## How It Works

### Volume Profile
Distributes volume across price levels using a weighted gaussian method. The **Value Area** captures 70% of total volume centered around the POC.

### Balance Detection
A market is **balanced** when ≥70% of recent price bars close within the Value Area (VAH-VAL range). Balanced markets indicate consolidation and potential for a breakout.

### Breakout Strategy
- **Breakout UP**: Price closes above VAH after being inside the Value Area → Bullish signal
- **Breakout DOWN**: Price closes below VAL after being inside the Value Area → Bearish signal

### Profile Periods
| Period | Profile Built From | Trading On |
|--------|-------------------|------------|
| Previous Day | Yesterday's intraday data | Today |
| Previous Week | Last week's intraday data | This week |
| Current Week | This week so far (rolling) | This week |

## Project Structure

```
volume-profile-breakout/
├── app.py                  # Main Streamlit application
├── requirements.txt        # Python dependencies
├── .streamlit/
│   └── config.toml         # Streamlit theme config
├── .gitignore
└── README.md
```

## Screenshots

The app displays:
- Candlestick chart with VAH/VAL/POC overlay
- Horizontal Volume Profile histogram
- Value Area shading
- Breakout signal markers (▲ UP / ▼ DOWN)
- Balance status indicator

## Disclaimer

This tool is for **educational and research purposes only**. It is not financial advice. Always do your own analysis before making trading decisions.
