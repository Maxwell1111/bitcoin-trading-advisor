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
from src.analysis.technical import TechnicalAnalyzer
from src.analysis.sentiment import SentimentAnalyzer
from src.engine.recommendation import RecommendationEngine
from src.utils.config import get_config


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

    args = parser.parse_args()

    print("=" * 70)
    print("BITCOIN PORTFOLIO ADVISOR".center(70))
    print("=" * 70)
    print()

    try:
        # Load configuration
        if not args.mock:
            print("Loading configuration...")
            config = get_config()
            print("✓ Configuration loaded")
        else:
            print("Running in MOCK MODE (using sample data)")
            config = None

        # Step 1: Fetch price data
        print("\n[1/5] Fetching Bitcoin price data...")
        price_fetcher = PriceFetcher(provider="coingecko")

        current_price = price_fetcher.get_current_price()
        print(f"✓ Current BTC Price: ${current_price:,.2f}")

        historical_data = price_fetcher.fetch_historical_data(days=args.days)
        print(f"✓ Retrieved {len(historical_data)} days of historical data")

        # Step 2: Fetch news
        print("\n[2/5] Fetching cryptocurrency news...")

        if args.mock or not config:
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
            days=args.news_days,
            max_articles=args.articles
        )
        print(f"✓ Retrieved {len(news_articles)} news articles")

        # Step 3: Technical Analysis
        print("\n[3/5] Performing technical analysis...")
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

        # Step 4: Sentiment Analysis
        print("\n[4/5] Analyzing news sentiment...")
        sentiment_analyzer = SentimentAnalyzer(analyzer_type='vader')

        sentiment_results = sentiment_analyzer.analyze_articles(news_articles)
        print(f"✓ Overall Sentiment: {sentiment_results['overall_sentiment'].upper()}")
        print(f"✓ Sentiment Score: {sentiment_results['average_compound']:.3f}")
        print(f"✓ Positive: {sentiment_results['positive_count']}, "
              f"Negative: {sentiment_results['negative_count']}, "
              f"Neutral: {sentiment_results['neutral_count']}")

        # Step 5: Generate Recommendation
        print("\n[5/5] Generating recommendation...")

        # Get weights from config or use defaults
        if config:
            tech_weight = config.get('recommendation.technical_weight', 0.6)
            sent_weight = config.get('recommendation.sentiment_weight', 0.4)
        else:
            tech_weight = 0.6
            sent_weight = 0.4

        engine = RecommendationEngine(
            technical_weight=tech_weight,
            sentiment_weight=sent_weight
        )

        recommendation = engine.generate_recommendation(
            technical_analysis=technical_results,
            sentiment_analysis=sentiment_results,
            current_price=current_price
        )

        # Display results
        print("\n")
        print(engine.format_recommendation(recommendation))

        # Optional: Show top news headlines
        if len(news_articles) > 0:
            print("\n" + "=" * 70)
            print("TOP NEWS HEADLINES:".center(70))
            print("=" * 70)
            for i, article in enumerate(news_articles[:5], 1):
                sentiment_result = sentiment_analyzer.analyze_article(article)
                sentiment_label = sentiment_result['classification'].upper()
                print(f"\n{i}. {article['title']}")
                print(f"   Source: {article.get('source', 'Unknown')} | "
                      f"Sentiment: {sentiment_label}")

        print("\n" + "=" * 70)
        print("Analysis complete! Happy investing! 🚀".center(70))
        print("=" * 70)

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if args.mock:
            print("\nEven in mock mode, an error occurred. Please check your installation.")
        else:
            print("\nTry running with --mock flag to test without API keys:")
            print("  python main.py --mock")
        sys.exit(1)


if __name__ == "__main__":
    main()
