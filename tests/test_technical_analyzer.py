"""
Comprehensive tests for TechnicalAnalyzer
Tests RSI, MACD, moving averages, and crossover detection
"""

import numpy as np
import pandas as pd

from src.analysis.technical import TechnicalAnalyzer


class TestTechnicalAnalyzerInitialization:
    """Test analyzer initialization"""

    def test_default_initialization(self):
        """Test default parameter initialization"""
        analyzer = TechnicalAnalyzer()
        assert analyzer.rsi_period == 14
        assert analyzer.macd_fast == 12
        assert analyzer.macd_slow == 26
        assert analyzer.macd_signal == 9
        assert 20 in analyzer.sma_periods
        assert 50 in analyzer.sma_periods
        assert 200 in analyzer.sma_periods

    def test_custom_parameters(self):
        """Test custom parameter initialization"""
        analyzer = TechnicalAnalyzer(rsi_period=21, macd_fast=8, macd_slow=21, sma_periods=[10, 30])
        assert analyzer.rsi_period == 21
        assert analyzer.macd_fast == 8
        assert analyzer.macd_slow == 21
        assert analyzer.sma_periods == [10, 30]


class TestRSICalculation:
    """Test RSI (Relative Strength Index) calculation"""

    def test_rsi_calculation_basic(self, sample_price_data):
        """Test basic RSI calculation"""
        analyzer = TechnicalAnalyzer()
        rsi = analyzer.calculate_rsi(sample_price_data)

        assert isinstance(rsi, pd.Series)
        assert len(rsi) == len(sample_price_data)

        # RSI should be between 0 and 100
        assert rsi.dropna().min() >= 0
        assert rsi.dropna().max() <= 100

    def test_rsi_overbought_condition(self):
        """Test RSI calculation with strong uptrend (overbought)"""
        # Create data with strong uptrend
        dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
        prices = np.linspace(40000, 60000, 30)  # Clear uptrend

        df = pd.DataFrame(
            {
                "close": prices,
                "open": prices,
                "high": prices * 1.01,
                "low": prices * 0.99,
                "volume": [1000000] * 30,
            },
            index=dates,
        )

        analyzer = TechnicalAnalyzer()
        rsi = analyzer.calculate_rsi(df)

        # In strong uptrend, RSI should trend toward overbought (>70)
        final_rsi = rsi.iloc[-1]
        assert final_rsi > 50  # At minimum, should be above neutral

    def test_rsi_oversold_condition(self):
        """Test RSI calculation with strong downtrend (oversold)"""
        # Create data with strong downtrend
        dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
        prices = np.linspace(60000, 40000, 30)  # Clear downtrend

        df = pd.DataFrame(
            {
                "close": prices,
                "open": prices,
                "high": prices * 1.01,
                "low": prices * 0.99,
                "volume": [1000000] * 30,
            },
            index=dates,
        )

        analyzer = TechnicalAnalyzer()
        rsi = analyzer.calculate_rsi(df)

        # In strong downtrend, RSI should trend toward oversold (<30)
        final_rsi = rsi.iloc[-1]
        assert final_rsi < 50  # At minimum, should be below neutral

    def test_rsi_with_minimal_data(self):
        """Test RSI calculation with minimal data points"""
        dates = pd.date_range(start="2024-01-01", periods=15, freq="D")
        prices = np.random.randint(45000, 55000, 15)

        df = pd.DataFrame(
            {
                "close": prices,
                "open": prices,
                "high": prices * 1.01,
                "low": prices * 0.99,
                "volume": [1000000] * 15,
            },
            index=dates,
        )

        analyzer = TechnicalAnalyzer(rsi_period=14)
        rsi = analyzer.calculate_rsi(df)

        # Should still calculate RSI
        assert len(rsi) == 15
        assert not rsi.isna().all()


