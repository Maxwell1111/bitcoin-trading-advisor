
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import get_trading_recommendation
from src.engine.recommendation import RecommendationEngine

app = FastAPI(
    title="Bitcoin Trading Advisor API",
    description="Provides trading recommendations based on market analysis.",
    version="1.0.0",
)

class Recommendation(BaseModel):
    decision: str
    confidence: float
    details: str

@app.get("/")
def read_root():
    """A simple endpoint to confirm the API is running."""
    return {"status": "ok"}

@app.get("/recommendation", response_model=Recommendation)
def get_recommendation_api(
    mock: bool = Query(False, description="Use mock data for testing"),
    days: int = Query(100, description="Number of days of historical price data"),
    news_days: int = Query(7, description="Number of days of news to analyze"),
    articles: int = Query(50, description="Maximum number of news articles to analyze"),
):
    """
    Returns a trading recommendation for Bitcoin.
    """
    try:
        recommendation, _, _, engine = get_trading_recommendation(
            mock=mock,
            days=days,
            news_days=news_days,
            articles=articles,
        )
        
        formatted = engine.format_recommendation(recommendation)


        return {
            "decision": formatted['recommendation'],
            "confidence": formatted['confidence'],
            "details": formatted['reasoning']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

