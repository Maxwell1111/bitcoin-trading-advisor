
import logging
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import get_trading_recommendation

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# ---

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
    reddit_posts: int = Query(100, description="Maximum number of reddit posts to analyze"),
):
    """
    Returns a trading recommendation for Bitcoin.
    """
    logging.info(f"API call to /recommendation with params: mock={mock}, days={days}, news_days={news_days}, articles={articles}, reddit_posts={reddit_posts}")
    try:
        recommendation, _, _, _ = get_trading_recommendation(
            mock=mock,
            days=days,
            news_days=news_days,
            articles=articles,
            reddit_posts=reddit_posts,
        )
        
        logging.info(f"Successfully generated recommendation: {recommendation.get('recommendation')}")

        if recommendation.get('recommendation') == 'CONTRARIAN_ALERT':
             return {
                "decision": recommendation.get('alert_type', 'CONTRARIAN_ALERT'),
                "confidence": recommendation.get('confidence', 1.0),
                "details": recommendation.get('reasoning', '')
            }

        if recommendation.get('recommendation') == 'POWER_LAW_ALERT':
             return {
                "decision": recommendation.get('alert_type', 'POWER_LAW_ALERT'),
                "confidence": recommendation.get('confidence', 1.0),
                "details": recommendation.get('reasoning', '')
            }

        return {
            "decision": recommendation['recommendation'],
            "confidence": recommendation['confidence'],
            "details": recommendation['reasoning']
        }
    except Exception as e:
        # This is the crucial part: log the full traceback of the error
        logging.error("!!! UNHANDLED EXCEPTION IN API !!!", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")