class TestMACDCalculation:
    """Test MACD (Moving Average Convergence Divergence) calculation"""

    def test_macd_calculation_basic(self, sample_price_data):
        """Test basic MACD calculation"""
        analyzer = TechnicalAnalyzer()
        macd_line, signal_line, histogram = analyzer.calculate_macd(sample_price_data)

        assert isinstance(macd_line, pd.Series)
        assert isinstance(signal_line, pd.Series)
        assert isinstance(histogram, pd.Series)
        assert len(macd_line) == len(sample_price_data)
        assert len(signal_line) == len(sample_price_data)
        assert len(histogram) == len(sample_price_data)

    def test_macd_histogram_calculation(self, sample_price_data):
        """Test that histogram equals MACD line minus signal line"""
        analyzer = TechnicalAnalyzer()
        macd_line, signal_line, histogram = analyzer.calculate_macd(sample_price_data)

        # Histogram = MACD - Signal
        expected_histogram = macd_line - signal_line
        pd.testing.assert_series_equal(histogram, expected_histogram)

    def test_macd_bullish_signal(self, bullish_price_data):
        """Test MACD in bullish conditions"""
        analyzer = TechnicalAnalyzer()
        macd_line, signal_line, histogram = analyzer.calculate_macd(bullish_price_data)

        # In uptrend, MACD should eventually be above signal line
        final_macd = macd_line.iloc[-1]
        final_signal = signal_line.iloc[-1]

        assert final_macd > final_signal or abs(final_macd - final_signal) < 100

    def test_macd_bearish_signal(self, bearish_price_data):
        """Test MACD in bearish conditions"""
        analyzer = TechnicalAnalyzer()
        macd_line, signal_line, histogram = analyzer.calculate_macd(bearish_price_data)

        # In downtrend, MACD should eventually be below signal line
        final_macd = macd_line.iloc[-1]
        final_signal = signal_line.iloc[-1]

        assert final_macd < final_signal or abs(final_macd - final_signal) < 100


class TestMovingAverages:
    """Test SMA and EMA calculations"""

    def test_sma_calculation(self, sample_price_data):
        """Test Simple Moving Average calculation"""
        analyzer = TechnicalAnalyzer()
        sma_20 = analyzer.calculate_sma(sample_price_data, period=20)

        assert isinstance(sma_20, pd.Series)
        assert len(sma_20) == len(sample_price_data)

        # First 19 values should be NaN
        assert sma_20.iloc[:19].isna().all()

        # After period 20, should have values
        assert not sma_20.iloc[20:].isna().all()

    def test_ema_calculation(self, sample_price_data):
        """Test Exponential Moving Average calculation"""
        analyzer = TechnicalAnalyzer()
        ema_20 = analyzer.calculate_ema(sample_price_data, period=20)

        assert isinstance(ema_20, pd.Series)
        assert len(ema_20) == len(sample_price_data)
        assert not ema_20.isna().all()

    def test_sma_vs_ema_responsiveness(self):
        """Test that EMA responds faster than SMA to price changes"""
        # Create data with sudden price jump
        dates = pd.date_range(start="2024-01-01", periods=50, freq="D")
        prices = [50000] * 25 + [55000] * 25  # Sudden 10% jump

        df = pd.DataFrame(
            {
                "close": prices,
                "open": prices,
                "high": prices,
                "low": prices,
                "volume": [1000000] * 50,
            },
            index=dates,
        )

        analyzer = TechnicalAnalyzer()
        sma_20 = analyzer.calculate_sma(df, period=20)
        ema_20 = analyzer.calculate_ema(df, period=20)

        # After the jump, EMA should respond faster
        sma_after_jump = sma_20.iloc[30]
        ema_after_jump = ema_20.iloc[30]

        # EMA should be closer to current price than SMA
        assert abs(ema_after_jump - 55000) < abs(sma_after_jump - 55000)

    def test_calculate_moving_averages_dict(self, sample_price_data):
        """Test calculation of multiple moving averages"""
        analyzer = TechnicalAnalyzer(sma_periods=[20, 50], ema_periods=[9, 21])
        mas = analyzer.calculate_moving_averages(sample_price_data)

        assert "sma_20" in mas
        assert "sma_50" in mas
        assert "ema_9" in mas
        assert "ema_21" in mas

        # Check structure
        assert "value" in mas["sma_20"]
        assert "period" in mas["sma_20"]
        assert "price_vs_ma" in mas["sma_20"]
        assert mas["sma_20"]["price_vs_ma"] in ["above", "below"]


