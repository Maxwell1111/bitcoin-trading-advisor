"""
Bitcoin Trading Advisor FastAPI Application
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.data.price_fetcher import PriceFetcher
from src.data.news_fetcher import NewsFetcher, MockNewsFetcher
from src.analysis.technical import TechnicalAnalyzer
from src.analysis.sentiment import SentimentAnalyzer
from src.engine.recommendation import RecommendationEngine
from src.utils.config import get_config

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
    """Root endpoint"""
    return {
        "message": "Bitcoin Portfolio Advisor API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "recommendation": "/api/recommendation",
            "price": "/api/price"
        }
    }


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
    """Get current Bitcoin price"""
    try:
        fetcher = PriceFetcher(provider="coingecko")
        price = fetcher.get_current_price()
        return {
            "price": price,
            "currency": "USD",
            "symbol": "BTC"
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
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
        # Fetch price data
        price_fetcher = PriceFetcher(provider="coingecko")
        current_price = price_fetcher.get_current_price()
        historical_data = price_fetcher.fetch_historical_data(days=request.days)

        # Fetch news
        if request.use_mock:
            news_fetcher = MockNewsFetcher()
        else:
            try:
                config = get_config()
                api_key = config.get_api_key('newsapi')
                news_fetcher = NewsFetcher(api_key=api_key, provider='newsapi')
            except (ValueError, FileNotFoundError):
                # Fall back to mock if no API key
                news_fetcher = MockNewsFetcher()

        news_articles = news_fetcher.fetch_news(
            keywords=['bitcoin', 'btc', 'cryptocurrency'],
            days=request.news_days,
            max_articles=request.max_articles
        )

        # Technical analysis
        tech_analyzer = TechnicalAnalyzer()
        technical_results = tech_analyzer.analyze(historical_data)

        # Sentiment analysis
        sentiment_analyzer = SentimentAnalyzer(analyzer_type='vader')
        sentiment_results = sentiment_analyzer.analyze_articles(news_articles)

        # Generate recommendation
        engine = RecommendationEngine(technical_weight=0.6, sentiment_weight=0.4)
        recommendation = engine.generate_recommendation(
            technical_analysis=technical_results,
            sentiment_analysis=sentiment_results,
            current_price=current_price
        )

        return RecommendationResponse(**recommendation)

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get("/api/technical")
async def get_technical_analysis(days: int = 100):
    """Get only technical analysis"""
    try:
        price_fetcher = PriceFetcher(provider="coingecko")
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
    """Get only sentiment analysis"""
    try:
        if use_mock:
            news_fetcher = MockNewsFetcher()
        else:
            try:
                config = get_config()
                api_key = config.get_api_key('newsapi')
                news_fetcher = NewsFetcher(api_key=api_key, provider='newsapi')
            except (ValueError, FileNotFoundError):
                news_fetcher = MockNewsFetcher()

        news_articles = news_fetcher.fetch_news(
            keywords=['bitcoin', 'btc', 'cryptocurrency'],
            days=days,
            max_articles=max_articles
        )

        sentiment_analyzer = SentimentAnalyzer(analyzer_type='vader')
        results = sentiment_analyzer.analyze_articles(news_articles)

        return results

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
