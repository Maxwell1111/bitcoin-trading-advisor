"""
Bitcoin Power Law Model
Implements the power law regression for long-term Bitcoin valuation

Formula: Price = 10^(-17) × (days_since_genesis)^(5.8)

Reference: https://www.lookintobitcoin.com/charts/bitcoin-power-law/
Genesis Block: January 3, 2009
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Tuple, List
import pandas as pd


class BitcoinPowerLaw:
    """
    Bitcoin Power Law Model for long-term valuation

    The power law behaves like natural growth systems (city populations,
    biological systems) rather than traditional finance models, making it
    a "scale-invariant" model for Bitcoin's long-term trajectory.
    """

    # Genesis block date
    GENESIS_DATE = datetime(2009, 1, 3)

    # Power law parameters (from historical regression)
    # Price = 10^A × (days)^B
    A = -17.0  # Intercept
    B = 5.8    # Slope (power)

    # Standard deviation for bands (from historical data)
    # These create the support and resistance corridors
    BAND_WIDTH = 0.4  # Log scale standard deviation

    def __init__(self):
        """Initialize Bitcoin Power Law calculator"""
        pass

    def days_since_genesis(self, date: datetime = None) -> int:
        """
        Calculate days since Bitcoin genesis block

        Args:
            date: Date to calculate from (default: now)

        Returns:
            Number of days since January 3, 2009
        """
        if date is None:
            date = datetime.now()

        delta = date - self.GENESIS_DATE
        return delta.days

    def calculate_fair_value(self, days: int) -> float:
        """
        Calculate fair value using power law formula

        Price = 10^(-17) × (days_since_genesis)^(5.8)

        Args:
            days: Days since genesis block

        Returns:
            Fair value price in USD
        """
        if days <= 0:
            return 0.0

        # Power law formula
        log_price = self.A + self.B * np.log10(days)
        price = 10 ** log_price

        return price

    def calculate_support(self, days: int) -> float:
        """
        Calculate support band (lower bound)

        Args:
            days: Days since genesis block

        Returns:
            Support price in USD
        """
        if days <= 0:
            return 0.0

        # Support is fair value minus band width (in log scale)
        log_price = self.A + self.B * np.log10(days) - self.BAND_WIDTH
        price = 10 ** log_price

        return price

    def calculate_resistance(self, days: int) -> float:
        """
        Calculate resistance band (upper bound / bubble territory)

        Args:
            days: Days since genesis block

        Returns:
            Resistance price in USD
        """
        if days <= 0:
            return 0.0

        # Resistance is fair value plus band width (in log scale)
        log_price = self.A + self.B * np.log10(days) + self.BAND_WIDTH
        price = 10 ** log_price

        return price

    def get_current_position(self, current_price: float, date: datetime = None) -> Dict:
        """
        Get current position relative to power law bands

        Args:
            current_price: Current Bitcoin price
            date: Date to calculate for (default: now)

        Returns:
            Dictionary with position analysis
        """
        days = self.days_since_genesis(date)

        fair_value = self.calculate_fair_value(days)
        support = self.calculate_support(days)
        resistance = self.calculate_resistance(days)

        # Calculate position metrics
        fair_value_ratio = current_price / fair_value if fair_value > 0 else 0
        support_ratio = current_price / support if support > 0 else 0
        resistance_ratio = current_price / resistance if resistance > 0 else 0

        # Determine zone
        if current_price < support:
            zone = "deep_value"
            zone_description = "Deep Value Zone"
            color = "green"
        elif current_price > resistance:
            zone = "bubble_risk"
            zone_description = "Bubble Risk Zone"
            color = "red"
        elif current_price < fair_value:
            zone = "accumulation"
            zone_description = "Accumulation Zone"
            color = "lightgreen"
        elif current_price > fair_value:
            zone = "distribution"
            zone_description = "Distribution Zone"
            color = "orange"
        else:
            zone = "fair_value"
            zone_description = "Fair Value"
            color = "yellow"

        # Calculate deviation from fair value
        deviation_pct = ((current_price / fair_value) - 1) * 100 if fair_value > 0 else 0

        return {
            'days_since_genesis': days,
            'current_price': round(current_price, 2),
            'fair_value': round(fair_value, 2),
            'support': round(support, 2),
            'resistance': round(resistance, 2),
            'fair_value_ratio': round(fair_value_ratio, 3),
            'support_ratio': round(support_ratio, 3),
            'resistance_ratio': round(resistance_ratio, 3),
            'deviation_from_fair_value_pct': round(deviation_pct, 1),
            'zone': zone,
            'zone_description': zone_description,
            'zone_color': color,
            'date': date.isoformat() if date else datetime.now().isoformat()
        }

    def generate_corridor_data(self, start_date: datetime = None,
                              end_date: datetime = None,
                              points: int = 100) -> Dict:
        """
        Generate power law corridor data for charting

        Args:
            start_date: Start date (default: 1 year after genesis)
            end_date: End date (default: 10 years from now)
            points: Number of data points to generate

        Returns:
            Dictionary with dates and price arrays for charting
        """
        if start_date is None:
            start_date = self.GENESIS_DATE + timedelta(days=365)  # Start 1 year after genesis

        if end_date is None:
            end_date = datetime.now() + timedelta(days=365 * 10)  # 10 years into future

        # Generate dates
        date_range = pd.date_range(start=start_date, end=end_date, periods=points)

        dates = []
        fair_values = []
        supports = []
        resistances = []

        for date in date_range:
            days = self.days_since_genesis(date)

            dates.append(date.strftime('%Y-%m-%d'))
            fair_values.append(round(self.calculate_fair_value(days), 2))
            supports.append(round(self.calculate_support(days), 2))
            resistances.append(round(self.calculate_resistance(days), 2))

        return {
            'dates': dates,
            'fair_value': fair_values,
            'support': supports,
            'resistance': resistances,
            'days_since_genesis': [self.days_since_genesis(date) for date in date_range]
        }

    def get_macro_signal(self, current_price: float, date: datetime = None) -> Dict:
        """
        Get macro signal for AI advisor integration

        Args:
            current_price: Current Bitcoin price
            date: Date to calculate for (default: now)

        Returns:
            Dictionary with macro signal and reasoning
        """
        position = self.get_current_position(current_price, date)

        zone = position['zone']
        deviation = position['deviation_from_fair_value_pct']
        fair_value = position['fair_value']

        # Determine signal and reasoning
        if zone == "deep_value":
            signal = "strong_buy"
            confidence = 0.95
            reasoning = (
                f"POWER LAW DEEP VALUE: Price is below the historical support band "
                f"(${position['support']:,.0f}). Historically, this has been an exceptional "
                f"accumulation zone with minimal downside risk. Current price is "
                f"{abs(deviation):.1f}% below fair value (${fair_value:,.0f})."
            )
            override = True

        elif zone == "bubble_risk":
            signal = "high_risk"
            confidence = 0.90
            reasoning = (
                f"POWER LAW BUBBLE WARNING: Price is above the historical resistance band "
                f"(${position['resistance']:,.0f}). This zone has marked cycle tops in 2013, "
                f"2017, and 2021. Consider distribution. Price is {deviation:.1f}% above "
                f"fair value (${fair_value:,.0f})."
            )
            override = True

        elif zone == "accumulation" and deviation < -30:
            signal = "buy"
            confidence = 0.75
            reasoning = (
                f"POWER LAW ACCUMULATION: Price is {abs(deviation):.1f}% below fair value "
                f"(${fair_value:,.0f}). Mean reversion suggests probable upside over 6-12 months. "
                f"Good risk/reward for accumulation."
            )
            override = False

        elif zone == "distribution" and deviation > 30:
            signal = "caution"
            confidence = 0.70
            reasoning = (
                f"POWER LAW DISTRIBUTION: Price is {deviation:.1f}% above fair value "
                f"(${fair_value:,.0f}). Mean reversion suggests probable consolidation or "
                f"correction over 6-12 months. Consider taking profits."
            )
            override = False

        else:
            signal = "neutral"
            confidence = 0.50
            reasoning = (
                f"POWER LAW FAIR VALUE: Price is near fair value (${fair_value:,.0f}), "
                f"currently {deviation:+.1f}% from regression center. No strong macro signal. "
                f"Focus on short-term technicals and sentiment."
            )
            override = False

        return {
            'signal': signal,
            'confidence': confidence,
            'reasoning': reasoning,
            'should_override': override,
            'position': position
        }


if __name__ == "__main__":
    # Test the power law model
    print("Bitcoin Power Law Model Test\n")
    print("=" * 60)

    bpl = BitcoinPowerLaw()

    # Current position
    current_price = 95000  # Example price
    position = bpl.get_current_position(current_price)

    print(f"\nCurrent Analysis (Price: ${current_price:,})")
    print("-" * 60)
    print(f"Days since genesis: {position['days_since_genesis']:,}")
    print(f"Fair Value: ${position['fair_value']:,}")
    print(f"Support: ${position['support']:,}")
    print(f"Resistance: ${position['resistance']:,}")
    print(f"Zone: {position['zone_description']}")
    print(f"Deviation from Fair Value: {position['deviation_from_fair_value_pct']:+.1f}%")

    # Macro signal
    macro = bpl.get_macro_signal(current_price)
    print(f"\nMacro Signal: {macro['signal'].upper()}")
    print(f"Confidence: {macro['confidence'] * 100:.0f}%")
    print(f"Should Override: {macro['should_override']}")
    print(f"\nReasoning: {macro['reasoning']}")

    # Test different price scenarios
    print("\n" + "=" * 60)
    print("Price Scenario Analysis:")
    print("=" * 60)

    scenarios = [
        ("Deep Value", 20000),
        ("Below Fair Value", 60000),
        ("Fair Value", 94000),
        ("Above Fair Value", 130000),
        ("Bubble Territory", 200000)
    ]

    for name, price in scenarios:
        pos = bpl.get_current_position(price)
        print(f"\n{name} (${price:,}): {pos['zone_description']} "
              f"({pos['deviation_from_fair_value_pct']:+.1f}% from FV)")
