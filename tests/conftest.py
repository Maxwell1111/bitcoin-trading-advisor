"""
Shared pytest fixtures for all tests
"""

from datetime import datetime

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def sample_price_data() -> pd.DataFrame:
    """
    Generate sample Bitcoin price data for testing

    Returns 100 days of realistic-looking OHLCV data
    """
    dates = pd.date_range(end=datetime.now(), periods=100, freq="D")
    np.random.seed(42)

    # Simulate realistic price movements
    base_price = 50000
    returns = np.random.randn(len(dates)) * 0.02  # 2% daily volatility
    prices = base_price * (1 + returns).cumprod()

    df = pd.DataFrame(
        {
            "close": prices,
            "open": prices * (1 + np.random.randn(len(dates)) * 0.005),
            "high": prices * (1 + np.abs(np.random.randn(len(dates))) * 0.01),
            "low": prices * (1 - np.abs(np.random.randn(len(dates))) * 0.01),
            "volume": np.random.randint(1000000, 10000000, len(dates)),
        },
        index=dates,
    )

    return df


@pytest.fixture
def long_price_data() -> pd.DataFrame:
    """
    Generate long-term price data (300+ days) for testing MA crossovers
    """
    dates = pd.date_range(end=datetime.now(), periods=300, freq="D")
    np.random.seed(42)

    base_price = 40000
    # Add trend component
    trend = np.linspace(0, 0.5, len(dates))
    returns = np.random.randn(len(dates)) * 0.015
    prices = base_price * (1 + trend + returns).cumprod()

    df = pd.DataFrame(
        {
            "close": prices,
            "open": prices * (1 + np.random.randn(len(dates)) * 0.005),
            "high": prices * (1 + np.abs(np.random.randn(len(dates))) * 0.01),
            "low": prices * (1 - np.abs(np.random.randn(len(dates))) * 0.01),
            "volume": np.random.randint(1000000, 10000000, len(dates)),
        },
        index=dates,
    )

    return df


@pytest.fixture
def bullish_price_data() -> pd.DataFrame:
    """Generate uptrending price data"""
    dates = pd.date_range(end=datetime.now(), periods=50, freq="D")
    prices = np.linspace(40000, 60000, len(dates))  # Clear uptrend

    df = pd.DataFrame(
        {
            "close": prices,
            "open": prices * 0.99,
            "high": prices * 1.01,
            "low": prices * 0.98,
            "volume": np.random.randint(1000000, 10000000, len(dates)),
        },
        index=dates,
    )

    return df


@pytest.fixture
def bearish_price_data() -> pd.DataFrame:
    """Generate downtrending price data"""
    dates = pd.date_range(end=datetime.now(), periods=50, freq="D")
    prices = np.linspace(60000, 40000, len(dates))  # Clear downtrend

    df = pd.DataFrame(
        {
            "close": prices,
            "open": prices * 1.01,
            "high": prices * 1.02,
            "low": prices * 0.99,
            "volume": np.random.randint(1000000, 10000000, len(dates)),
        },
        index=dates,
    )

    return df


@pytest.fixture
def sample_news_articles() -> list[dict]:
    """Generate sample news articles for sentiment testing"""
    return [
        {
            "title": "Bitcoin Soars to New All-Time High",
            "description": "Bitcoin price surges past $70,000 as institutional demand grows.",
            "content": "Bitcoin has reached unprecedented levels...",
            "source": "Crypto News",
            "source_type": "news",
            "url": "https://example.com/1",
            "published_date": "2024-01-10",
        },
        {
            "title": "Regulatory Concerns Shake Crypto Market",
            "description": "New regulations cause uncertainty among Bitcoin investors.",
            "content": "Regulators have announced stricter guidelines...",
            "source": "Financial Times",
            "source_type": "news",
            "url": "https://example.com/2",
            "published_date": "2024-01-09",
        },
        {
            "title": "Bitcoin Adoption Increases Globally",
            "description": "More countries embrace Bitcoin as legal tender.",
            "content": "Adoption rates continue to climb...",
            "source": "Global Finance",
            "source_type": "news",
            "url": "https://example.com/3",
            "published_date": "2024-01-08",
        },
    ]


