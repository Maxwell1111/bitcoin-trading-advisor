# Bitcoin Portfolio Advisor Bot

An intelligent Bitcoin trading recommendation bot that combines **sentiment analysis** from crypto news and **technical analysis** (RSI & MACD) to provide portfolio investment recommendations.

## Features

- **News Sentiment Analysis**: Analyzes cryptocurrency news articles to gauge market sentiment
- **Technical Indicators**: Uses RSI and MACD to identify market trends and momentum
- **Smart Recommendations**: Combines sentiment and technical signals for BUY/HOLD/SELL recommendations
- **Portfolio Advisor**: Designed for long-term investment decisions
- **Visualization**: Charts and graphs for easy understanding

## Architecture

```
bitcoin-trading-advisor/
├── src/
│   ├── data/
│   │   ├── price_fetcher.py      # Fetch Bitcoin price data
│   │   └── news_fetcher.py       # Fetch crypto news articles
│   ├── analysis/
│   │   ├── sentiment.py          # News sentiment analysis
│   │   ├── technical.py          # RSI & MACD calculations
│   │   └── indicators.py         # Technical indicator utilities
│   ├── engine/
│   │   └── recommendation.py     # Combine signals and generate recommendations
│   └── utils/
│       ├── config.py             # Configuration management
│       └── visualization.py      # Charts and plotting
├── data/                         # Data storage
├── notebooks/                    # Jupyter notebooks for analysis
├── tests/                        # Unit tests
├── requirements.txt              # Python dependencies
├── config.yaml                   # Configuration file
└── main.py                       # Main entry point
```

## Tech Stack

- **Python 3.9+**
- **Pandas** & **NumPy**: Data manipulation
- **TA-Lib** or **Pandas-TA**: Technical indicators (RSI, MACD)
- **VADER** or **TextBlob**: Sentiment analysis
- **CoinGecko API** / **Binance API**: Price data
- **NewsAPI** or **CryptoPanic API**: News articles
- **Matplotlib** / **Plotly**: Visualization

## Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/bitcoin-trading-advisor.git
cd bitcoin-trading-advisor

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

1. Copy `config.example.yaml` to `config.yaml`
2. Add your API keys:
   - NewsAPI key
   - Exchange API keys (if needed)

## Usage

```bash
# Run the advisor
python main.py

# Or use Jupyter notebooks for interactive analysis
jupyter notebook notebooks/analysis.ipynb
```

## How It Works

### 1. Data Collection
- Fetches Bitcoin price data from CoinGecko/Binance
- Retrieves recent crypto news articles

### 2. Sentiment Analysis
- Analyzes news headlines and content
- Calculates sentiment scores (positive/negative/neutral)
- Aggregates overall market sentiment

### 3. Technical Analysis
- Calculates RSI (Relative Strength Index)
- Computes MACD (Moving Average Convergence Divergence)
- Identifies overbought/oversold conditions

### 4. Recommendation Engine
- Combines sentiment and technical signals
- Generates weighted recommendation score
- Provides BUY/HOLD/SELL advice with confidence level

## Example Output

```
=== Bitcoin Portfolio Advisor ===
Date: 2025-12-20
Current Price: $65,432

Sentiment Analysis:
  News Sentiment: Positive (0.72)
  Source Count: 50 articles

Technical Analysis:
  RSI (14): 58.2 (Neutral)
  MACD: Bullish crossover

RECOMMENDATION: BUY
Confidence: 75%
Reasoning: Positive news sentiment combined with bullish MACD signal
```

## Key Libraries

| Library | Purpose |
|---------|---------|
| `pandas-ta` | Technical indicators (RSI, MACD) |
| `vaderSentiment` | News sentiment analysis |
| `requests` | API calls |
| `yfinance` | Historical price data |
| `matplotlib` | Visualization |

## Roadmap

- [ ] Basic sentiment analysis from news
- [ ] RSI and MACD implementation
- [ ] Recommendation engine
- [ ] Backtesting framework
- [ ] Web dashboard
- [ ] Real-time alerts
- [ ] Multi-crypto support

## Contributing

Contributions welcome! Please read CONTRIBUTING.md first.

## Disclaimer

**This bot is for educational and research purposes only. It does not constitute financial advice. Cryptocurrency trading involves significant risk. Always do your own research and never invest more than you can afford to lose.**

## License

MIT License - see LICENSE file

## Resources

- [Bitcoin Trading Bot Examples](https://github.com/Roibal/Cryptocurrency-Trading-Bots-Python-Beginner-Advance)
- [TA-Lib Documentation](https://mrjbq7.github.io/ta-lib/)
- [VADER Sentiment Analysis](https://github.com/cjhutto/vaderSentiment)
- [CoinGecko API](https://www.coingecko.com/en/api)

---
Made with ❤️ for the crypto community
