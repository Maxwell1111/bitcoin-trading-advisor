"""
Comprehensive tests for RecommendationEngine
Tests the core business logic of combining signals and generating recommendations
"""

import pytest

from src.engine.recommendation import RecommendationEngine


class TestRecommendationEngineInitialization:
    """Test engine initialization and weight validation"""

    def test_default_weights(self):
        """Test default weight initialization"""
        engine = RecommendationEngine()
        assert engine.reddit_weight == 0.4
        assert engine.news_weight == 0.3
        assert engine.technical_weight == 0.3
        assert abs(engine.reddit_weight + engine.news_weight + engine.technical_weight - 1.0) < 0.01

    def test_custom_weights(self):
        """Test custom weight initialization"""
        engine = RecommendationEngine(reddit_weight=0.5, news_weight=0.2, technical_weight=0.3)
        assert engine.reddit_weight == 0.5
        assert engine.news_weight == 0.2
        assert engine.technical_weight == 0.3

    def test_weights_must_sum_to_one(self):
        """Test that weights must sum to 1.0"""
        with pytest.raises(ValueError, match="Weights must sum to 1.0"):
            RecommendationEngine(reddit_weight=0.5, news_weight=0.5, technical_weight=0.5)

    def test_weights_must_be_between_zero_and_one(self):
        """Test that weights must be between 0 and 1"""
        with pytest.raises(ValueError, match="Weights must be between 0 and 1"):
            RecommendationEngine(reddit_weight=-0.1, news_weight=0.6, technical_weight=0.5)

        with pytest.raises(ValueError, match="Weights must be between 0 and 1"):
            RecommendationEngine(reddit_weight=1.1, news_weight=0.0, technical_weight=-0.1)


class TestRecommendationScoring:
    """Test recommendation to score conversion"""

    def test_recommendation_to_score_buy(self):
        """Test 'buy' maps to score of 1.0"""
        engine = RecommendationEngine()
        assert engine._recommendation_to_score("buy") == 1.0
        assert engine._recommendation_to_score("BUY") == 1.0

    def test_recommendation_to_score_sell(self):
        """Test 'sell' maps to score of -1.0"""
        engine = RecommendationEngine()
        assert engine._recommendation_to_score("sell") == -1.0
        assert engine._recommendation_to_score("SELL") == -1.0

    def test_recommendation_to_score_hold(self):
        """Test 'hold' maps to score of 0.0"""
        engine = RecommendationEngine()
        assert engine._recommendation_to_score("hold") == 0.0
        assert engine._recommendation_to_score("HOLD") == 0.0

    def test_recommendation_to_score_unknown(self):
        """Test unknown recommendation defaults to 0.0"""
        engine = RecommendationEngine()
        assert engine._recommendation_to_score("unknown") == 0.0
        assert engine._recommendation_to_score("") == 0.0


class TestScoreToRecommendation:
    """Test score to recommendation conversion with confidence"""

    def test_strong_buy_threshold(self):
        """Test strong_buy recommendation for score >= 0.7"""
        engine = RecommendationEngine()
        rec, conf = engine._score_to_recommendation(0.7)
        assert rec == "strong_buy"
        assert conf == 0.7

        rec, conf = engine._score_to_recommendation(0.9)
        assert rec == "strong_buy"
        assert conf == 0.9

    def test_buy_threshold(self):
        """Test buy recommendation for 0.3 <= score < 0.7"""
        engine = RecommendationEngine()
        rec, conf = engine._score_to_recommendation(0.3)
        assert rec == "buy"
        assert conf == 0.3

        rec, conf = engine._score_to_recommendation(0.5)
        assert rec == "buy"
        assert conf == 0.5

    def test_hold_threshold(self):
        """Test hold recommendation for -0.3 < score < 0.3"""
        engine = RecommendationEngine()
        rec, conf = engine._score_to_recommendation(0.0)
        assert rec == "hold"
        assert conf == 1.0  # Hold has inverted confidence

        rec, conf = engine._score_to_recommendation(0.1)
        assert rec == "hold"
        assert 0.9 <= conf <= 1.0

        rec, conf = engine._score_to_recommendation(-0.2)
        assert rec == "hold"

    def test_sell_threshold(self):
        """Test sell recommendation for -0.7 < score <= -0.3"""
        engine = RecommendationEngine()
        rec, conf = engine._score_to_recommendation(-0.3)
        assert rec == "sell"
        assert conf == 0.3

        rec, conf = engine._score_to_recommendation(-0.5)
        assert rec == "sell"
        assert conf == 0.5

    def test_strong_sell_threshold(self):
        """Test strong_sell recommendation for score <= -0.7"""
        engine = RecommendationEngine()
        rec, conf = engine._score_to_recommendation(-0.7)
        assert rec == "strong_sell"
        assert conf == 0.7

        rec, conf = engine._score_to_recommendation(-0.9)
        assert rec == "strong_sell"
        assert conf == 0.9