class TestCrossoverDetection:
    """Test moving average crossover detection"""

    def test_golden_cross_detection(self):
        """Test Golden Cross (50 SMA crosses above 200 SMA)"""
        dates = pd.date_range(start="2024-01-01", periods=250, freq="D")

        # Create price pattern that causes golden cross
        # Downtrend, then strong uptrend
        prices = list(np.linspace(60000, 40000, 100)) + list(np.linspace(40000, 70000, 150))

        df = pd.DataFrame(
            {
                "close": prices,
                "open": prices,
                "high": prices,
                "low": prices,
                "volume": [1000000] * 250,
            },
            index=dates,
        )

        analyzer = TechnicalAnalyzer()
        crossovers = analyzer.detect_ma_crossovers(df)

        # Should detect that 50 SMA is above 200 SMA (golden cross happened)
        assert "sma_50_vs_200" in crossovers
        assert crossovers["sma_50_vs_200"] == "above"

    def test_death_cross_detection(self):
        """Test Death Cross (50 SMA crosses below 200 SMA)"""
        dates = pd.date_range(start="2024-01-01", periods=250, freq="D")

        # Create price pattern that causes death cross
        # Uptrend, then strong downtrend
        prices = list(np.linspace(40000, 70000, 100)) + list(np.linspace(70000, 40000, 150))

        df = pd.DataFrame(
            {
                "close": prices,
                "open": prices,
                "high": prices,
                "low": prices,
                "volume": [1000000] * 250,
            },
            index=dates,
        )

        analyzer = TechnicalAnalyzer()
        crossovers = analyzer.detect_ma_crossovers(df)

        # Should detect that 50 SMA is below 200 SMA (death cross happened)
        assert "sma_50_vs_200" in crossovers
        assert crossovers["sma_50_vs_200"] == "below"

    def test_short_term_crossover_detection(self, long_price_data):
        """Test short-term EMA crossover (9 EMA vs 21 EMA)"""
        analyzer = TechnicalAnalyzer()
        crossovers = analyzer.detect_ma_crossovers(long_price_data)

        assert "ema_9_vs_21" in crossovers
        assert crossovers["ema_9_vs_21"] in ["above", "below"]

    def test_crossover_with_insufficient_data(self, sample_price_data):
        """Test crossover detection with insufficient data for 200 SMA"""
        # sample_price_data only has 100 days, not enough for 200 SMA
        analyzer = TechnicalAnalyzer()
        crossovers = analyzer.detect_ma_crossovers(sample_price_data)

        # Should not have golden_cross/death_cross keys if insufficient data
        # Or should handle gracefully
        assert isinstance(crossovers, dict)


