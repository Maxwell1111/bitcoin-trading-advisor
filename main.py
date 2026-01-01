#!/usr/bin/env python3
"""
Bitcoin Portfolio Advisor - Main Entry Point

Combines sentiment analysis from crypto news and technical analysis (RSI & MACD)
to generate Bitcoin trading recommendations.
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.data.price_fetcher import PriceFetcher
from src.data.news_fetcher import NewsFetcher, MockNewsFetcher
from src.data.reddit_fetcher import MockRedditFetcher
from src.analysis.technical import TechnicalAnalyzer
from src.analysis.sentiment import SentimentAnalyzer
from src.analysis.power_law import PowerLawModel
from src.engine.recommendation import RecommendationEngine
from src.utils.config import get_config
import logging

def get_trading_recommendation(
    mock: bool, days: int, news_days: int, articles: int, reddit_posts: int
):
    """
    Fetches data, performs analysis, and returns a trading recommendation.
    """
    try:
        # Load configuration
        if not mock:
            logging.info("Loading configuration...")
            config = get_config()
            logging.info("✓ Configuration loaded")
        else:
            logging.info("Running in MOCK MODE (using sample data)")
            config = None

        # Step 1: Fetch price data
        logging.info("\n[1/7] Fetching Bitcoin price data...")
        price_fetcher = PriceFetcher(provider="yfinance")
        current_price = price_fetcher.get_current_price()
        logging.info(f"✓ Current BTC Price: ${current_price:,.2f}")
        
        # We need long-term data for the power law model
        power_law_days = max(days, 1500) 
        historical_data = price_fetcher.fetch_historical_data(days=power_law_days)
        logging.info(f"✓ Retrieved {len(historical_data)} days of historical data for analysis.")

        # Step 2: Power Law Analysis
        logging.info("\n[2/7] Performing Power Law macro analysis...")
        power_law_analyzer = PowerLawModel()
        power_law_results = power_law_analyzer.analyze(historical_data)
        logging.info(f"✓ Power Law Status: {power_law_results['status']}")

        # Step 3: Fetch news
        logging.info("\n[3/7] Fetching cryptocurrency news...")
        if mock or not config:
            news_fetcher = MockNewsFetcher()
        else:
            # ... (news fetcher logic remains the same)
            news_fetcher = MockNewsFetcher() # Placeholder for now
        news_articles = news_fetcher.fetch_news(keywords=['bitcoin', 'btc'], days=news_days, max_articles=articles)
        logging.info(f"✓ Retrieved {len(news_articles)} news articles")

        # Step 4: Fetch Reddit posts
        logging.info("\n[4/7] Fetching Reddit posts...")
        reddit_fetcher = MockRedditFetcher()
        reddit_data = reddit_fetcher.fetch_reddit_posts(subreddit='cryptocurrency', limit=reddit_posts)
        logging.info(f"✓ Retrieved {len(reddit_data)} Reddit posts")

        # Step 5: Technical Analysis
        logging.info("\n[5/7] Performing short-term technical analysis...")
        tech_analyzer = TechnicalAnalyzer()
        technical_results = tech_analyzer.analyze(historical_data.tail(days)) # Use shorter period for TA
        logging.info(f"✓ Technical analysis recommendation: {technical_results['overall']['recommendation'].upper()}")

        # Step 6: Sentiment Analysis
        logging.info("\n[6/7] Analyzing sentiment...")
        sentiment_analyzer = SentimentAnalyzer(analyzer_type='vader')
        news_sentiment_results = sentiment_analyzer.analyze_articles(news_articles)
        logging.info(f"✓ News Sentiment: {news_sentiment_results['overall_sentiment'].upper()}")
        reddit_sentiment_results = sentiment_analyzer.analyze_articles(reddit_data)
        logging.info(f"✓ Reddit Sentiment: {reddit_sentiment_results['overall_sentiment'].upper()}")

        # Step 7: Generate Recommendation
        logging.info("\n[7/7] Generating final recommendation...")
        engine = RecommendationEngine() # Weights are now handled inside
        recommendation = engine.generate_recommendation(
            power_law_analysis=power_law_results,
            technical_analysis=technical_results,
            news_sentiment_analysis=news_sentiment_results,
            reddit_sentiment_analysis=reddit_sentiment_results,
            current_price=current_price
        )

        # We also need to return the full power law time series for the chart
        recommendation['power_law_chart_data'] = power_law_results['time_series']

        return recommendation, news_articles, sentiment_analyzer, engine

    except Exception as e:
        logging.error("!!! ERROR IN get_trading_recommendation !!!", exc_info=True)
        raise e



def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Bitcoin Portfolio Advisor - Get trading recommendations'
    )
    parser.add_argument(
        '--mock',
        action='store_true',
        help='Use mock data for testing (no API keys required)'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=100,
        help='Number of days of historical price data (default: 100)'
    )
    parser.add_argument(
        '--news-days',
        type=int,
        default=7,
        help='Number of days of news to analyze (default: 7)'
    )
    parser.add_argument(
        '--articles',
        type=int,
        default=50,
        help='Maximum number of news articles to analyze (default: 50)'
    )
    parser.add_argument(
        '--reddit-posts',
        type=int,
        default=100,
        help='Maximum number of reddit posts to analyze (default: 100)'
    )

    args = parser.parse_args()

    print("=" * 70)
    print("BITCOIN PORTFOLIO ADVISOR".center(70))
    print("=" * 70)
    print()

    try:
        recommendation, news_articles, sentiment_analyzer, engine = get_trading_recommendation(
            mock=args.mock,
            days=args.days,
            news_days=args.news_days,
            articles=args.articles,
            reddit_posts=args.reddit_posts,
        )

        # Display results
        print("\n")
        print(engine.format_recommendation(recommendation))

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