class TestContrarianAlerts:
    """Test contrarian alert system for extreme sentiment"""

    def test_extreme_euphoria_alert(
        self, mock_technical_analysis, mock_sentiment_analysis, current_price, historical_data_dict
    ):
        """Test contrarian alert triggers at >0.85 sentiment"""
        engine = RecommendationEngine()

        # Create extreme euphoria sentiment
        euphoric_reddit = mock_sentiment_analysis.copy()
        euphoric_reddit["average_compound"] = 0.90  # Above 0.85 threshold

        result = engine.generate_recommendation(
            technical_analysis=mock_technical_analysis,
            news_sentiment_analysis=mock_sentiment_analysis,
            reddit_sentiment_analysis=euphoric_reddit,
            historical_data=historical_data_dict,
            current_price=current_price,
        )

        assert result["recommendation"] == "CONTRARIAN_ALERT"
        assert result["alert_type"] == "Extreme Euphoria"
        assert result["confidence"] == 1.0
        assert "unsustainably bullish" in result["reasoning"].lower()

    def test_extreme_fear_alert(
        self, mock_technical_analysis, mock_sentiment_analysis, current_price, historical_data_dict
    ):
        """Test contrarian alert triggers at <0.15 sentiment"""
        engine = RecommendationEngine()

        # Create extreme fear sentiment
        fearful_reddit = mock_sentiment_analysis.copy()
        fearful_reddit["average_compound"] = 0.10  # Below 0.15 threshold

        result = engine.generate_recommendation(
            technical_analysis=mock_technical_analysis,
            news_sentiment_analysis=mock_sentiment_analysis,
            reddit_sentiment_analysis=fearful_reddit,
            historical_data=historical_data_dict,
            current_price=current_price,
        )

        assert result["recommendation"] == "CONTRARIAN_ALERT"
        assert result["alert_type"] == "Extreme Fear"
        assert result["confidence"] == 1.0
        assert "maximum fear" in result["reasoning"].lower()

    def test_no_contrarian_alert_normal_sentiment(
        self, mock_technical_analysis, mock_sentiment_analysis, current_price, historical_data_dict
    ):
        """Test no contrarian alert for normal sentiment range"""
        engine = RecommendationEngine()

        # Normal sentiment (between 0.15 and 0.85)
        normal_reddit = mock_sentiment_analysis.copy()
        normal_reddit["average_compound"] = 0.50

        result = engine.generate_recommendation(
            technical_analysis=mock_technical_analysis,
            news_sentiment_analysis=mock_sentiment_analysis,
            reddit_sentiment_analysis=normal_reddit,
            historical_data=historical_data_dict,
            current_price=current_price,
        )

        assert result["recommendation"] != "CONTRARIAN_ALERT"


