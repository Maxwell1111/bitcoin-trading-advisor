"""
Bitcoin Trading Advisor FastAPI Application
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, Dict, Any
import sys
from pathlib import Path
import os
import pandas as pd

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.data.price_fetcher import PriceFetcher
from src.data.news_fetcher import NewsFetcher, MockNewsFetcher, MultiSourceFetcher
from src.analysis.technical import TechnicalAnalyzer
from src.analysis.sentiment import SentimentAnalyzer
from src.engine.recommendation import RecommendationEngine
from src.utils.config import get_config
from src.utils.cache import get_cache

# Initialize FastAPI app
app = FastAPI(
    title="Bitcoin Portfolio Advisor API",
    description="Get Bitcoin trading recommendations based on sentiment analysis and technical indicators",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for API
class HealthResponse(BaseModel):
    status: str
    message: str


class RecommendationRequest(BaseModel):
    days: int = 100
    news_days: int = 7
    max_articles: int = 50
    use_mock: bool = False


class RecommendationResponse(BaseModel):
    recommendation: str
    confidence: float
    current_price: float
    signals: Dict[str, Any]
    targets: Dict[str, Any]
    reasoning: str
    timestamp: str


@app.get("/")
async def root():
    """Serve the web interface"""
    static_dir = Path(__file__).parent.parent.parent / "static"
    index_file = static_dir / "index.html"

    if index_file.exists():
        return FileResponse(index_file)
    else:
        # Fallback to API info if static files don't exist
        return {
            "message": "Bitcoin Portfolio Advisor API",
            "version": "1.0.0",
            "endpoints": {
                "health": "/health",
                "docs": "/docs",
                "dashboard": "/dashboard",
                "recommendation": "/api/recommendation",
                "price": "/api/price",
                "chart_data": "/api/chart-data"
            }
        }


@app.get("/dashboard")
async def dashboard():
    """Serve the advanced dashboard with charts"""
    static_dir = Path(__file__).parent.parent.parent / "static"
    dashboard_file = static_dir / "dashboard.html"

    if dashboard_file.exists():
        return FileResponse(dashboard_file)
    else:
        return JSONResponse(
            status_code=404,
            content={"error": "Dashboard not found"}
        )


@app.get("/health")
async def health() -> PlainTextResponse:
    """Health check endpoint"""
    return PlainTextResponse(content="OK", status_code=200)


@app.get("/api/health")
async def api_health() -> HealthResponse:
    """API health check"""
    return HealthResponse(status="healthy", message="Bitcoin Trading Advisor API is running")


@app.get("/api/price")
async def get_current_price():
    """Get current Bitcoin price with caching and fallback"""
    cache = get_cache()

    # Check cache first (60 second TTL)
    cached_price = cache.get("btc_price")
    if cached_price is not None:
        return {
            "price": cached_price,
            "currency": "USD",
            "symbol": "BTC",
            "cached": True
        }

    # Try multiple providers in order
    providers = ["yfinance", "coingecko", "binance"]
    last_error = None

    for provider in providers:
        try:
            fetcher = PriceFetcher(provider=provider)
            price = fetcher.get_current_price()

            # Cache for 60 seconds
            cache.set("btc_price", price, ttl=60)

            return {
                "price": price,
                "currency": "USD",
                "symbol": "BTC",
                "provider": provider,
                "cached": False
            }
        except Exception as e:
            last_error = str(e)
            continue

    # All providers failed
    return JSONResponse(
        status_code=503,
        content={
            "error": "Unable to fetch Bitcoin price from any provider",
            "last_error": last_error,
            "tried_providers": providers
        }
    )


@app.post("/api/recommendation")
async def get_recommendation(request: RecommendationRequest) -> RecommendationResponse:
    """
    Get trading recommendation based on technical and sentiment analysis

    Parameters:
    - days: Number of days of historical price data (default: 100)
    - news_days: Number of days of news to analyze (default: 7)
    - max_articles: Maximum number of news articles (default: 50)
    - use_mock: Use mock data for testing (default: false)
    """
    try:
        # Fetch price data - use yfinance to avoid CoinGecko rate limits
        price_fetcher = PriceFetcher(provider="yfinance")
        current_price = price_fetcher.get_current_price()
        historical_data = price_fetcher.fetch_historical_data(days=request.days)

        # Fetch sentiment from multiple sources
        news_articles = []

        if request.use_mock:
            try:
                news_fetcher = MockNewsFetcher()
                news_articles = news_fetcher.fetch_news(
                    keywords=['bitcoin', 'btc', 'cryptocurrency'],
                    days=request.news_days,
                    max_articles=request.max_articles
                )
            except Exception as e:
                print(f"Mock fetcher error: {e}")
                # Create minimal mock data as fallback
                news_articles = [{
                    'title': 'Bitcoin Market Update',
                    'description': 'Bitcoin trading continues.',
                    'content': 'Bitcoin trading continues with mixed signals.',
                    'source': 'Mock',
                    'source_type': 'news'
                }]
        else:
            # Use multi-source fetcher (NewsAPI + Reddit + Twitter)
            try:
                config = get_config()
                newsapi_key = config.get_api_key('newsapi')
            except:
                newsapi_key = None
                print("No NewsAPI key found")

            # Get Twitter token if available (optional)
            try:
                twitter_token = config.get_api_key('twitter_bearer_token')
            except:
                twitter_token = None

            try:
                multi_fetcher = MultiSourceFetcher(
                    newsapi_key=newsapi_key,
                    twitter_bearer_token=twitter_token
                )

                # Fetch from all sources (NewsAPI + Reddit + Twitter if enabled)
                news_articles = multi_fetcher.get_combined_items(
                    max_per_source=request.max_articles // 2  # Split quota between sources
                )

                print(f"Fetched {len(news_articles)} items from multi-source")

            except Exception as e:
                print(f"Multi-source fetcher error: {e}")
                # Fallback to mock data if all sources fail
                news_articles = [{
                    'title': 'Bitcoin Market Analysis',
                    'description': 'Bitcoin shows neutral sentiment.',
                    'content': 'Bitcoin market sentiment appears neutral.',
                    'source': 'Fallback',
                    'source_type': 'news'
                }]

        # Ensure we have at least some data
        if not news_articles or len(news_articles) == 0:
            news_articles = [{
                'title': 'Bitcoin Update',
                'description': 'Bitcoin market analysis.',
                'content': 'Bitcoin market shows mixed signals.',
                'source': 'Default',
                'source_type': 'news'
            }]

        # Technical analysis
        tech_analyzer = TechnicalAnalyzer()
        technical_results = tech_analyzer.analyze(historical_data)

        # Sentiment analysis - separate Reddit from News
        try:
            sentiment_analyzer = SentimentAnalyzer(analyzer_type='vader')

            # Split articles by source type
            news_items = [a for a in news_articles if a.get('source_type') == 'news']
            reddit_items = [a for a in news_articles if a.get('source_type') == 'reddit']

            # Analyze separately
            if news_items:
                news_sentiment = sentiment_analyzer.analyze_articles(news_items)
            else:
                news_sentiment = {
                    'overall_sentiment': 'neutral',
                    'recommendation': 'hold',
                    'confidence': 0.5,
                    'average_compound': 0.0,
                    'article_count': 0,
                    'positive_count': 0,
                    'negative_count': 0,
                    'neutral_count': 0
                }

            if reddit_items:
                reddit_sentiment = sentiment_analyzer.analyze_articles(reddit_items)
            else:
                reddit_sentiment = {
                    'overall_sentiment': 'neutral',
                    'recommendation': 'hold',
                    'confidence': 0.5,
                    'average_compound': 0.0,
                    'article_count': 0,
                    'positive_count': 0,
                    'negative_count': 0,
                    'neutral_count': 0
                }

            # Track source counts
            source_counts = {
                'news': len(news_items),
                'reddit': len(reddit_items)
            }

            print(f"Sentiment analysis: {len(news_items)} news, {len(reddit_items)} reddit")

        except Exception as e:
            print(f"Sentiment analysis error: {e}")
            # Create default sentiment results
            news_sentiment = {
                'overall_sentiment': 'neutral',
                'recommendation': 'hold',
                'confidence': 0.5,
                'average_compound': 0.0,
                'article_count': 0,
                'positive_count': 0,
                'negative_count': 0,
                'neutral_count': 0
            }
            reddit_sentiment = news_sentiment.copy()
            source_counts = {'news': 0, 'reddit': 0}

        # Generate recommendation with contrarian engine
        engine = RecommendationEngine(
            reddit_weight=0.25,
            news_weight=0.15,
            technical_weight=0.6
        )
        recommendation = engine.generate_recommendation(
            technical_analysis=technical_results,
            news_sentiment_analysis=news_sentiment,
            reddit_sentiment_analysis=reddit_sentiment,
            historical_data=historical_data,
            current_price=current_price
        )

        # Add sentiment sources to recommendation response
        if 'signals' in recommendation and 'sentiment' in recommendation['signals']:
            recommendation['signals']['sentiment']['sources'] = source_counts

        return RecommendationResponse(**recommendation)

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"ERROR in /api/recommendation: {str(e)}")
        print(f"Traceback: {error_trace}")

        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "details": "Check server logs for full traceback",
                "endpoint": "/api/recommendation"
            }
        )


@app.get("/api/technical")
async def get_technical_analysis(days: int = 100):
    """Get only technical analysis"""
    try:
        price_fetcher = PriceFetcher(provider="yfinance")
        current_price = price_fetcher.get_current_price()
        historical_data = price_fetcher.fetch_historical_data(days=days)

        tech_analyzer = TechnicalAnalyzer()
        results = tech_analyzer.analyze(historical_data)

        return {
            "current_price": current_price,
            "technical_analysis": results
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get("/api/sentiment")
async def get_sentiment_analysis(days: int = 7, max_articles: int = 50, use_mock: bool = False):
    """Get sentiment analysis from multiple sources (NewsAPI + Reddit + Twitter)"""
    try:
        if use_mock:
            news_fetcher = MockNewsFetcher()
            news_articles = news_fetcher.fetch_news(
                keywords=['bitcoin', 'btc', 'cryptocurrency'],
                days=days,
                max_articles=max_articles
            )
        else:
            # Get API keys
            try:
                config = get_config()
                newsapi_key = config.get_api_key('newsapi')
            except:
                newsapi_key = None

            try:
                twitter_token = config.get_api_key('twitter_bearer_token')
            except:
                twitter_token = None

            # Use multi-source fetcher
            multi_fetcher = MultiSourceFetcher(
                newsapi_key=newsapi_key,
                twitter_bearer_token=twitter_token
            )

            news_articles = multi_fetcher.get_combined_items(max_per_source=max_articles // 2)

        sentiment_analyzer = SentimentAnalyzer(analyzer_type='vader')
        results = sentiment_analyzer.analyze_articles(news_articles)

        # Add source breakdown
        source_counts = {}
        for article in news_articles:
            source_type = article.get('source_type', 'unknown')
            source_counts[source_type] = source_counts.get(source_type, 0) + 1

        results['sources_used'] = source_counts
        results['total_items'] = len(news_articles)

        return results

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get("/api/chart-data")
async def get_chart_data(days: int = 180):
    """
    Get historical price data with moving averages for charting

    Parameters:
    - days: Number of days of historical data (default: 180)

    Returns:
    - dates: List of dates in ISO format
    - price: Bitcoin closing prices
    - ema_20: 20-day Exponential Moving Average
    - sma_50: 50-day Simple Moving Average
    - sma_200: 200-day Simple Moving Average
    - ema_21week: 21-week EMA (Bull Market Support Band)
    """
    try:
        # Fetch more data than requested to ensure we have enough for 200 SMA calculation
        fetch_days = max(days + 200, 400)

        price_fetcher = PriceFetcher(provider="yfinance")
        historical_data = price_fetcher.fetch_historical_data(days=fetch_days)

        # Calculate moving averages
        tech_analyzer = TechnicalAnalyzer()

        # Calculate EMAs
        ema_20 = tech_analyzer.calculate_ema(historical_data, 20)
        ema_21week = tech_analyzer.calculate_ema(historical_data, 147)  # 21 weeks * 7 days

        # Calculate SMAs
        sma_50 = tech_analyzer.calculate_sma(historical_data, 50)
        sma_200 = tech_analyzer.calculate_sma(historical_data, 200)

        # Get the most recent 'days' worth of data
        historical_data = historical_data.tail(days)
        ema_20 = ema_20.tail(days)
        ema_21week = ema_21week.tail(days)
        sma_50 = sma_50.tail(days)
        sma_200 = sma_200.tail(days)

        # Prepare response data
        dates = historical_data.index.strftime('%Y-%m-%d').tolist()

        # Convert to list and replace NaN with None for JSON serialization
        def series_to_list(series):
            """Convert pandas Series to list, replacing NaN with None"""
            return [None if pd.isna(x) else round(float(x), 2) for x in series]

        return {
            "dates": dates,
            "price": [round(float(x), 2) for x in historical_data['close']],
            "ema_20": series_to_list(ema_20),
            "sma_50": series_to_list(sma_50),
            "sma_200": series_to_list(sma_200),
            "ema_21week": series_to_list(ema_21week)
        }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
