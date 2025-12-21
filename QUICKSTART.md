# Quick Start Guide

## 🚀 Get Started in 5 Minutes

### 1. Install Dependencies

```bash
cd bitcoin-trading-advisor

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

**Note**: If `TA-Lib` installation fails, you can skip it for now. The bot will work with `pandas-ta` as a fallback.

### 2. Test with Mock Data (No API Keys Needed)

```bash
python main.py --mock
```

This will run the bot with sample news data and live Bitcoin price data from CoinGecko.

### 3. Set Up API Keys (Optional, for Real News)

1. Get a free API key from [NewsAPI.org](https://newsapi.org/register)
2. Copy the example config:
   ```bash
   cp config.example.yaml config.yaml
   ```
3. Edit `config.yaml` and add your NewsAPI key:
   ```yaml
   api_keys:
     newsapi: "YOUR_ACTUAL_API_KEY_HERE"
   ```

### 4. Run with Real Data

```bash
python main.py
```

## 📊 Command Line Options

```bash
# Use mock data (testing)
python main.py --mock

# Analyze more historical data
python main.py --days 200

# Analyze more news articles
python main.py --articles 100

# Look at news from last 14 days
python main.py --news-days 14

# Combine options
python main.py --days 200 --articles 100 --news-days 14
```

## 🔧 Troubleshooting

### TA-Lib Installation Issues

TA-Lib can be tricky to install. If you get errors:

**macOS:**
```bash
brew install ta-lib
pip install TA-Lib
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install ta-lib
pip install TA-Lib
```

**Windows:**
Download pre-built wheel from [here](https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib)

**Alternative:** Remove `TA-Lib` from `requirements.txt` and use `pandas-ta` only

### NewsAPI Rate Limits

Free tier: 100 requests/day, so use `--articles 50` or less

### Connection Errors

If you get connection errors, check your internet connection and try again.

## 📈 Example Output

```
══════════════════════════════════════════════════════════════
           BITCOIN PORTFOLIO ADVISOR RECOMMENDATION
══════════════════════════════════════════════════════════════

Date/Time: 2025-12-20T10:30:00
Current BTC Price: $65,432.50

══════════════════════════════════════════════════════════════

RECOMMENDATION: BUY
Confidence Level: 72%

══════════════════════════════════════════════════════════════

ANALYSIS BREAKDOWN:

Technical Analysis (60% weight):
  → Recommendation: BUY
  → Confidence: 65%
  → RSI: 58.2 (neutral)
  → MACD: bullish

Sentiment Analysis (40% weight):
  → Recommendation: BUY
  → Confidence: 72%
  → Overall Sentiment: POSITIVE
  → News Articles Analyzed: 50
  → Sentiment Score: 0.245
```

## 🎯 Next Steps

1. **Customize Settings**: Edit `config.yaml` to adjust weights and thresholds
2. **Backtest**: Use historical data to see how recommendations would have performed
3. **Automate**: Set up a cron job to run daily and email you results
4. **Visualize**: Check out the `notebooks/` folder for Jupyter notebook examples
5. **Contribute**: Fork the repo and add features!

## ❓ Need Help?

- Check the main README.md for detailed documentation
- Look at example code in each module's `if __name__ == "__main__"` section
- Open an issue on GitHub

Happy trading! 📈🚀