class TestTrendAnalysis:
    """Test overall trend analysis"""

    def test_uptrend_detection(self, bullish_price_data):
        """Test detection of uptrend"""
        analyzer = TechnicalAnalyzer()
        trend = analyzer.analyze_ma_trend(bullish_price_data)

        assert trend["overall_trend"] in ["uptrend", "strong_uptrend"]
        assert trend["recommendation"] == "buy"
        assert trend["bullish_signals"] > trend["bearish_signals"]
        assert trend["bullish_ratio"] > 0.5

    def test_downtrend_detection(self, bearish_price_data):
        """Test detection of downtrend"""
        analyzer = TechnicalAnalyzer()
        trend = analyzer.analyze_ma_trend(bearish_price_data)

        assert trend["overall_trend"] == "downtrend"
        assert trend["recommendation"] == "sell"
        assert trend["bullish_signals"] < trend["bearish_signals"]
        assert trend["bullish_ratio"] < 0.5

    def test_neutral_trend_detection(self):
        """Test detection of neutral/sideways trend"""
        dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
        # Sideways movement
        prices = 50000 + np.sin(np.linspace(0, 4 * np.pi, 100)) * 2000

        df = pd.DataFrame(
            {
                "close": prices,
                "open": prices,
                "high": prices * 1.01,
                "low": prices * 0.99,
                "volume": [1000000] * 100,
            },
            index=dates,
        )

        analyzer = TechnicalAnalyzer()
        trend = analyzer.analyze_ma_trend(df)

        assert trend["overall_trend"] in ["neutral", "uptrend", "downtrend"]
        assert "bullish_ratio" in trend
        assert 0.0 <= trend["bullish_ratio"] <= 1.0


class TestFullAnalysis:
    """Test complete technical analysis"""

    def test_full_analysis_structure(self, sample_price_data):
        """Test that full analysis returns correct structure"""
        analyzer = TechnicalAnalyzer()
        results = analyzer.analyze(sample_price_data)

        # Check top-level keys
        assert "rsi" in results
        assert "macd" in results
        assert "moving_averages" in results
        assert "ma_crossovers" in results
        assert "ma_trend" in results
        assert "overall" in results

        # Check RSI structure
        assert "value" in results["rsi"]
        assert "signal" in results["rsi"]
        assert "recommendation" in results["rsi"]

        # Check MACD structure
        assert "macd_line" in results["macd"]
        assert "signal_line" in results["macd"]
        assert "histogram" in results["macd"]
        assert "signal" in results["macd"]
        assert "recommendation" in results["macd"]

        # Check overall structure
        assert "recommendation" in results["overall"]
        assert "confidence" in results["overall"]
        assert "buy_signals" in results["overall"]
        assert "sell_signals" in results["overall"]

    def test_rsi_signal_classification(self, sample_price_data):
        """Test RSI signal classification"""
        analyzer = TechnicalAnalyzer()
        results = analyzer.analyze(sample_price_data)

        rsi_value = results["rsi"]["value"]
        rsi_signal = results["rsi"]["signal"]

        if rsi_value > 70:
            assert rsi_signal == "overbought"
            assert results["rsi"]["recommendation"] == "sell"
        elif rsi_value < 30:
            assert rsi_signal == "oversold"
            assert results["rsi"]["recommendation"] == "buy"
        else:
            assert rsi_signal == "neutral"
            assert results["rsi"]["recommendation"] == "hold"

    def test_macd_signal_classification(self, sample_price_data):
        """Test MACD signal classification"""
        analyzer = TechnicalAnalyzer()
        results = analyzer.analyze(sample_price_data)

        macd_signal = results["macd"]["signal"]
        macd_rec = results["macd"]["recommendation"]

        if "bullish" in macd_signal:
            assert macd_rec == "buy"
        elif "bearish" in macd_signal:
            assert macd_rec == "sell"
        else:
            assert macd_rec == "hold"

    def test_overall_recommendation_logic(self, bullish_price_data):
        """Test overall recommendation combines signals correctly"""
        analyzer = TechnicalAnalyzer()
        results = analyzer.analyze(bullish_price_data)

        buy_signals = results["overall"]["buy_signals"]
        sell_signals = results["overall"]["sell_signals"]
        recommendation = results["overall"]["recommendation"]

        if buy_signals > sell_signals:
            assert recommendation == "buy"
        elif sell_signals > buy_signals:
            assert recommendation == "sell"
        else:
            assert recommendation == "hold"

    def test_confidence_calculation(self, sample_price_data):
        """Test confidence calculation is reasonable"""
        analyzer = TechnicalAnalyzer()
        results = analyzer.analyze(sample_price_data)

        confidence = results["overall"]["confidence"]

        # Confidence should be between 0 and 1
        assert 0.0 <= confidence <= 1.0

        # Confidence should relate to signal strength
        buy_signals = results["overall"]["buy_signals"]
        sell_signals = results["overall"]["sell_signals"]
        total_indicators = results["overall"]["total_indicators"]

        if buy_signals > 0 or sell_signals > 0:
            expected_conf = max(buy_signals, sell_signals) / total_indicators
            assert abs(confidence - expected_conf) < 0.1