@pytest.fixture
def positive_articles() -> list[dict]:
    """Generate strongly positive news articles"""
    return [
        {
            "title": "Bitcoin Surges! Amazing Rally!",
            "description": "Incredible bullish momentum drives Bitcoin higher!",
            "source": "Crypto Enthusiast",
            "source_type": "news",
        },
        {
            "title": "Bitcoin Moon Shot! Institutional Buying Frenzy!",
            "description": "Massive institutional investment propels Bitcoin to stratospheric levels!",
            "source": "Bull Market Daily",
            "source_type": "news",
        },
        {
            "title": "Bitcoin Breaks All Records! Historic Gains!",
            "description": "Unprecedented growth as Bitcoin crushes all previous highs!",
            "source": "Crypto Winner",
            "source_type": "news",
        },
    ]


@pytest.fixture
def negative_articles() -> list[dict]:
    """Generate strongly negative news articles"""
    return [
        {
            "title": "Bitcoin Crashes! Market Panic!",
            "description": "Severe decline triggers widespread selling and fear.",
            "source": "Bear News",
            "source_type": "news",
        },
        {
            "title": "Bitcoin Collapse! Investors Flee!",
            "description": "Catastrophic losses as Bitcoin plummets amid crisis.",
            "source": "Doom Report",
            "source_type": "news",
        },
        {
            "title": "Bitcoin Disaster! Worst Performance Ever!",
            "description": "Terrible market conditions destroy Bitcoin value.",
            "source": "Crisis Watch",
            "source_type": "news",
        },
    ]


@pytest.fixture
def neutral_articles() -> list[dict]:
    """Generate neutral news articles"""
    return [
        {
            "title": "Bitcoin Price Analysis",
            "description": "Technical analysis shows mixed signals for Bitcoin.",
            "source": "Neutral Observer",
            "source_type": "news",
        },
        {
            "title": "Bitcoin Market Update",
            "description": "Bitcoin trading continues with moderate activity.",
            "source": "Market Watch",
            "source_type": "news",
        },
    ]


@pytest.fixture
def sample_reddit_posts() -> list[dict]:
    """Generate sample Reddit posts"""
    return [
        {
            "title": "HODL! Bitcoin to the moon! 🚀",
            "description": "This is our time guys! Bitcoin will change everything!",
            "source": "r/Bitcoin",
            "source_type": "reddit",
        },
        {
            "title": "Should I sell my Bitcoin?",
            "description": "Worried about the recent dip. What do you think?",
            "source": "r/cryptocurrency",
            "source_type": "reddit",
        },
    ]


@pytest.fixture
def mock_technical_analysis() -> dict:
    """Mock technical analysis results"""
    return {
        "rsi": {"value": 55.0, "signal": "neutral", "recommendation": "hold"},
        "macd": {
            "macd_line": 100.0,
            "signal_line": 95.0,
            "histogram": 5.0,
            "signal": "bullish",
            "recommendation": "buy",
        },
        "moving_averages": {
            "sma_50": {"value": 48000, "price_vs_ma": "above"},
            "sma_200": {"value": 45000, "price_vs_ma": "above"},
        },
        "ma_crossovers": {"golden_cross": False, "death_cross": False},
        "ma_trend": {
            "overall_trend": "uptrend",
            "recommendation": "buy",
            "bullish_signals": 4,
            "bearish_signals": 1,
            "bullish_ratio": 0.8,
        },
        "overall": {
            "recommendation": "buy",
            "confidence": 0.65,
            "buy_signals": 3,
            "sell_signals": 0,
            "total_indicators": 5,
        },
    }


@pytest.fixture
def mock_sentiment_analysis() -> dict:
    """Mock sentiment analysis results"""
    return {
        "overall_sentiment": "positive",
        "recommendation": "buy",
        "confidence": 0.72,
        "average_compound": 0.245,
        "median_compound": 0.250,
        "article_count": 25,
        "positive_count": 18,
        "negative_count": 4,
        "neutral_count": 3,
        "positive_ratio": 0.72,
        "negative_ratio": 0.16,
        "neutral_ratio": 0.12,
    }


@pytest.fixture
def current_price() -> float:
    """Standard test price"""
    return 50000.0


@pytest.fixture
def historical_data_dict(sample_price_data) -> dict:
    """Convert price DataFrame to dict format expected by some functions"""
    return {
        "Close": sample_price_data["close"].tolist(),
        "Open": sample_price_data["open"].tolist(),
        "High": sample_price_data["high"].tolist(),
        "Low": sample_price_data["low"].tolist(),
        "Volume": sample_price_data["volume"].tolist(),
    }
