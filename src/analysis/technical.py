"""
Technical analysis module - RSI, MACD, and Moving Averages
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, List


class TechnicalAnalyzer:
    """Calculate technical indicators (RSI, MACD, Moving Averages)"""

    def __init__(self, rsi_period: int = 14, macd_fast: int = 12,
                 macd_slow: int = 26, macd_signal: int = 9,
                 sma_periods: List[int] = None, ema_periods: List[int] = None):
        """
        Initialize technical analyzer

        Args:
            rsi_period: RSI calculation period (default: 14)
            macd_fast: MACD fast EMA period (default: 12)
            macd_slow: MACD slow EMA period (default: 26)
            macd_signal: MACD signal line period (default: 9)
            sma_periods: SMA periods to calculate (default: [20, 50, 100, 200])
            ema_periods: EMA periods to calculate (default: [9, 20, 21, 50, 100, 147, 200])
                         Note: 147 days = 21 weeks (Bull Market Support Band)
        """
        self.rsi_period = rsi_period
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.sma_periods = sma_periods or [20, 50, 100, 200]
        self.ema_periods = ema_periods or [9, 20, 21, 50, 100, 147, 200]  # Added 20, 147 (21-week)

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

    def calculate_sma(self, data: pd.DataFrame, period: int, column: str = 'close') -> pd.Series:
        """
        Calculate Simple Moving Average (SMA)

        Args:
            data: DataFrame with price data
            period: Period for SMA calculation
            column: Column name to calculate SMA on

        Returns:
            Series with SMA values
        """
        return data[column].rolling(window=period).mean()

    def calculate_ema(self, data: pd.DataFrame, period: int, column: str = 'close') -> pd.Series:
        """
        Calculate Exponential Moving Average (EMA)

        Args:
            data: DataFrame with price data
            period: Period for EMA calculation
            column: Column name to calculate EMA on

        Returns:
            Series with EMA values
        """
        return data[column].ewm(span=period, adjust=False).mean()

    def calculate_moving_averages(self, data: pd.DataFrame) -> Dict:
        """
        Calculate multiple SMAs and EMAs

        Args:
            data: DataFrame with OHLCV data

        Returns:
            Dictionary with all moving averages
        """
        current_price = data['close'].iloc[-1]
        mas = {}

        # Calculate SMAs
        for period in self.sma_periods:
            if len(data) >= period:
                sma = self.calculate_sma(data, period)
                mas[f'sma_{period}'] = {
                    'value': round(sma.iloc[-1], 2),
                    'period': period,
                    'type': 'SMA',
                    'price_vs_ma': 'above' if current_price > sma.iloc[-1] else 'below',
                    'distance_pct': round(((current_price / sma.iloc[-1]) - 1) * 100, 2)
                }

        # Calculate EMAs
        for period in self.ema_periods:
            if len(data) >= period:
                ema = self.calculate_ema(data, period)
                mas[f'ema_{period}'] = {
                    'value': round(ema.iloc[-1], 2),
                    'period': period,
                    'type': 'EMA',
                    'price_vs_ma': 'above' if current_price > ema.iloc[-1] else 'below',
                    'distance_pct': round(((current_price / ema.iloc[-1]) - 1) * 100, 2)
                }

        return mas

    def detect_ma_crossovers(self, data: pd.DataFrame) -> Dict:
        """
        Detect moving average crossovers (Golden Cross, Death Cross, etc.)

        Args:
            data: DataFrame with OHLCV data

        Returns:
            Dictionary with crossover signals
        """
        crossovers = {}

        # Golden Cross / Death Cross (50 SMA vs 200 SMA)
        if len(data) >= 200:
            sma_50 = self.calculate_sma(data, 50)
            sma_200 = self.calculate_sma(data, 200)

            current_50 = sma_50.iloc[-1]
            current_200 = sma_200.iloc[-1]
            prev_50 = sma_50.iloc[-2] if len(sma_50) > 1 else current_50
            prev_200 = sma_200.iloc[-2] if len(sma_200) > 1 else current_200

            if prev_50 <= prev_200 and current_50 > current_200:
                crossovers['golden_cross'] = True
                crossovers['golden_cross_signal'] = 'Strong Bullish - Golden Cross detected!'
            elif prev_50 >= prev_200 and current_50 < current_200:
                crossovers['death_cross'] = True
                crossovers['death_cross_signal'] = 'Strong Bearish - Death Cross detected!'
            else:
                crossovers['golden_cross'] = False
                crossovers['death_cross'] = False

            crossovers['sma_50_vs_200'] = 'above' if current_50 > current_200 else 'below'

        # Short-term crossover (9 EMA vs 21 EMA)
        if len(data) >= 21:
            ema_9 = self.calculate_ema(data, 9)
            ema_21 = self.calculate_ema(data, 21)

            current_9 = ema_9.iloc[-1]
            current_21 = ema_21.iloc[-1]
            prev_9 = ema_9.iloc[-2] if len(ema_9) > 1 else current_9
            prev_21 = ema_21.iloc[-2] if len(ema_21) > 1 else current_21

            if prev_9 <= prev_21 and current_9 > current_21:
                crossovers['short_term_bullish_cross'] = True
            elif prev_9 >= prev_21 and current_9 < current_21:
                crossovers['short_term_bearish_cross'] = True
            else:
                crossovers['short_term_bullish_cross'] = False
                crossovers['short_term_bearish_cross'] = False

            crossovers['ema_9_vs_21'] = 'above' if current_9 > current_21 else 'below'

        return crossovers

    def analyze_ma_trend(self, data: pd.DataFrame) -> Dict:
        """
        Analyze overall trend based on moving averages

        Args:
            data: DataFrame with OHLCV data

        Returns:
            Dictionary with trend analysis
        """
        current_price = data['close'].iloc[-1]
        trend_signals = []
        bullish_count = 0
        bearish_count = 0

        # Check price vs key moving averages
        ma_checks = [
            (20, 'short'),
            (50, 'medium'),
            (200, 'long')
        ]

        trend_analysis = {}

        for period, term in ma_checks:
            if len(data) >= period:
                sma = self.calculate_sma(data, period)
                ema = self.calculate_ema(data, period)

                sma_val = sma.iloc[-1]
                ema_val = ema.iloc[-1]

                if current_price > sma_val:
                    bullish_count += 1
                    trend_signals.append(f"Above {period}-day SMA")
                else:
                    bearish_count += 1
                    trend_signals.append(f"Below {period}-day SMA")

                if current_price > ema_val:
                    bullish_count += 1
                else:
                    bearish_count += 1

                trend_analysis[f'{term}_term'] = {
                    'sma': sma_val,
                    'ema': ema_val,
                    'price_vs_sma': 'above' if current_price > sma_val else 'below',
                    'price_vs_ema': 'above' if current_price > ema_val else 'below'
                }

        # Overall trend determination
        total_signals = bullish_count + bearish_count
        if total_signals > 0:
            bullish_ratio = bullish_count / total_signals

            if bullish_ratio >= 0.7:
                overall_trend = 'strong_uptrend'
                recommendation = 'buy'
            elif bullish_ratio >= 0.5:
                overall_trend = 'uptrend'
                recommendation = 'buy'
            elif bullish_ratio >= 0.3:
                overall_trend = 'neutral'
                recommendation = 'hold'
            else:
                overall_trend = 'downtrend'
                recommendation = 'sell'
        else:
            overall_trend = 'neutral'
            recommendation = 'hold'

        return {
            'overall_trend': overall_trend,
            'recommendation': recommendation,
            'bullish_signals': bullish_count,
            'bearish_signals': bearish_count,
            'bullish_ratio': round(bullish_ratio, 2) if total_signals > 0 else 0.5,
            'trend_details': trend_analysis
        }

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

        # Calculate moving averages
        moving_averages = self.calculate_moving_averages(data)
        ma_crossovers = self.detect_ma_crossovers(data)
        ma_trend = self.analyze_ma_trend(data)

        # Combined technical signal (now including MA analysis)
        buy_signals = sum([
            rsi_recommendation == "buy",
            macd_recommendation == "buy",
            ma_trend['recommendation'] == "buy",
            ma_crossovers.get('golden_cross', False),
            ma_crossovers.get('short_term_bullish_cross', False)
        ])
        sell_signals = sum([
            rsi_recommendation == "sell",
            macd_recommendation == "sell",
            ma_trend['recommendation'] == "sell",
            ma_crossovers.get('death_cross', False),
            ma_crossovers.get('short_term_bearish_cross', False)
        ])

        total_indicators = 5  # RSI, MACD, MA trend, long-term crossover, short-term crossover

        if buy_signals > sell_signals:
            overall_recommendation = "buy"
            confidence = buy_signals / total_indicators
        elif sell_signals > buy_signals:
            overall_recommendation = "sell"
            confidence = sell_signals / total_indicators
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
            'moving_averages': moving_averages,
            'ma_crossovers': ma_crossovers,
            'ma_trend': ma_trend,
            'overall': {
                'recommendation': overall_recommendation,
                'confidence': round(confidence, 2),
                'buy_signals': buy_signals,
                'sell_signals': sell_signals,
                'total_indicators': total_indicators
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
