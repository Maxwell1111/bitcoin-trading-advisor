"""
Technical analysis module - RSI and MACD indicators
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple


class TechnicalAnalyzer:
    """Calculate technical indicators (RSI and MACD)"""

    def __init__(self, rsi_period: int = 14, macd_fast: int = 12,
                 macd_slow: int = 26, macd_signal: int = 9):
        """
        Initialize technical analyzer

        Args:
            rsi_period: RSI calculation period (default: 14)
            macd_fast: MACD fast EMA period (default: 12)
            macd_slow: MACD slow EMA period (default: 26)
            macd_signal: MACD signal line period (default: 9)
        """
        self.rsi_period = rsi_period
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal

    def calculate_rsi(self, data: pd.DataFrame, column: str = 'close') -> pd.Series:
        """
        Calculate Relative Strength Index (RSI)

        Args:
            data: DataFrame with price data
            column: Column name to calculate RSI on

        Returns:
            Series with RSI values (0-100)
        """
        prices = data[column].copy()

        # Calculate price changes
        delta = prices.diff()

        # Separate gains and losses
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        # Calculate average gains and losses
        avg_gain = gain.rolling(window=self.rsi_period, min_periods=1).mean()
        avg_loss = loss.rolling(window=self.rsi_period, min_periods=1).mean()

        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def calculate_macd(self, data: pd.DataFrame, column: str = 'close') -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate MACD (Moving Average Convergence Divergence)

        Args:
            data: DataFrame with price data
            column: Column name to calculate MACD on

        Returns:
            Tuple of (macd_line, signal_line, histogram)
        """
        prices = data[column].copy()

        # Calculate EMAs
        ema_fast = prices.ewm(span=self.macd_fast, adjust=False).mean()
        ema_slow = prices.ewm(span=self.macd_slow, adjust=False).mean()

        # Calculate MACD line
        macd_line = ema_fast - ema_slow

        # Calculate signal line
        signal_line = macd_line.ewm(span=self.macd_signal, adjust=False).mean()

        # Calculate histogram
        histogram = macd_line - signal_line

        return macd_line, signal_line, histogram

    def analyze(self, data: pd.DataFrame) -> Dict:
        """
        Perform full technical analysis

        Args:
            data: DataFrame with OHLCV data

        Returns:
            Dictionary with technical analysis results
        """
        # Calculate indicators
        rsi = self.calculate_rsi(data)
        macd_line, signal_line, histogram = self.calculate_macd(data)

        # Get current values (latest)
        current_rsi = rsi.iloc[-1]
        current_macd = macd_line.iloc[-1]
        current_signal = signal_line.iloc[-1]
        current_histogram = histogram.iloc[-1]

        # Previous values for trend detection
        prev_histogram = histogram.iloc[-2] if len(histogram) > 1 else 0

        # RSI interpretation
        if current_rsi > 70:
            rsi_signal = "overbought"
            rsi_recommendation = "sell"
        elif current_rsi < 30:
            rsi_signal = "oversold"
            rsi_recommendation = "buy"
        else:
            rsi_signal = "neutral"
            rsi_recommendation = "hold"

        # MACD interpretation
        if current_macd > current_signal:
            if prev_histogram < 0 and current_histogram > 0:
                macd_signal = "bullish_crossover"
                macd_recommendation = "buy"
            else:
                macd_signal = "bullish"
                macd_recommendation = "buy"
        elif current_macd < current_signal:
            if prev_histogram > 0 and current_histogram < 0:
                macd_signal = "bearish_crossover"
                macd_recommendation = "sell"
            else:
                macd_signal = "bearish"
                macd_recommendation = "sell"
        else:
            macd_signal = "neutral"
            macd_recommendation = "hold"

        # Combined technical signal
        buy_signals = sum([
            rsi_recommendation == "buy",
            macd_recommendation == "buy"
        ])
        sell_signals = sum([
            rsi_recommendation == "sell",
            macd_recommendation == "sell"
        ])

        if buy_signals > sell_signals:
            overall_recommendation = "buy"
            confidence = buy_signals / 2.0
        elif sell_signals > buy_signals:
            overall_recommendation = "sell"
            confidence = sell_signals / 2.0
        else:
            overall_recommendation = "hold"
            confidence = 0.5

        return {
            'rsi': {
                'value': round(current_rsi, 2),
                'signal': rsi_signal,
                'recommendation': rsi_recommendation
            },
            'macd': {
                'macd_line': round(current_macd, 2),
                'signal_line': round(current_signal, 2),
                'histogram': round(current_histogram, 2),
                'signal': macd_signal,
                'recommendation': macd_recommendation
            },
            'overall': {
                'recommendation': overall_recommendation,
                'confidence': round(confidence, 2),
                'buy_signals': buy_signals,
                'sell_signals': sell_signals
            }
        }

    def add_indicators_to_dataframe(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Add all indicators as columns to the dataframe

        Args:
            data: DataFrame with OHLCV data

        Returns:
            DataFrame with added indicator columns
        """
        df = data.copy()

        # Add RSI
        df['rsi'] = self.calculate_rsi(df)

        # Add MACD
        macd_line, signal_line, histogram = self.calculate_macd(df)
        df['macd'] = macd_line
        df['macd_signal'] = signal_line
        df['macd_histogram'] = histogram

        return df


if __name__ == "__main__":
    # Test with sample data
    print("Testing Technical Analyzer...\n")

    # Create sample price data
    dates = pd.date_range(start='2024-01-01', end='2024-12-20', freq='D')
    np.random.seed(42)

    # Simulate price data with trend
    prices = 40000 + np.cumsum(np.random.randn(len(dates)) * 1000)
    prices = np.maximum(prices, 10000)  # Keep prices positive

    df = pd.DataFrame({
        'close': prices,
        'open': prices * (1 + np.random.randn(len(dates)) * 0.01),
        'high': prices * (1 + np.abs(np.random.randn(len(dates))) * 0.02),
        'low': prices * (1 - np.abs(np.random.randn(len(dates))) * 0.02),
        'volume': np.random.randint(1000000, 10000000, len(dates))
    }, index=dates)

    # Analyze
    analyzer = TechnicalAnalyzer()
    results = analyzer.analyze(df)

    print("=== Technical Analysis Results ===\n")
    print(f"RSI: {results['rsi']['value']} ({results['rsi']['signal']})")
    print(f"  Recommendation: {results['rsi']['recommendation'].upper()}\n")

    print(f"MACD: {results['macd']['macd_line']}")
    print(f"Signal: {results['macd']['signal_line']}")
    print(f"Histogram: {results['macd']['histogram']}")
    print(f"  Signal: {results['macd']['signal']}")
    print(f"  Recommendation: {results['macd']['recommendation'].upper()}\n")

    print(f"Overall Recommendation: {results['overall']['recommendation'].upper()}")
    print(f"Confidence: {results['overall']['confidence'] * 100}%")