class TestWeightedRecommendation:
    """Test weighted combination of signals"""

    def test_all_signals_buy(self, mock_technical_analysis, current_price, historical_data_dict):
        """Test when all signals agree on buy"""
        engine = RecommendationEngine(reddit_weight=0.4, news_weight=0.3, technical_weight=0.3)

        # All bullish
        bullish_sentiment = {
            "recommendation": "buy",
            "confidence": 0.8,
            "average_compound": 0.6,
            "overall_sentiment": "positive",
        }

        result = engine.generate_recommendation(
            technical_analysis=mock_technical_analysis,  # Already bullish
            news_sentiment_analysis=bullish_sentiment,
            reddit_sentiment_analysis=bullish_sentiment,
            historical_data=historical_data_dict,
            current_price=current_price,
        )

        assert result["recommendation"] in ["buy", "strong_buy"]
        assert result["confidence"] > 0.6
        assert result["combined_score"] > 0.3

    def test_all_signals_sell(self, current_price, historical_data_dict):
        """Test when all signals agree on sell"""
        engine = RecommendationEngine()

        # All bearish
        bearish_technical = {
            "rsi": {"value": 75, "signal": "overbought", "recommendation": "sell"},
            "macd": {"signal": "bearish", "recommendation": "sell"},
            "ma_trend": {"recommendation": "sell"},
            "ma_crossovers": {"death_cross": True},
            "overall": {
                "recommendation": "sell",
                "confidence": 0.8,
                "buy_signals": 0,
                "sell_signals": 4,
            },
        }

        bearish_sentiment = {
            "recommendation": "sell",
            "confidence": 0.75,
            "average_compound": -0.4,
            "overall_sentiment": "negative",
        }

        result = engine.generate_recommendation(
            technical_analysis=bearish_technical,
            news_sentiment_analysis=bearish_sentiment,
            reddit_sentiment_analysis=bearish_sentiment,
            historical_data=historical_data_dict,
            current_price=current_price,
        )

        assert result["recommendation"] in ["sell", "strong_sell"]
        assert result["confidence"] > 0.6
        assert result["combined_score"] < -0.3

    def test_mixed_signals(self, current_price, historical_data_dict):
        """Test mixed signals result in hold or low confidence"""
        engine = RecommendationEngine(reddit_weight=0.4, news_weight=0.3, technical_weight=0.3)

        # Technical says buy
        bullish_technical = {
            "overall": {
                "recommendation": "buy",
                "confidence": 0.7,
                "buy_signals": 3,
                "sell_signals": 0,
            }
        }

        # Sentiment says sell
        bearish_sentiment = {
            "recommendation": "sell",
            "confidence": 0.7,
            "average_compound": -0.3,
            "overall_sentiment": "negative",
        }

        # News says hold
        neutral_news = {
            "recommendation": "hold",
            "confidence": 0.5,
            "average_compound": 0.0,
            "overall_sentiment": "neutral",
        }

        result = engine.generate_recommendation(
            technical_analysis=bullish_technical,
            news_sentiment_analysis=neutral_news,
            reddit_sentiment_analysis=bearish_sentiment,
            historical_data=historical_data_dict,
            current_price=current_price,
        )

        # With conflicting signals, confidence should be lower
        assert result["confidence"] < 0.8


class TestTargetCalculation:
    """Test target price calculations"""

    def test_buy_targets(self):
        """Test target calculation for buy recommendations"""
        engine = RecommendationEngine()
        current_price = 50000.0

        targets = engine._calculate_targets(current_price, "buy", 0.7)

        assert targets["entry"] == current_price
        assert targets["target_1"] > current_price
        assert targets["target_2"] > targets["target_1"]
        assert targets["stop_loss"] < current_price

        # Verify targets are reasonable (not too extreme)
        assert targets["target_1"] < current_price * 1.1
        assert targets["stop_loss"] > current_price * 0.9

    def test_sell_targets(self):
        """Test target calculation for sell recommendations"""
        engine = RecommendationEngine()
        current_price = 50000.0

        targets = engine._calculate_targets(current_price, "sell", 0.7)

        assert targets["entry"] == current_price
        assert targets["target_1"] < current_price
        assert targets["target_2"] < targets["target_1"]
        assert targets["stop_loss"] > current_price

    def test_hold_targets(self):
        """Test target calculation for hold recommendations"""
        engine = RecommendationEngine()
        current_price = 50000.0

        targets = engine._calculate_targets(current_price, "hold", 0.5)

        assert targets["entry"] == current_price
        assert "support" in targets
        assert "resistance" in targets
        assert targets["support"] < current_price
        assert targets["resistance"] > current_price

    def test_targets_scale_with_confidence(self):
        """Test that targets scale with confidence"""
        engine = RecommendationEngine()
        current_price = 50000.0

        targets_low_conf = engine._calculate_targets(current_price, "buy", 0.3)
        targets_high_conf = engine._calculate_targets(current_price, "buy", 0.9)

        # Higher confidence = larger targets
        assert (targets_high_conf["target_1"] - current_price) > (
            targets_low_conf["target_1"] - current_price
        )

    def test_targets_are_positive(self):
        """Test that all target prices are positive"""
        engine = RecommendationEngine()
        current_price = 1000.0  # Low price edge case

        for rec in ["buy", "sell", "hold"]:
            targets = engine._calculate_targets(current_price, rec, 0.7)
            for key, value in targets.items():
                assert value > 0, f"{key} should be positive, got {value}"


