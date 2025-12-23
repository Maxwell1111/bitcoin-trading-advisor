#!/usr/bin/env python3
"""
Quick internal UI to view current recommendation with factor breakdown
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.data.price_fetcher import PriceFetcher
from src.analysis.technical import TechnicalAnalyzer
from src.analysis.power_law import PowerLawModel
from src.analysis.sentiment import SentimentAnalyzer
from src.engine.recommendation import RecommendationEngine

def create_bar_chart(value, max_val=1.0, width=40):
    """Create ASCII bar chart"""
    filled = int((abs(value) / max_val) * width)
    if value >= 0:
        bar = '+' + '█' * filled + '░' * (width - filled)
        color = '\033[92m' if value > 0.3 else '\033[93m'  # Green if > 0.3, yellow otherwise
    else:
        bar = '-' + '█' * filled + '░' * (width - filled)
        color = '\033[91m' if value < -0.3 else '\033[93m'  # Red if < -0.3, yellow otherwise
    reset = '\033[0m'
    return f"{color}{bar}{reset} {value:+.3f}"

print("\033[2J\033[H")  # Clear screen
print("=" * 100)
print(" " * 30 + "BITCOIN HOLISTIC ANALYSIS - INTERNAL DASHBOARD")
print("=" * 100)

print("\n[1/5] Fetching Bitcoin price data...")
price_fetcher = PriceFetcher(provider="yfinance")
current_price = price_fetcher.get_current_price()
print(f"✓ Current BTC Price: ${current_price:,.2f}")

power_law_days = 1500
historical_data = price_fetcher.fetch_historical_data(days=power_law_days)
print(f"✓ Retrieved {len(historical_data)} days of historical data")

print("\n[2/5] Running Power Law analysis...")
power_law_analyzer = PowerLawModel()
power_law_results = power_law_analyzer.analyze(historical_data)
print(f"✓ Status: {power_law_results['status']}")

print("\n[3/5] Performing technical analysis...")
tech_analyzer = TechnicalAnalyzer()
short_history = historical_data.tail(100)
technical_results = tech_analyzer.analyze(short_history)
print(f"✓ RSI: {technical_results['rsi']['value']:.1f}")

print("\n[4/5] Analyzing sentiment (mock)...")
mock_sentiment = {
    'overall_sentiment': 'neutral',
    'recommendation': 'hold',
    'confidence': 0.5,
    'average_compound': 0.0,
    'article_count': 0,
    'positive_count': 0,
    'negative_count': 0,
    'neutral_count': 0
}
print("✓ Using neutral sentiment (mock)")

print("\n[5/5] Generating holistic recommendation...")
engine = RecommendationEngine()
recommendation = engine.generate_recommendation(
    power_law_analysis=power_law_results,
    technical_analysis=technical_results,
    news_sentiment_analysis=mock_sentiment,
    reddit_sentiment_analysis=mock_sentiment,
    current_price=current_price
)
print("✓ Recommendation generated")

# Display results
print("\n" + "=" * 100)
print(" " * 40 + "RECOMMENDATION DASHBOARD")
print("=" * 100)

# Overall recommendation
rec_color = {
    'strong_buy': '\033[92m',  # Green
    'buy': '\033[92m',
    'hold': '\033[93m',  # Yellow
    'sell': '\033[91m',  # Red
    'strong_sell': '\033[91m'
}
rec_text = recommendation['recommendation'].replace('_', ' ').upper()
color = rec_color.get(recommendation['recommendation'], '\033[0m')
print(f"\n🎯 RECOMMENDATION: {color}{rec_text}\033[0m")
print(f"📊 Confidence: {recommendation['confidence']*100:.0f}%")
print(f"📈 Composite Score: {recommendation['composite_score']:+.3f}")

# Factor breakdown
print("\n" + "-" * 100)
print("FACTOR BREAKDOWN (weighted scores):")
print("-" * 100)

factors = recommendation['factor_scores']
weights = recommendation['factor_weights']

print(f"\n📊 RSI (Weight: {weights['rsi']*100:.0f}%)")
print(f"   {create_bar_chart(factors['rsi'])}")
print(f"   Current RSI: {technical_results['rsi']['value']:.1f}")

print(f"\n📈 Moving Averages (Weight: {weights['moving_averages']*100:.0f}%)")
print(f"   {create_bar_chart(factors['moving_averages'])}")
print(f"   Trend: {technical_results.get('ma_trend', 'N/A')}")

print(f"\n🌐 Power Law (Weight: {weights['power_law']*100:.0f}%)")
print(f"   {create_bar_chart(factors['power_law'])}")
pl_data = recommendation['power_law_data']
deviation = ((current_price - pl_data['fair_value']) / pl_data['fair_value']) * 100
print(f"   Status: {pl_data['status']} ({deviation:+.1f}% from fair value)")
print(f"   Fair Value: ${pl_data['fair_value']:,.2f}")
print(f"   Support: ${pl_data['support_value']:,.2f}")
print(f"   Resistance: ${pl_data['resistance_value']:,.2f}")

print(f"\n⚡ MACD (Weight: {weights['macd']*100:.0f}%)")
print(f"   {create_bar_chart(factors['macd'])}")
print(f"   Signal: {technical_results['macd']['signal']}")

print(f"\n🗣️ Sentiment (Weight: {weights['sentiment']*100:.0f}%)")
print(f"   {create_bar_chart(factors['sentiment'])}")
print(f"   (Using neutral mock data)")

# Composite calculation
print("\n" + "-" * 100)
print("COMPOSITE SCORE CALCULATION:")
print("-" * 100)
print(f"  RSI:       {factors['rsi']:+.3f} × {weights['rsi']:.2f} = {factors['rsi'] * weights['rsi']:+.3f}")
print(f"  MA:        {factors['moving_averages']:+.3f} × {weights['moving_averages']:.2f} = {factors['moving_averages'] * weights['moving_averages']:+.3f}")
print(f"  Power Law: {factors['power_law']:+.3f} × {weights['power_law']:.2f} = {factors['power_law'] * weights['power_law']:+.3f}")
print(f"  MACD:      {factors['macd']:+.3f} × {weights['macd']:.2f} = {factors['macd'] * weights['macd']:+.3f}")
print(f"  Sentiment: {factors['sentiment']:+.3f} × {weights['sentiment']:.2f} = {factors['sentiment'] * weights['sentiment']:+.3f}")
print(f"  " + "-" * 50)
print(f"  TOTAL:     {recommendation['composite_score']:+.3f}")

# Score interpretation
print("\n" + "-" * 100)
print("SCORE INTERPRETATION:")
print("-" * 100)
print("  +0.70 to +1.00 = Strong Buy")
print("  +0.30 to +0.70 = Buy")
print("  -0.30 to +0.30 = Hold")
print("  -0.70 to -0.30 = Sell")
print("  -1.00 to -0.70 = Strong Sell")

print("\n" + "=" * 100)
print("\n✅ For backtesting: Run 'python3 backtest_advisor.py'")
print("📊 For visualization: Open 'backtest_visualization.html' in your browser")
print("=" * 100)
