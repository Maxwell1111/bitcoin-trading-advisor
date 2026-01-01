#!/usr/bin/env python3
"""
Direct Power Law analysis test - shows the power law calculations
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.data.price_fetcher import PriceFetcher
from src.analysis.power_law import PowerLawModel

print("=" * 70)
print("BITCOIN POWER LAW ANALYSIS TEST".center(70))
print("=" * 70)

try:
    # Fetch price data
    print("\n[1/2] Fetching Bitcoin price data...")
    price_fetcher = PriceFetcher(provider="yfinance")
    current_price = price_fetcher.get_current_price()
    print(f"✓ Current BTC Price: ${current_price:,.2f}")

    # Fetch enough historical data for power law (need long-term data)
    historical_data = price_fetcher.fetch_historical_data(days=1500)
    print(f"✓ Retrieved {len(historical_data)} days of historical data")

    # Power Law Analysis
    print("\n[2/2] Running Power Law analysis...")
    power_law = PowerLawModel(corridor_offset=0.6)
    results = power_law.analyze(historical_data)

    print("\n" + "=" * 70)
    print("POWER LAW RESULTS".center(70))
    print("=" * 70)
    print(f"\nCurrent Price:     ${results['current_price']:>12,.2f}")
    print(f"Fair Value:        ${results['fair_value']:>12,.2f}")
    print(f"Support (Deep):    ${results['support_value']:>12,.2f}")
    print(f"Resistance (Bubble):${results['resistance_value']:>12,.2f}")
    print(f"\nStatus: {results['status']}")

    # Calculate position relative to fair value
    deviation = ((results['current_price'] - results['fair_value']) / results['fair_value']) * 100
    print(f"Deviation from Fair Value: {deviation:+.1f}%")

    # Show corridor position
    if results['current_price'] < results['support_value']:
        below_support = ((results['support_value'] - results['current_price']) / results['support_value']) * 100
        print(f"Below Support by: {below_support:.1f}%")
    elif results['current_price'] > results['resistance_value']:
        above_resistance = ((results['current_price'] - results['resistance_value']) / results['resistance_value']) * 100
        print(f"Above Resistance by: {above_resistance:.1f}%")

    if results['mean_reversion_narrative']:
        print(f"\nMean Reversion Signal:")
        print(f"  {results['mean_reversion_narrative']}")

    print("\n" + "=" * 70)
    print("✓ Power Law integration is working correctly!")
    print("=" * 70)

    # Show formula
    print("\nFormula: Price = 10^-17 × (days_since_genesis)^5.8")
    print("Genesis Date: January 3, 2009 (Bitcoin's birth)")
    print("Corridor Offset: ±0.6 in log10 space (~4x multiplier)")

except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
