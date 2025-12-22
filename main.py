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
from src.engine.recommendation import RecommendationEngine
from src.utils.config import get_config


def get_trading_recommendation(
    mock: bool, days: int, news_days: int, articles: int, reddit_posts: int
):
    """
    Fetches data, performs analysis, and returns a trading recommendation.
    """
    try:
        # Load configuration
        if not mock:
            print("Loading configuration...")
            config = get_config()
            print("✓ Configuration loaded")
        else:
            print("Running in MOCK MODE (using sample data)")
            config = None

        # Step 1: Fetch price data
        print("\n[1/6] Fetching Bitcoin price data...")
        price_fetcher = PriceFetcher(provider="coingecko")

        current_price = price_fetcher.get_current_price()
        print(f"✓ Current BTC Price: ${current_price:,.2f}")

        historical_data = price_fetcher.fetch_historical_data(days=days)
        print(f"✓ Retrieved {len(historical_data)} days of historical data")

        # Step 2: Fetch news
        print("\n[2/6] Fetching cryptocurrency news...")

        if mock or not config:
            news_fetcher = MockNewsFetcher()
            print("✓ Using mock news data")
        else:
            try:
                api_key = config.get_api_key('newsapi')
                news_fetcher = NewsFetcher(api_key=api_key, provider='newsapi')
            except ValueError as e:
                print(f"⚠ {e}")
                print("  Using mock news data instead")
                news_fetcher = MockNewsFetcher()

        news_articles = news_fetcher.fetch_news(
            keywords=['bitcoin', 'btc', 'cryptocurrency'],
            days=news_days,
            max_articles=articles
        )
        print(f"✓ Retrieved {len(news_articles)} news articles")

        # Step 3: Fetch Reddit posts
        print("\n[3/6] Fetching Reddit posts...")
        reddit_fetcher = MockRedditFetcher()
        reddit_data = reddit_fetcher.fetch_reddit_posts(subreddit='cryptocurrency', limit=reddit_posts)
        print(f"✓ Retrieved {len(reddit_data)} Reddit posts")


        # Step 4: Technical Analysis
        print("\n[4/6] Performing technical analysis...")
        tech_analyzer = TechnicalAnalyzer(
            rsi_period=14,
            macd_fast=12,
            macd_slow=26,
            macd_signal=9
        )

        technical_results = tech_analyzer.analyze(historical_data)
        print(f"✓ RSI: {technical_results['rsi']['value']:.1f} ({technical_results['rsi']['signal']})")
        print(f"✓ MACD: {technical_results['macd']['signal']}")
        print(f"✓ Technical Recommendation: {technical_results['overall']['recommendation'].upper()}")

        # Step 5: Sentiment Analysis
        print("\n[5/6] Analyzing sentiment...")
        sentiment_analyzer = SentimentAnalyzer(analyzer_type='vader')

        news_sentiment_results = sentiment_analyzer.analyze_articles(news_articles)
        print(f"✓ News Sentiment: {news_sentiment_results['overall_sentiment'].upper()} (Score: {news_sentiment_results['average_compound']:.3f})")
        
        reddit_sentiment_results = sentiment_analyzer.analyze_articles(reddit_data)
        print(f"✓ Reddit Sentiment: {reddit_sentiment_results['overall_sentiment'].upper()} (Score: {reddit_sentiment_results['average_compound']:.3f})")


        # Step 6: Generate Recommendation
        print("\n[6/6] Generating recommendation...")

        # Get weights from config or use defaults
        if config:
            reddit_weight = config.get('recommendation.reddit_weight', 0.4)
            news_weight = config.get('recommendation.news_weight', 0.3)
            tech_weight = config.get('recommendation.technical_weight', 0.3)
        else:
            reddit_weight = 0.4
            news_weight = 0.3
            tech_weight = 0.3

        engine = RecommendationEngine(
            reddit_weight=reddit_weight,
            news_weight=news_weight,
            technical_weight=tech_weight
        )

        recommendation = engine.generate_recommendation(
            technical_analysis=technical_results,
            news_sentiment_analysis=news_sentiment_results,
            reddit_sentiment_analysis=reddit_sentiment_results,
            historical_data=historical_data,
            current_price=current_price
        )

        return recommendation, news_articles, sentiment_analyzer, engine

    except Exception as e:
        print(f"\n❌ Error: {e}")
        if mock:
            print("\nEven in mock mode, an error occurred. Please check your installation.")
        else:
            print("\nTry running with --mock flag to test without API keys:")
            print("  python main.py --mock")
        sys.exit(1)


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