class TestResponseStructure:
    """Test that recommendation response has correct structure"""

    def test_response_contains_required_fields(
        self, mock_technical_analysis, mock_sentiment_analysis, current_price, historical_data_dict
    ):
        """Test that response contains all required fields"""
        engine = RecommendationEngine()

        result = engine.generate_recommendation(
            technical_analysis=mock_technical_analysis,
            news_sentiment_analysis=mock_sentiment_analysis,
            reddit_sentiment_analysis=mock_sentiment_analysis,
            historical_data=historical_data_dict,
            current_price=current_price,
        )

        # Top-level fields
        assert "recommendation" in result
        assert "confidence" in result
        assert "current_price" in result
        assert "signals" in result
        assert "targets" in result
        assert "reasoning" in result
        assert "timestamp" in result

        # Signals structure
        assert "technical" in result["signals"]
        assert "sentiment" in result["signals"]

        # Technical signal fields
        assert "recommendation" in result["signals"]["technical"]
        assert "confidence" in result["signals"]["technical"]
        assert "weight" in result["signals"]["technical"]

        # Sentiment signal fields
        assert "recommendation" in result["signals"]["sentiment"]
        assert "confidence" in result["signals"]["sentiment"]
        assert "weight" in result["signals"]["sentiment"]

    def test_confidence_is_between_zero_and_one(
        self, mock_technical_analysis, mock_sentiment_analysis, current_price, historical_data_dict
    ):
        """Test that confidence is always between 0 and 1"""
        engine = RecommendationEngine()

        result = engine.generate_recommendation(
            technical_analysis=mock_technical_analysis,
            news_sentiment_analysis=mock_sentiment_analysis,
            reddit_sentiment_analysis=mock_sentiment_analysis,
            historical_data=historical_data_dict,
            current_price=current_price,
        )

        assert 0.0 <= result["confidence"] <= 1.0

    def test_weights_sum_to_one_in_response(
        self, mock_technical_analysis, mock_sentiment_analysis, current_price, historical_data_dict
    ):
        """Test that reported weights sum to 1.0"""
        engine = RecommendationEngine(reddit_weight=0.4, news_weight=0.3, technical_weight=0.3)

        result = engine.generate_recommendation(
            technical_analysis=mock_technical_analysis,
            news_sentiment_analysis=mock_sentiment_analysis,
            reddit_sentiment_analysis=mock_sentiment_analysis,
            historical_data=historical_data_dict,
            current_price=current_price,
        )

        tech_weight = result["signals"]["technical"]["weight"]
        sent_weight = result["signals"]["sentiment"]["weight"]

        assert abs((tech_weight + sent_weight) - 1.0) < 0.01


class TestDivergenceDetection:
    """Test sentiment/price divergence detection"""

    def test_bearish_divergence_detected(
        self, mock_technical_analysis, mock_sentiment_analysis, current_price
    ):
        """Test bearish divergence: price high but sentiment low"""
        engine = RecommendationEngine()

        # Create data where price is at 30-day high
        historical_data = {"Close": [45000] * 28 + [49000, 50000]}  # Price at high

        # But sentiment is low
        low_sentiment = mock_sentiment_analysis.copy()
        low_sentiment["average_compound"] = 0.3  # Below 0.5

        result = engine.generate_recommendation(
            technical_analysis=mock_technical_analysis,
            news_sentiment_analysis=mock_sentiment_analysis,
            reddit_sentiment_analysis=low_sentiment,
            historical_data=historical_data,
            current_price=current_price,
        )

        assert "divergence_signal" in result
        assert "BEARISH DIVERGENCE" in result["divergence_signal"]

    def test_no_divergence_normal_conditions(
        self, mock_technical_analysis, mock_sentiment_analysis, current_price
    ):
        """Test no divergence under normal conditions"""
        engine = RecommendationEngine()

        # Price not at highs, sentiment normal
        historical_data = {"Close": [48000, 49000, 47000, 50000] * 8}

        result = engine.generate_recommendation(
            technical_analysis=mock_technical_analysis,
            news_sentiment_analysis=mock_sentiment_analysis,
            reddit_sentiment_analysis=mock_sentiment_analysis,
            historical_data=historical_data,
            current_price=current_price,
        )

        assert "divergence_signal" in result
        assert "No significant divergence" in result["divergence_signal"]