class TestAddIndicatorsToDataframe:
    """Test adding indicators as DataFrame columns"""

    def test_add_indicators(self, sample_price_data):
        """Test adding all indicators to DataFrame"""
        analyzer = TechnicalAnalyzer()
        df = analyzer.add_indicators_to_dataframe(sample_price_data)

        assert "rsi" in df.columns
        assert "macd" in df.columns
        assert "macd_signal" in df.columns
        assert "macd_histogram" in df.columns
        assert len(df) == len(sample_price_data)

    def test_original_data_preserved(self, sample_price_data):
        """Test that original DataFrame is not modified"""
        analyzer = TechnicalAnalyzer()
        original_columns = sample_price_data.columns.tolist()

        analyzer.add_indicators_to_dataframe(sample_price_data)

        # Original DataFrame should be unchanged
        assert sample_price_data.columns.tolist() == original_columns
        assert "rsi" not in sample_price_data.columns


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_single_price_point(self):
        """Test with single data point"""
        df = pd.DataFrame(
            {
                "close": [50000],
                "open": [49000],
                "high": [51000],
                "low": [48000],
                "volume": [1000000],
            }
        )

        analyzer = TechnicalAnalyzer()

        # Should handle gracefully, even if indicators are NaN
        rsi = analyzer.calculate_rsi(df)
        assert len(rsi) == 1

    def test_flat_prices(self):
        """Test with completely flat prices (no movement)"""
        dates = pd.date_range(start="2024-01-01", periods=50, freq="D")
        prices = [50000] * 50  # No price movement

        df = pd.DataFrame(
            {
                "close": prices,
                "open": prices,
                "high": prices,
                "low": prices,
                "volume": [1000000] * 50,
            },
            index=dates,
        )

        analyzer = TechnicalAnalyzer()
        results = analyzer.analyze(df)

        # Should still return valid structure
        assert "overall" in results
        assert "recommendation" in results["overall"]

    def test_extreme_volatility(self):
        """Test with extreme price volatility"""
        dates = pd.date_range(start="2024-01-01", periods=50, freq="D")
        # Alternating extreme moves
        prices = [50000, 40000, 55000, 35000, 60000] * 10

        df = pd.DataFrame(
            {
                "close": prices,
                "open": prices,
                "high": [p * 1.1 for p in prices],
                "low": [p * 0.9 for p in prices],
                "volume": [1000000] * 50,
            },
            index=dates,
        )

        analyzer = TechnicalAnalyzer()
        results = analyzer.analyze(df)

        # Should handle without crashing
        assert "overall" in results
        assert 0.0 <= results["overall"]["confidence"] <= 1.0

    def test_negative_prices(self):
        """Test that negative prices are handled (shouldn't happen in reality)"""
        dates = pd.date_range(start="2024-01-01", periods=50, freq="D")
        prices = np.linspace(-1000, 1000, 50)  # Including negative

        df = pd.DataFrame(
            {
                "close": prices,
                "open": prices,
                "high": prices,
                "low": prices,
                "volume": [1000000] * 50,
            },
            index=dates,
        )

        analyzer = TechnicalAnalyzer()

        # Should either handle gracefully or raise clear error
        try:
            results = analyzer.analyze(df)
            assert "overall" in results
        except (ValueError, ZeroDivisionError):
            # Acceptable to raise error for invalid data
            pass
