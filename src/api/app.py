"""
Bitcoin Trading Advisor FastAPI Application
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import contextlib

from src.analysis.rebalance_analyzer import RebalanceAnalyzer
from src.analysis.sentiment import SentimentAnalyzer
from src.analysis.technical import TechnicalAnalyzer
from src.data.gold_fetcher import GoldFetcher
from src.data.news_fetcher import MockNewsFetcher, MultiSourceFetcher
from src.data.price_fetcher import PriceFetcher

# Adaptive system imports
from src.database import init_database
from src.engine.recommendation import RecommendationEngine
from src.services import (
    HistoryTracker,
    PriceMonitor,
    ValidationJob,
    ValidationService,
    WeightOptimizer,
    get_weight_manager,
)
from src.utils.cache import get_cache
from src.utils.config import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Bitcoin Portfolio Advisor API",
    description="Get Bitcoin trading recommendations based on sentiment analysis and technical indicators",
    version="2.0.0",  # Bumped version for adaptive system
)

# Global service instances
weight_manager = get_weight_manager()
history_tracker = HistoryTracker()
validation_service = ValidationService()

# Background service instances (will be started in startup event)
price_monitor = None
validation_job = None
weight_optimizer = None

# Background task references
background_tasks = {}

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize database and start background services"""
    global price_monitor, validation_job, weight_optimizer

    logger.info("=" * 60)
    logger.info("BITCOIN ADVISOR API STARTING UP")
    logger.info("=" * 60)

    # 1. Initialize database
    logger.info("Initializing database...")
    init_success = init_database()
    if init_success:
        logger.info("✓ Database initialized successfully")
    else:
        logger.error("✗ Database initialization failed!")

    # 2. Start WeightManager periodic refresh
    logger.info("Starting WeightManager...")
    weight_manager.start_refresh_task()
    logger.info("✓ WeightManager started")

    # 3. Start PriceMonitor
    logger.info("Starting PriceMonitor...")
    price_monitor = PriceMonitor(volatility_threshold=0.03, poll_interval=30)
    background_tasks["price_monitor"] = asyncio.create_task(price_monitor.run())
    logger.info("✓ PriceMonitor started")

    # 4. Start ValidationJob
    logger.info("Starting ValidationJob...")

    async def get_current_price_async():
        """Wrapper to get current price for validation job"""
        if price_monitor:
            price = price_monitor.get_current_price()
            if price:
                return price
        # Fallback to fetching directly
        fetcher = PriceFetcher(provider="yfinance")
        return fetcher.get_current_price()

    validation_job = ValidationJob(
        validation_service=validation_service,
        price_fetcher=get_current_price_async,
        interval_seconds=300,  # 5 minutes
        batch_size=100,
    )
    background_tasks["validation_job"] = asyncio.create_task(validation_job.run())
    logger.info("✓ ValidationJob started")

    # 5. Start WeightOptimizer
    logger.info("Starting WeightOptimizer...")
    weight_optimizer = WeightOptimizer(
        validation_service=validation_service,
        rolling_window_days=30,
        cold_start_days=30,
        smoothing_factor=0.3,
    )
    background_tasks["weight_optimizer"] = asyncio.create_task(weight_optimizer.run())
    logger.info("✓ WeightOptimizer started")

    logger.info("=" * 60)
    logger.info("ALL SERVICES STARTED SUCCESSFULLY")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Gracefully shutdown background services"""
    logger.info("Shutting down background services...")

    # Stop WeightManager refresh
    weight_manager.stop_refresh_task()

    # Cancel all background tasks
    for name, task in background_tasks.items():
        if not task.done():
            logger.info(f"Cancelling {name}...")
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    logger.info("✓ All services stopped")


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
    signals: dict[str, Any]
    targets: dict[str, Any]
    reasoning: str
    timestamp: str


@app.get("/")
async def root():
    """Serve the web interface"""
    static_dir = Path(__file__).parent.parent.parent / "static"
    index_file = static_dir / "index.html"

    if index_file.exists():
        return FileResponse(index_file)
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
            "chart_data": "/api/chart-data",
        },
    }


@app.get("/dashboard")
async def dashboard():
    """Serve the advanced dashboard with charts"""
    static_dir = Path(__file__).parent.parent.parent / "static"
    dashboard_file = static_dir / "dashboard.html"

    if dashboard_file.exists():
        return FileResponse(dashboard_file)
    return JSONResponse(status_code=404, content={"error": "Dashboard not found"})


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
        return {"price": cached_price, "currency": "USD", "symbol": "BTC", "cached": True}

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
                "cached": False,
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
            "tried_providers": providers,
        },
    )


@app.post("/api/recommendation")
async def get_recommendation(
    request: RecommendationRequest,
    include: Optional[str] = Query(
        None, description="Include additional data: 'stats', 'history', or 'full'"
    ),
) -> RecommendationResponse:
    """
    Get trading recommendation based on technical and sentiment analysis

    NOW WITH ADAPTIVE WEIGHTS! The system automatically adjusts technical vs sentiment
    weighting based on historical accuracy.

    Parameters:
    - days: Number of days of historical price data (default: 100)
    - news_days: Number of days of news to analyze (default: 7)
    - max_articles: Maximum number of news articles (default: 50)
    - use_mock: Use mock data for testing (default: false)
    - include: Optional metadata - 'stats' for accuracy metrics, 'full' for everything
    """
    try:
        # Load adaptive weights
        adaptive_weights = weight_manager.get_current_weights()
        logger.info(f"Using adaptive weights: {adaptive_weights}")

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
                    keywords=["bitcoin", "btc", "cryptocurrency"],
                    days=request.news_days,
                    max_articles=request.max_articles,
                )
            except Exception as e:
                print(f"Mock fetcher error: {e}")
                # Create minimal mock data as fallback
                news_articles = [
                    {
                        "title": "Bitcoin Market Update",
                        "description": "Bitcoin trading continues.",
                        "content": "Bitcoin trading continues with mixed signals.",
                        "source": "Mock",
                        "source_type": "news",
                    }
                ]
        else:
            # Use multi-source fetcher (NewsAPI + Reddit + Twitter)
            try:
                config = get_config()
                newsapi_key = config.get_api_key("newsapi")
            except:
                newsapi_key = None
                print("No NewsAPI key found")

            # Get Twitter token if available (optional)
            try:
                twitter_token = config.get_api_key("twitter_bearer_token")
            except:
                twitter_token = None

            try:
                multi_fetcher = MultiSourceFetcher(
                    newsapi_key=newsapi_key, twitter_bearer_token=twitter_token
                )

                # Fetch from all sources (NewsAPI + Reddit + Twitter if enabled)
                news_articles = multi_fetcher.get_combined_items(
                    max_per_source=request.max_articles // 2  # Split quota between sources
                )

                print(f"Fetched {len(news_articles)} items from multi-source")

            except Exception as e:
                print(f"Multi-source fetcher error: {e}")
                # Fallback to mock data if all sources fail
                news_articles = [
                    {
                        "title": "Bitcoin Market Analysis",
                        "description": "Bitcoin shows neutral sentiment.",
                        "content": "Bitcoin market sentiment appears neutral.",
                        "source": "Fallback",
                        "source_type": "news",
                    }
                ]

        # Ensure we have at least some data
        if not news_articles or len(news_articles) == 0:
            news_articles = [
                {
                    "title": "Bitcoin Update",
                    "description": "Bitcoin market analysis.",
                    "content": "Bitcoin market shows mixed signals.",
                    "source": "Default",
                    "source_type": "news",
                }
            ]

        # Technical analysis
        tech_analyzer = TechnicalAnalyzer()
        technical_results = tech_analyzer.analyze(historical_data)

        # Power Law macro analysis
        # TODO: Re-enable when PowerLawModel has get_macro_signal and get_current_position methods
        # bpl = PowerLawModel()
        # power_law_macro = bpl.get_macro_signal(current_price)
        # power_law_position = bpl.get_current_position(current_price)

        # Sentiment analysis - separate Reddit from News
        try:
            sentiment_analyzer = SentimentAnalyzer(analyzer_type="vader")

            # Split articles by source type
            news_items = [a for a in news_articles if a.get("source_type") == "news"]
            reddit_items = [a for a in news_articles if a.get("source_type") == "reddit"]

            # Analyze separately
            if news_items:
                news_sentiment = sentiment_analyzer.analyze_articles(news_items)
            else:
                news_sentiment = {
                    "overall_sentiment": "neutral",
                    "recommendation": "hold",
                    "confidence": 0.5,
                    "average_compound": 0.0,
                    "article_count": 0,
                    "positive_count": 0,
                    "negative_count": 0,
                    "neutral_count": 0,
                }

            if reddit_items:
                reddit_sentiment = sentiment_analyzer.analyze_articles(reddit_items)
            else:
                reddit_sentiment = {
                    "overall_sentiment": "neutral",
                    "recommendation": "hold",
                    "confidence": 0.5,
                    "average_compound": 0.0,
                    "article_count": 0,
                    "positive_count": 0,
                    "negative_count": 0,
                    "neutral_count": 0,
                }

            # Track source counts
            source_counts = {"news": len(news_items), "reddit": len(reddit_items)}

            print(f"Sentiment analysis: {len(news_items)} news, {len(reddit_items)} reddit")

        except Exception as e:
            print(f"Sentiment analysis error: {e}")
            # Create default sentiment results
            news_sentiment = {
                "overall_sentiment": "neutral",
                "recommendation": "hold",
                "confidence": 0.5,
                "average_compound": 0.0,
                "article_count": 0,
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0,
            }
            reddit_sentiment = news_sentiment.copy()
            source_counts = {"news": 0, "reddit": 0}

        # Generate recommendation with ADAPTIVE WEIGHTS
        engine = RecommendationEngine(
            reddit_weight=adaptive_weights["reddit_weight"],
            news_weight=adaptive_weights["news_weight"],
            technical_weight=adaptive_weights["technical_weight"],
        )
        recommendation = engine.generate_recommendation(
            technical_analysis=technical_results,
            news_sentiment_analysis=news_sentiment,
            reddit_sentiment_analysis=reddit_sentiment,
            historical_data=historical_data,
            current_price=current_price,
        )

        # Add sentiment sources to recommendation response
        if "signals" in recommendation and "sentiment" in recommendation["signals"]:
            recommendation["signals"]["sentiment"]["sources"] = source_counts

        # Save recommendation to history (for adaptive learning)
        try:
            rec_id = history_tracker.save_recommendation(
                rec_data=recommendation,
                current_price=current_price,
                weights=adaptive_weights,
                operating_mode="normal",  # TODO: Implement mode detection
                request_params={
                    "days": request.days,
                    "news_days": request.news_days,
                    "max_articles": request.max_articles,
                    "use_mock": request.use_mock,
                },
            )
            logger.info(f"✓ Recommendation saved to database (ID: {rec_id})")
        except Exception as e:
            logger.error(f"Failed to save recommendation: {e}")
            # Don't fail the request if save fails

        # Add optional metadata if requested
        if include:
            meta = {
                "operating_mode": "normal",  # TODO: Implement mode detection
                "weights_used": {
                    "technical": adaptive_weights["technical_weight"],
                    "reddit": adaptive_weights["reddit_weight"],
                    "news": adaptive_weights["news_weight"],
                    "source": "adaptive",
                    "last_updated": weight_manager.get_weight_config().last_updated.isoformat(),
                },
                "data_quality": {
                    "technical_available": True,
                    "sentiment_available": True,
                    "degraded_reason": None,
                },
            }
            recommendation["meta"] = meta

            if include in ["stats", "full"]:
                # Add performance statistics
                recent_accuracy = validation_service.get_recent_accuracy("standard_24h", days=7)
                recommendation["performance_stats"] = {
                    "recent_accuracy": {"7d": round(recent_accuracy, 3)},
                    "recommendations_today": len(
                        history_tracker.get_recent_recommendations(limit=100)
                    ),
                }

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
                "endpoint": "/api/recommendation",
            },
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

        return {"current_price": current_price, "technical_analysis": results}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/sentiment")
async def get_sentiment_analysis(days: int = 7, max_articles: int = 50, use_mock: bool = False):
    """Get sentiment analysis from multiple sources (NewsAPI + Reddit + Twitter)"""
    try:
        if use_mock:
            news_fetcher = MockNewsFetcher()
            news_articles = news_fetcher.fetch_news(
                keywords=["bitcoin", "btc", "cryptocurrency"], days=days, max_articles=max_articles
            )
        else:
            # Get API keys
            try:
                config = get_config()
                newsapi_key = config.get_api_key("newsapi")
            except:
                newsapi_key = None

            try:
                twitter_token = config.get_api_key("twitter_bearer_token")
            except:
                twitter_token = None

            # Use multi-source fetcher
            multi_fetcher = MultiSourceFetcher(
                newsapi_key=newsapi_key, twitter_bearer_token=twitter_token
            )

            news_articles = multi_fetcher.get_combined_items(max_per_source=max_articles // 2)

        sentiment_analyzer = SentimentAnalyzer(analyzer_type="vader")
        results = sentiment_analyzer.analyze_articles(news_articles)

        # Add source breakdown
        source_counts = {}
        for article in news_articles:
            source_type = article.get("source_type", "unknown")
            source_counts[source_type] = source_counts.get(source_type, 0) + 1

        results["sources_used"] = source_counts
        results["total_items"] = len(news_articles)

        return results

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/rebalance")
async def get_rebalance_signal(days: int = 90):
    """
    Get Bitcoin/Gold rebalancing signal with confidence interval

    Analyzes momentum and volatility indicators to generate a rebalancing
    recommendation between Bitcoin and Gold allocations.

    Parameters:
    - days: Number of days of historical data to analyze (default: 90)

    Returns:
    - recommendation: 'increase_btc', 'increase_gold', 'slight_increase_btc',
                     'slight_increase_gold', or 'hold_current'
    - confidence: Signal confidence (0-1)
    - confidence_interval: Lower and upper bounds of confidence
    - suggested_allocation: Recommended BTC/Gold percentage split
    - bitcoin: BTC momentum and volatility indicators
    - gold: Gold momentum and volatility indicators
    - correlation: Current BTC/Gold correlation
    - relative_strength: BTC vs Gold relative performance
    - volatility_ratio: BTC volatility / Gold volatility
    - risk_assessment: Overall portfolio risk analysis
    """
    try:
        cache = get_cache()

        # Check cache (5 minute TTL for rebalance signal)
        cache_key = f"rebalance_signal_{days}"
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            cached_result["cached"] = True
            return cached_result

        # Fetch Bitcoin data
        btc_fetcher = PriceFetcher(provider="yfinance")
        btc_data = btc_fetcher.fetch_historical_data(days=days + 30)  # Extra for indicators

        # Fetch Gold data
        gold_fetcher = GoldFetcher()
        gold_data = gold_fetcher.fetch_historical_data(days=days + 30)

        # Analyze
        analyzer = RebalanceAnalyzer()
        result = analyzer.analyze(btc_data, gold_data)

        # Add metadata with timestamp
        from datetime import datetime

        result["days_analyzed"] = days
        result["cached"] = False
        result["latest_btc_date"] = btc_data.index[-1].strftime("%Y-%m-%d")
        result["data_fetched_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        # Cache for 30 seconds for fresher data
        cache.set(cache_key, result, ttl=30)

        return result

    except Exception as e:
        logger.error(f"Rebalance analysis error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "message": "Failed to generate rebalancing signal"},
        )


@app.get("/api/rebalance/history")
async def get_rebalance_history(days: int = 30):
    """
    Get historical BTC/Gold price ratio and correlation data for charting

    Parameters:
    - days: Number of days of history (default: 30)

    Returns:
    - dates: List of dates
    - btc_prices: Bitcoin prices (normalized to start=100)
    - gold_prices: Gold prices (normalized to start=100)
    - btc_gold_ratio: BTC/Gold price ratio over time
    - rolling_correlation: 14-day rolling correlation
    """
    try:
        # Fetch data
        btc_fetcher = PriceFetcher(provider="yfinance")
        gold_fetcher = GoldFetcher()

        btc_data = btc_fetcher.fetch_historical_data(days=days + 30)
        gold_data = gold_fetcher.fetch_historical_data(days=days + 30)

        # Normalize timezones for alignment
        btc_data.index = pd.to_datetime(btc_data.index).tz_localize(None).normalize()
        gold_data.index = pd.to_datetime(gold_data.index).tz_localize(None).normalize()
        btc_data = btc_data[~btc_data.index.duplicated(keep="last")]
        gold_data = gold_data[~gold_data.index.duplicated(keep="last")]

        # Align data
        common_idx = btc_data.index.intersection(gold_data.index)
        btc_close = btc_data.loc[common_idx, "close"].tail(days)
        gold_close = gold_data.loc[common_idx, "close"].tail(days)

        # Normalize prices (start = 100)
        btc_normalized = (btc_close / btc_close.iloc[0]) * 100
        gold_normalized = (gold_close / gold_close.iloc[0]) * 100

        # Calculate ratio
        btc_gold_ratio = btc_close / gold_close

        # Calculate rolling correlation (14-day)
        btc_returns = btc_close.pct_change()
        gold_returns = gold_close.pct_change()
        rolling_corr = btc_returns.rolling(window=14).corr(gold_returns)

        # Prepare response
        dates = btc_close.index.strftime("%Y-%m-%d").tolist()

        def to_list(series):
            return [None if pd.isna(x) else round(float(x), 4) for x in series]

        return {
            "dates": dates,
            "btc_prices": to_list(btc_normalized),
            "gold_prices": to_list(gold_normalized),
            "btc_gold_ratio": to_list(btc_gold_ratio),
            "rolling_correlation": to_list(rolling_corr),
            "current_ratio": round(float(btc_gold_ratio.iloc[-1]), 4),
            "current_correlation": (
                round(float(rolling_corr.iloc[-1]), 4)
                if not pd.isna(rolling_corr.iloc[-1])
                else None
            ),
        }

    except Exception as e:
        logger.error(f"Rebalance history error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/rebalance/signal")
async def get_rebalance_trigger_signal(
    days: int = 90,
    current_btc_pct: float = 100.0,
    current_gold_pct: float = 0.0,
    target_btc_pct: float = 70.0,
    target_gold_pct: float = 30.0,
):
    """
    Get Kelly Criterion-based rebalance trigger signal

    Analyzes current market conditions to determine if now is a good time
    to rebalance from current allocation toward target allocation.

    Parameters:
    - days: Historical data period for analysis (default: 90)
    - current_btc_pct: Current BTC allocation percentage (default: 100)
    - current_gold_pct: Current Gold allocation percentage (default: 0)
    - target_btc_pct: Target BTC allocation percentage (default: 70)
    - target_gold_pct: Target Gold allocation percentage (default: 30)

    Returns:
    - should_rebalance_now: Whether conditions favor rebalancing now
    - urgency: 'none', 'low', 'medium', or 'high'
    - confidence: Signal confidence (0-1)
    - trigger_conditions: Active/inactive trigger checklist
    - price_targets: BTC price levels for rebalancing decisions
    - suggested_action: Specific rebalance recommendation
    """
    try:
        cache = get_cache()

        # Check cache (2 minute TTL for trigger signal)
        cache_key = f"rebalance_signal_{days}_{current_btc_pct}_{target_btc_pct}"
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            cached_result["cached"] = True
            return cached_result

        # Fetch Bitcoin data
        btc_fetcher = PriceFetcher(provider="yfinance")
        btc_data = btc_fetcher.fetch_historical_data(days=days + 30)

        # Fetch Gold data
        gold_fetcher = GoldFetcher()
        gold_data = gold_fetcher.fetch_historical_data(days=days + 30)

        # Generate signal
        analyzer = RebalanceAnalyzer()
        result = analyzer.generate_rebalance_signal(
            btc_data=btc_data,
            gold_data=gold_data,
            current_btc_pct=current_btc_pct,
            current_gold_pct=current_gold_pct,
            target_btc_pct=target_btc_pct,
            target_gold_pct=target_gold_pct,
        )

        # Add metadata with timestamp
        from datetime import datetime

        result["days_analyzed"] = days
        result["cached"] = False
        result["latest_btc_date"] = btc_data.index[-1].strftime("%Y-%m-%d")
        result["data_fetched_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        # Cache for 30 seconds for fresher data
        cache.set(cache_key, result, ttl=30)

        return result

    except Exception as e:
        logger.error(f"Rebalance signal error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "message": "Failed to generate rebalance trigger signal"},
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
        dates = historical_data.index.strftime("%Y-%m-%d").tolist()

        # Convert to list and replace NaN with None for JSON serialization
        def series_to_list(series):
            """Convert pandas Series to list, replacing NaN with None"""
            return [None if pd.isna(x) else round(float(x), 2) for x in series]

        return {
            "dates": dates,
            "price": [round(float(x), 2) for x in historical_data["close"]],
            "ema_20": series_to_list(ema_20),
            "sma_50": series_to_list(sma_50),
            "sma_200": series_to_list(sma_200),
            "ema_21week": series_to_list(ema_21week),
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/power-law/position")
async def get_power_law_position():
    """
    Get current Bitcoin position relative to Power Law bands

    TEMPORARILY DISABLED: PowerLawModel needs get_current_position and get_macro_signal methods
    """
    return JSONResponse(
        status_code=501,
        content={"error": "Power Law position endpoint temporarily disabled during system upgrade"},
    )

    # TODO: Re-enable when PowerLawModel has required methods
    # try:
    #     price_fetcher = PriceFetcher(provider="yfinance")
    #     current_price = price_fetcher.get_current_price()
    #     bpl = PowerLawModel()
    #     position = bpl.get_current_position(current_price)
    #     macro_signal = bpl.get_macro_signal(current_price)
    #     return {
    #         "current_price": current_price,
    #         "position": position,
    #         "macro_signal": macro_signal
    #     }
    # except Exception as e:
    #     return JSONResponse(
    #         status_code=500,
    #         content={"error": str(e)}
    #     )


@app.get("/api/power-law/corridor")
async def get_power_law_corridor(points: int = 100):
    """
    Get Power Law corridor data for charting

    TEMPORARILY DISABLED: PowerLawModel needs generate_corridor_data method
    """
    return JSONResponse(
        status_code=501,
        content={"error": "Power Law corridor endpoint temporarily disabled during system upgrade"},
    )

    # TODO: Re-enable when PowerLawModel has generate_corridor_data method
    # try:
    #     bpl = PowerLawModel()
    #     corridor_data = bpl.generate_corridor_data(points=points)
    #     return corridor_data
    # except Exception as e:
    #     return JSONResponse(
    #         status_code=500,
    #         content={"error": str(e)}
    #     )


@app.get("/api/metrics")
async def get_metrics():
    """
    Get system metrics and adaptive learning statistics

    Returns comprehensive metrics about:
    - Current adaptive weights
    - Historical accuracy rates
    - System health (background services)
    - Cache performance
    - Recommendation statistics
    """
    try:
        # Get weight statistics
        weight_stats = weight_manager.get_stats()

        # Get validation statistics
        validation_stats = validation_service.get_validation_stats()

        # Get history statistics
        history_stats = history_tracker.get_stats()

        # Get background service stats
        background_stats = {}

        if price_monitor:
            background_stats["price_monitor"] = price_monitor.get_stats()

        if validation_job:
            background_stats["validation_job"] = validation_job.get_stats()

        if weight_optimizer:
            background_stats["weight_optimizer"] = weight_optimizer.get_stats()

        return {
            "system_health": {
                "status": "healthy",
                "operating_mode": "normal",  # TODO: Implement mode detection
                "services_running": len(
                    [
                        s
                        for s in background_stats.values()
                        if s.get("status") in ["healthy", "running", "active"]
                    ]
                ),
            },
            "adaptive_weights": weight_stats,
            "validation": validation_stats,
            "history": history_stats,
            "background_services": background_stats,
        }

    except Exception as e:
        logger.error(f"Failed to get metrics: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/adaptive-stats")
async def get_adaptive_stats():
    """
    Get detailed adaptive system statistics for the System Intelligence dashboard tab

    Returns:
    - Weight evolution over time with Bayesian phase indicators
    - Accuracy metrics by recommendation type (buy/sell/hold)
    - Sharpe ratio trends over time
    - Data quality indicators and graceful degradation messages
    """
    try:
        from datetime import datetime, timedelta

        from src.database.models import Recommendation, WeightHistory
        from src.database.session import get_db_session

        # Get database session
        db = get_db_session()

        try:
            # 1. Weight Evolution Data
            weight_history = (
                db.query(WeightHistory).order_by(WeightHistory.timestamp.desc()).limit(90).all()
            )
            weight_history.reverse()  # Chronological order

            weight_evolution = {
                "dates": [w.timestamp.strftime("%Y-%m-%d") for w in weight_history],
                "technical": [round(w.weight_technical, 3) for w in weight_history],
                "reddit": [round(w.weight_reddit, 3) for w in weight_history],
                "news": [round(w.weight_news, 3) for w in weight_history],
                "bayesian_factors": [round(w.prior_weight_factor, 3) for w in weight_history],
            }

            # Calculate Bayesian phase for each point
            phases = []
            for w in weight_history:
                if w.prior_weight_factor >= 0.7:
                    phases.append("Cold Start")
                elif w.prior_weight_factor >= 0.3:
                    phases.append("Transitioning")
                else:
                    phases.append("Fully Adaptive")
            weight_evolution["phases"] = phases

            # 2. Accuracy Metrics by Recommendation Type
            # Calculate accuracy from actual recommendations and validations
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)

            # Initialize accuracy by type
            accuracy_by_type = {
                "buy": {"correct": 0, "total": 0, "rate": 0.0},
                "sell": {"correct": 0, "total": 0, "rate": 0.0},
                "hold": {"correct": 0, "total": 0, "rate": 0.0},
                "strong_buy": {"correct": 0, "total": 0, "rate": 0.0},
                "strong_sell": {"correct": 0, "total": 0, "rate": 0.0},
            }

            # Get recent recommendations with their validations
            from src.database.models import ValidationResult

            recent_recs = (
                db.query(Recommendation).filter(Recommendation.timestamp >= thirty_days_ago).all()
            )

            # Calculate accuracy from validation results
            for rec in recent_recs:
                rec_type = rec.recommendation
                if rec_type in accuracy_by_type:
                    # Get validation results for this recommendation
                    validations = (
                        db.query(ValidationResult)
                        .filter(ValidationResult.recommendation_id == rec.id)
                        .all()
                    )

                    if validations:
                        # Count successful validations
                        for val in validations:
                            accuracy_by_type[rec_type]["total"] += 1
                            if val.outcome == "success":
                                accuracy_by_type[rec_type]["correct"] += 1

            # Calculate rates
            for rec_type in accuracy_by_type:
                if accuracy_by_type[rec_type]["total"] > 0:
                    accuracy_by_type[rec_type]["rate"] = round(
                        accuracy_by_type[rec_type]["correct"] / accuracy_by_type[rec_type]["total"],
                        3,
                    )

            # 3. Sharpe Ratio Trends
            # Get recent Sharpe ratios from weight history (stored during optimization)
            sharpe_trends = {"dates": [], "technical": [], "reddit": [], "news": [], "combined": []}

            # Note: We'll need to add Sharpe ratio storage to WeightHistory model later
            # For now, return empty arrays with a note
            sharpe_trends["note"] = (
                "Sharpe ratio tracking will be available after next optimization cycle"
            )

            # 4. Data Quality and Graceful Degradation
            total_recs = db.query(Recommendation).count()
            recent_recs = (
                db.query(Recommendation).filter(Recommendation.timestamp >= thirty_days_ago).count()
            )

            data_quality = {
                "total_recommendations": total_recs,
                "recent_recommendations_30d": recent_recs,
                "has_sufficient_data": total_recs >= 30,
                "message": None,
            }

            if total_recs < 30:
                data_quality["message"] = (
                    f"System is in learning phase ({total_recs}/30 recommendations). Full metrics available after {30 - total_recs} more recommendations."
                )
            elif recent_recs < 10:
                data_quality["message"] = (
                    "Limited recent data. Consider increasing recommendation frequency for better adaptive learning."
                )

            # 5. Current System Status
            current_weights = weight_manager.get_current_weights()
            current_config = weight_manager.get_weight_config()

            # Get days_of_data from the latest WeightHistory record
            latest_weight_history = weight_history[-1] if weight_history else None
            days_of_data = latest_weight_history.days_of_data if latest_weight_history else 0

            system_status = {
                "current_weights": {
                    "technical": round(current_weights["technical_weight"], 3),
                    "reddit": round(current_weights["reddit_weight"], 3),
                    "news": round(current_weights["news_weight"], 3),
                },
                "last_optimization": (
                    current_config.last_updated.isoformat() if current_config else None
                ),
                "days_of_data": days_of_data,
                "bayesian_phase": phases[-1] if phases else "Unknown",
            }

            return {
                "weight_evolution": weight_evolution,
                "accuracy_by_type": accuracy_by_type,
                "sharpe_trends": sharpe_trends,
                "data_quality": data_quality,
                "system_status": system_status,
                "timestamp": datetime.utcnow().isoformat(),
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Failed to get adaptive stats: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "message": "Unable to fetch adaptive system statistics"},
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