class TestFormatRecommendation:
    """Test human-readable formatting"""

    def test_format_buy_recommendation(
        self, mock_technical_analysis, mock_sentiment_analysis, current_price, historical_data_dict
    ):
        """Test formatting of buy recommendation"""
        engine = RecommendationEngine()

        result = engine.generate_recommendation(
            technical_analysis=mock_technical_analysis,
            news_sentiment_analysis=mock_sentiment_analysis,
            reddit_sentiment_analysis=mock_sentiment_analysis,
            historical_data=historical_data_dict,
            current_price=current_price,
        )

        formatted = engine.format_recommendation(result)

        assert isinstance(formatted, str)
        assert "BITCOIN PORTFOLIO ADVISOR" in formatted
        assert "RECOMMENDATION" in formatted
        assert "DISCLAIMER" in formatted.upper()

    def test_format_contrarian_alert(self):
        """Test formatting of contrarian alert"""
        engine = RecommendationEngine()

        contrarian_result = {
            "recommendation": "CONTRARIAN_ALERT",
            "alert_type": "Extreme Euphoria",
            "confidence": 1.0,
            "reasoning": "Market sentiment unsustainably bullish",
            "current_price": 50000,
            "timestamp": "2024-01-10T12:00:00",
        }

        formatted = engine.format_recommendation(contrarian_result)

        assert "CONTRARIAN_ALERT" in formatted or "EXTREME EUPHORIA" in formatted
        assert "unsustainably bullish" in formatted.lower()


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_zero_confidence_signals(self, current_price, historical_data_dict):
        """Test handling of zero confidence signals"""
        engine = RecommendationEngine()

        zero_conf_technical = {
            "overall": {
                "recommendation": "hold",
                "confidence": 0.0,
                "buy_signals": 0,
                "sell_signals": 0,
            }
        }

        zero_conf_sentiment = {
            "recommendation": "hold",
            "confidence": 0.0,
            "average_compound": 0.0,
            "overall_sentiment": "neutral",
        }

        result = engine.generate_recommendation(
            technical_analysis=zero_conf_technical,
            news_sentiment_analysis=zero_conf_sentiment,
            reddit_sentiment_analysis=zero_conf_sentiment,
            historical_data=historical_data_dict,
            current_price=current_price,
        )

        assert result["recommendation"] == "hold"
        assert 0.0 <= result["confidence"] <= 1.0

    def test_very_low_price(
        self, mock_technical_analysis, mock_sentiment_analysis, historical_data_dict
    ):
        """Test with very low Bitcoin price"""
        engine = RecommendationEngine()
        low_price = 100.0

        result = engine.generate_recommendation(
            technical_analysis=mock_technical_analysis,
            news_sentiment_analysis=mock_sentiment_analysis,
            reddit_sentiment_analysis=mock_sentiment_analysis,
            historical_data=historical_data_dict,
            current_price=low_price,
        )

        assert result["current_price"] == low_price
        assert all(v > 0 for v in result["targets"].values())

    def test_very_high_price(
        self, mock_technical_analysis, mock_sentiment_analysis, historical_data_dict
    ):
        """Test with very high Bitcoin price"""
        engine = RecommendationEngine()
        high_price = 1000000.0

        result = engine.generate_recommendation(
            technical_analysis=mock_technical_analysis,
            news_sentiment_analysis=mock_sentiment_analysis,
            reddit_sentiment_analysis=mock_sentiment_analysis,
            historical_data=historical_data_dict,
            current_price=high_price,
        )

        assert result["current_price"] == high_price
        assert all(v > 0 for v in result["targets"].values())

    def test_minimal_historical_data(
        self, mock_technical_analysis, mock_sentiment_analysis, current_price
    ):
        """Test with minimal historical data"""
        engine = RecommendationEngine()

        # Only 5 days of data
        minimal_data = {"Close": [48000, 49000, 50000, 49500, 50000]}

        result = engine.generate_recommendation(
            technical_analysis=mock_technical_analysis,
            news_sentiment_analysis=mock_sentiment_analysis,
            reddit_sentiment_analysis=mock_sentiment_analysis,
            historical_data=minimal_data,
            current_price=current_price,
        )

        # Should still generate a recommendation
        assert "recommendation" in result
        assert "confidence" in result
