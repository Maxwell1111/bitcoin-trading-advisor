#!/usr/bin/env python3
"""
Backtest the holistic recommendation engine on historical data
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.data.price_fetcher import PriceFetcher
from src.analysis.technical import TechnicalAnalyzer
from src.analysis.power_law import PowerLawModel
from src.analysis.sentiment import SentimentAnalyzer
from src.engine.recommendation import RecommendationEngine

print("=" * 80)
print("BITCOIN ADVISOR BACKTESTING ENGINE".center(80))
print("=" * 80)

# Configuration
BACKTEST_DAYS = 365  # 1 year of backtesting
WINDOW_SIZE = 100  # Days of data to analyze for each recommendation
STEP_SIZE = 7  # Step forward 7 days at a time (weekly analysis)

print(f"\nConfiguration:")
print(f"  • Backtest Period: {BACKTEST_DAYS} days")
print(f"  • Analysis Window: {WINDOW_SIZE} days")
print(f"  • Step Size: {STEP_SIZE} days (weekly)")

# Fetch historical data
print(f"\n[1/4] Fetching historical data...")
price_fetcher = PriceFetcher(provider="yfinance")
total_days_needed = BACKTEST_DAYS + WINDOW_SIZE + 1500  # Extra for power law
historical_data = price_fetcher.fetch_historical_data(days=total_days_needed)
print(f"✓ Retrieved {len(historical_data)} days of data")

# Initialize analyzers
print(f"\n[2/4] Initializing analyzers...")
tech_analyzer = TechnicalAnalyzer()
power_law_analyzer = PowerLawModel()
engine = RecommendationEngine()
print(f"✓ All analyzers ready")

# Run backtest
print(f"\n[3/4] Running backtest...")
results = []

# Calculate number of iterations
num_iterations = (BACKTEST_DAYS - WINDOW_SIZE) // STEP_SIZE
print(f"  • Running {num_iterations} iterations...")

for i in range(0, BACKTEST_DAYS - WINDOW_SIZE, STEP_SIZE):
    # Get data window
    end_idx = len(historical_data) - (BACKTEST_DAYS - i - WINDOW_SIZE)
    start_idx = max(0, end_idx - 1500)  # Ensure enough data for power law

    window_data = historical_data.iloc[start_idx:end_idx]

    if len(window_data) < WINDOW_SIZE:
        continue

    # Get current price and date
    current_price = window_data['close'].iloc[-1]
    current_date = window_data.index[-1]

    try:
        # Technical Analysis
        ta_window = window_data.tail(WINDOW_SIZE)
        technical_results = tech_analyzer.analyze(ta_window)

        # Power Law Analysis
        power_law_results = power_law_analyzer.analyze(window_data)

        # Mock sentiment (neutral for backtesting - we don't have historical sentiment)
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

        # Generate recommendation
        recommendation = engine.generate_recommendation(
            power_law_analysis=power_law_results,
            technical_analysis=technical_results,
            news_sentiment_analysis=mock_sentiment,
            reddit_sentiment_analysis=mock_sentiment,
            current_price=current_price
        )

        # Calculate future price (7 days ahead)
        future_idx = min(end_idx + STEP_SIZE, len(historical_data) - 1)
        future_price = historical_data['close'].iloc[future_idx]
        price_change_pct = ((future_price - current_price) / current_price) * 100

        # Store results
        results.append({
            'date': current_date,
            'price': current_price,
            'future_price': future_price,
            'price_change_pct': price_change_pct,
            'recommendation': recommendation['recommendation'],
            'confidence': recommendation['confidence'],
            'composite_score': recommendation['composite_score'],
            'rsi_score': recommendation['factor_scores']['rsi'],
            'ma_score': recommendation['factor_scores']['moving_averages'],
            'pl_score': recommendation['factor_scores']['power_law'],
            'macd_score': recommendation['factor_scores']['macd'],
            'sentiment_score': recommendation['factor_scores']['sentiment'],
            'rsi_value': technical_results['rsi']['value'],
            'power_law_status': power_law_results['status'],
            'power_law_deviation': ((current_price - power_law_results['fair_value']) /
                                   power_law_results['fair_value']) * 100
        })

    except Exception as e:
        print(f"  ! Error at {current_date}: {e}")
        continue

print(f"✓ Completed {len(results)} iterations")

# Convert to DataFrame
df = pd.DataFrame(results)

# Calculate performance metrics
print(f"\n[4/4] Analyzing performance...")

# How often would we have been right?
df['signal'] = df['composite_score'].apply(lambda x: 'buy' if x > 0.3 else ('sell' if x < -0.3 else 'hold'))
df['correct'] = ((df['signal'] == 'buy') & (df['price_change_pct'] > 0)) | \
                ((df['signal'] == 'sell') & (df['price_change_pct'] < 0)) | \
                ((df['signal'] == 'hold') & (df['price_change_pct'].abs() < 2))

accuracy = df['correct'].sum() / len(df) * 100

print(f"\n{'='*80}")
print("BACKTEST RESULTS".center(80))
print(f"{'='*80}")
print(f"\nPeriod: {df['date'].iloc[0].strftime('%Y-%m-%d')} to {df['date'].iloc[-1].strftime('%Y-%m-%d')}")
print(f"Iterations: {len(df)}")
print(f"\nSignal Distribution:")
print(f"  • Buy signals:  {(df['signal'] == 'buy').sum()} ({(df['signal'] == 'buy').sum()/len(df)*100:.1f}%)")
print(f"  • Hold signals: {(df['signal'] == 'hold').sum()} ({(df['signal'] == 'hold').sum()/len(df)*100:.1f}%)")
print(f"  • Sell signals: {(df['signal'] == 'sell').sum()} ({(df['signal'] == 'sell').sum()/len(df)*100:.1f}%)")
print(f"\nAccuracy: {accuracy:.1f}%")

print(f"\nComposite Score Statistics:")
print(f"  • Mean: {df['composite_score'].mean():.3f}")
print(f"  • Std:  {df['composite_score'].std():.3f}")
print(f"  • Min:  {df['composite_score'].min():.3f}")
print(f"  • Max:  {df['composite_score'].max():.3f}")

# Save results
output_file = 'backtest_results.csv'
df.to_csv(output_file, index=False)
print(f"\n✓ Results saved to: {output_file}")

print(f"\n{'='*80}")
print(f"Run 'python3 plot_backtest.py' to visualize results")
print(f"{'='*80}")
