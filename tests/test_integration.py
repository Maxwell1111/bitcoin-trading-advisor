"""
Integration tests for the complete recommendation flow
Tests end-to-end scenarios with mocked external dependencies
"""

from datetime import datetime

import numpy as np
import pandas as pd

from src.analysis.sentiment import SentimentAnalyzer
from src.analysis.technical import TechnicalAnalyzer
from src.engine.recommendation import RecommendationEngine


class TestRecommendationFlow:
    """Test complete recommendation generation flow"""

    def test_full_recommendation_flow_bullish(
        self, bullish_price_data, positive_articles, current_price
    ):
        """Test complete flow with bullish signals"""
        # Technical analysis
        tech_analyzer = TechnicalAnalyzer()
        technical_results = tech_analyzer.analyze(bullish_price_data)

        # Sentiment analysis
        sent_analyzer = SentimentAnalyzer()
        sentiment_results = sent_analyzer.analyze_articles(positive_articles)

        # Generate recommendation
        engine = RecommendationEngine()
        recommendation = engine.generate_recommendation(
            technical_analysis=technical_results,
            news_sentiment_analysis=sentiment_results,
            reddit_sentiment_analysis=sentiment_results,
            historical_data={"Close": bullish_price_data["close"].tolist()},
            current_price=current_price,
        )

        # Verify bullish recommendation
        assert recommendation["recommendation"] in ["buy", "strong_buy"]
        assert recommendation["confidence"] > 0.5
        assert recommendation["current_price"] == current_price

    def test_full_recommendation_flow_bearish(
        self, bearish_price_data, negative_articles, current_price
    ):
        """Test complete flow with bearish signals"""
        # Technical analysis
        tech_analyzer = TechnicalAnalyzer()
        technical_results = tech_analyzer.analyze(bearish_price_data)

        # Sentiment analysis
        sent_analyzer = SentimentAnalyzer()
        sentiment_results = sent_analyzer.analyze_articles(negative_articles)

        # Generate recommendation
        engine = RecommendationEngine()
        recommendation = engine.generate_recommendation(
            technical_analysis=technical_results,
            news_sentiment_analysis=sentiment_results,
            reddit_sentiment_analysis=sentiment_results,
            historical_data={"Close": bearish_price_data["close"].tolist()},
            current_price=current_price,
        )

        # Verify bearish recommendation
        assert recommendation["recommendation"] in ["sell", "strong_sell"]
        assert recommendation["confidence"] > 0.4

    def test_full_recommendation_flow_mixed_signals(
        self, bullish_price_data, negative_articles, current_price
    ):
        """Test flow with conflicting signals (bullish technical, bearish sentiment)"""
        # Technical analysis (bullish)
        tech_analyzer = TechnicalAnalyzer()
        technical_results = tech_analyzer.analyze(bullish_price_data)

        # Sentiment analysis (bearish)
        sent_analyzer = SentimentAnalyzer()
        sentiment_results = sent_analyzer.analyze_articles(negative_articles)

        # Generate recommendation
        engine = RecommendationEngine()
        recommendation = engine.generate_recommendation(
            technical_analysis=technical_results,
            news_sentiment_analysis=sentiment_results,
            reddit_sentiment_analysis=sentiment_results,
            historical_data={"Close": bullish_price_data["close"].tolist()},
            current_price=current_price,
        )

        # With conflicting signals, recommendation should exist but with moderate confidence
        assert recommendation["recommendation"] in ["buy", "sell", "hold"]
        assert 0.0 <= recommendation["confidence"] <= 1.0


class TestWeightedScenarios:
    """Test different weighting scenarios"""

    def test_technical_heavy_weighting(self, bullish_price_data, neutral_articles, current_price):
        """Test with technical analysis heavily weighted"""
        # Technical bullish, sentiment neutral
        tech_analyzer = TechnicalAnalyzer()
        technical_results = tech_analyzer.analyze(bullish_price_data)

        sent_analyzer = SentimentAnalyzer()
        sentiment_results = sent_analyzer.analyze_articles(neutral_articles)

        # Heavy technical weight
        engine = RecommendationEngine(reddit_weight=0.1, news_weight=0.1, technical_weight=0.8)
        recommendation = engine.generate_recommendation(
            technical_analysis=technical_results,
            news_sentiment_analysis=sentiment_results,
            reddit_sentiment_analysis=sentiment_results,
            historical_data={"Close": bullish_price_data["close"].tolist()},
            current_price=current_price,
        )

        # Should follow technical analysis (buy)
        assert recommendation["recommendation"] in ["buy", "strong_buy"]

    def test_sentiment_heavy_weighting(self, bullish_price_data, positive_articles, current_price):
        """Test with sentiment heavily weighted"""
        # Technical neutral, sentiment positive
        tech_analyzer = TechnicalAnalyzer()
        technical_results = tech_analyzer.analyze(bullish_price_data)
        # Override to neutral
        technical_results["overall"]["recommendation"] = "hold"

        sent_analyzer = SentimentAnalyzer()
        sentiment_results = sent_analyzer.analyze_articles(positive_articles)

        # Heavy sentiment weight
        engine = RecommendationEngine(reddit_weight=0.45, news_weight=0.45, technical_weight=0.1)
        recommendation = engine.generate_recommendation(
            technical_analysis=technical_results,
            news_sentiment_analysis=sentiment_results,
            reddit_sentiment_analysis=sentiment_results,
            historical_data={"Close": bullish_price_data["close"].tolist()},
            current_price=current_price,
        )

        # Should follow sentiment (buy)
        assert recommendation["recommendation"] in ["buy", "strong_buy", "hold"]

    def test_balanced_weighting(self, bullish_price_data, positive_articles, current_price):
        """Test with balanced weighting"""
        tech_analyzer = TechnicalAnalyzer()
        technical_results = tech_analyzer.analyze(bullish_price_data)

        sent_analyzer = SentimentAnalyzer()
        sentiment_results = sent_analyzer.analyze_articles(positive_articles)

        # Balanced weights
        engine = RecommendationEngine(reddit_weight=0.35, news_weight=0.35, technical_weight=0.3)
        recommendation = engine.generate_recommendation(
            technical_analysis=technical_results,
            news_sentiment_analysis=sentiment_results,
            reddit_sentiment_analysis=sentiment_results,
            historical_data={"Close": bullish_price_data["close"].tolist()},
            current_price=current_price,
        )

        # Should combine both signals
        assert recommendation["recommendation"] in ["buy", "strong_buy"]
        assert "technical" in recommendation["signals"]
        assert "sentiment" in recommendation["signals"]


class TestDataQualityHandling:
    """Test handling of various data quality issues"""

    def test_minimal_price_data(self, positive_articles, current_price):
        """Test with minimal historical price data"""
        # Only 20 days of data
        dates = pd.date_range(end=datetime.now(), periods=20, freq="D")
        prices = np.linspace(48000, 52000, 20)

        minimal_data = pd.DataFrame(
            {
                "close": prices,
                "open": prices,
                "high": prices * 1.01,
                "low": prices * 0.99,
                "volume": [1000000] * 20,
            },
            index=dates,
        )

        tech_analyzer = TechnicalAnalyzer()
        technical_results = tech_analyzer.analyze(minimal_data)

        sent_analyzer = SentimentAnalyzer()
        sentiment_results = sent_analyzer.analyze_articles(positive_articles)

        engine = RecommendationEngine()
        recommendation = engine.generate_recommendation(
            technical_analysis=technical_results,
            news_sentiment_analysis=sentiment_results,
            reddit_sentiment_analysis=sentiment_results,
            historical_data={"Close": minimal_data["close"].tolist()},
            current_price=current_price,
        )

        # Should still generate recommendation
        assert "recommendation" in recommendation
        assert "confidence" in recommendation

    def test_no_sentiment_data(self, bullish_price_data, current_price):
        """Test with no sentiment articles (fallback to neutral)"""
        tech_analyzer = TechnicalAnalyzer()
        technical_results = tech_analyzer.analyze(bullish_price_data)

        sent_analyzer = SentimentAnalyzer()
        sentiment_results = sent_analyzer.analyze_articles([])  # Empty list

        engine = RecommendationEngine()
        recommendation = engine.generate_recommendation(
            technical_analysis=technical_results,
            news_sentiment_analysis=sentiment_results,
            reddit_sentiment_analysis=sentiment_results,
            historical_data={"Close": bullish_price_data["close"].tolist()},
            current_price=current_price,
        )

        # Should still generate recommendation (based on technical)
        assert "recommendation" in recommendation
        assert recommendation["signals"]["sentiment"]["confidence"] == 0.0

    def test_extreme_price_volatility(self, positive_articles, current_price):
        """Test with extreme price volatility"""
        dates = pd.date_range(end=datetime.now(), periods=50, freq="D")
        # Extreme swings
        prices = [50000, 40000, 60000, 35000, 65000] * 10

        volatile_data = pd.DataFrame(
            {
                "close": prices,
                "open": prices,
                "high": [p * 1.1 for p in prices],
                "low": [p * 0.9 for p in prices],
                "volume": [1000000] * 50,
            },
            index=dates,
        )

        tech_analyzer = TechnicalAnalyzer()
        technical_results = tech_analyzer.analyze(volatile_data)

        sent_analyzer = SentimentAnalyzer()
        sentiment_results = sent_analyzer.analyze_articles(positive_articles)

        engine = RecommendationEngine()
        recommendation = engine.generate_recommendation(
            technical_analysis=technical_results,
            news_sentiment_analysis=sentiment_results,
            reddit_sentiment_analysis=sentiment_results,
            historical_data={"Close": volatile_data["close"].tolist()},
            current_price=current_price,
        )

        # Should handle without crashing
        assert "recommendation" in recommendation


class TestResponseConsistency:
    """Test consistency and reproducibility of recommendations"""

    def test_same_inputs_same_outputs(self, bullish_price_data, positive_articles, current_price):
        """Test that same inputs produce same outputs"""
        tech_analyzer = TechnicalAnalyzer()
        technical_results = tech_analyzer.analyze(bullish_price_data)

        sent_analyzer = SentimentAnalyzer()
        sentiment_results = sent_analyzer.analyze_articles(positive_articles)

        engine = RecommendationEngine(reddit_weight=0.4, news_weight=0.3, technical_weight=0.3)

        # Generate recommendation twice
        rec1 = engine.generate_recommendation(
            technical_analysis=technical_results,
            news_sentiment_analysis=sentiment_results,
            reddit_sentiment_analysis=sentiment_results,
            historical_data={"Close": bullish_price_data["close"].tolist()},
            current_price=current_price,
        )

        rec2 = engine.generate_recommendation(
            technical_analysis=technical_results,
            news_sentiment_analysis=sentiment_results,
            reddit_sentiment_analysis=sentiment_results,
            historical_data={"Close": bullish_price_data["close"].tolist()},
            current_price=current_price,
        )

        # Core recommendation should be identical (excluding timestamp)
        assert rec1["recommendation"] == rec2["recommendation"]
        assert rec1["confidence"] == rec2["confidence"]
        assert rec1["current_price"] == rec2["current_price"]
        assert rec1["combined_score"] == rec2["combined_score"]

    def test_small_weight_changes_smooth_transitions(
        self, bullish_price_data, positive_articles, current_price
    ):
        """Test that small weight changes don't cause drastic recommendation changes"""
        tech_analyzer = TechnicalAnalyzer()
        technical_results = tech_analyzer.analyze(bullish_price_data)

        sent_analyzer = SentimentAnalyzer()
        sentiment_results = sent_analyzer.analyze_articles(positive_articles)

        # Test with slightly different weights
        engine1 = RecommendationEngine(reddit_weight=0.40, news_weight=0.30, technical_weight=0.30)
        engine2 = RecommendationEngine(reddit_weight=0.42, news_weight=0.29, technical_weight=0.29)

        rec1 = engine1.generate_recommendation(
            technical_analysis=technical_results,
            news_sentiment_analysis=sentiment_results,
            reddit_sentiment_analysis=sentiment_results,
            historical_data={"Close": bullish_price_data["close"].tolist()},
            current_price=current_price,
        )

        rec2 = engine2.generate_recommendation(
            technical_analysis=technical_results,
            news_sentiment_analysis=sentiment_results,
            reddit_sentiment_analysis=sentiment_results,
            historical_data={"Close": bullish_price_data["close"].tolist()},
            current_price=current_price,
        )

        # Recommendations should be similar (not wildly different)
        assert abs(rec1["confidence"] - rec2["confidence"]) < 0.1
        assert abs(rec1["combined_score"] - rec2["combined_score"]) < 0.05


class TestTargetPriceRealism:
    """Test that generated target prices are realistic"""

    def test_buy_targets_reasonable_range(self, bullish_price_data, positive_articles):
        """Test that buy targets are within reasonable range"""
        current_price = 50000.0

        tech_analyzer = TechnicalAnalyzer()
        technical_results = tech_analyzer.analyze(bullish_price_data)

        sent_analyzer = SentimentAnalyzer()
        sentiment_results = sent_analyzer.analyze_articles(positive_articles)

        engine = RecommendationEngine()
        recommendation = engine.generate_recommendation(
            technical_analysis=technical_results,
            news_sentiment_analysis=sentiment_results,
            reddit_sentiment_analysis=sentiment_results,
            historical_data={"Close": bullish_price_data["close"].tolist()},
            current_price=current_price,
        )

        targets = recommendation["targets"]

        # All prices should be positive
        assert all(v > 0 for v in targets.values())

        # Entry should equal current price
        assert targets["entry"] == current_price

        # If buy recommendation, verify target structure
        if "buy" in recommendation["recommendation"]:
            assert "target_1" in targets
            assert "target_2" in targets
            assert "stop_loss" in targets

            # Targets should be above entry
            assert targets["target_1"] > current_price
            assert targets["target_2"] > targets["target_1"]

            # Stop loss should be below entry
            assert targets["stop_loss"] < current_price

            # Targets shouldn't be extreme (within 20%)
            assert targets["target_2"] < current_price * 1.2
            assert targets["stop_loss"] > current_price * 0.8


class TestFormattedOutput:
    """Test formatted recommendation output"""

    def test_formatted_recommendation_readability(
        self, bullish_price_data, positive_articles, current_price
    ):
        """Test that formatted output is readable and complete"""
        tech_analyzer = TechnicalAnalyzer()
        technical_results = tech_analyzer.analyze(bullish_price_data)

        sent_analyzer = SentimentAnalyzer()
        sentiment_results = sent_analyzer.analyze_articles(positive_articles)

        engine = RecommendationEngine()
        recommendation = engine.generate_recommendation(
            technical_analysis=technical_results,
            news_sentiment_analysis=sentiment_results,
            reddit_sentiment_analysis=sentiment_results,
            historical_data={"Close": bullish_price_data["close"].tolist()},
            current_price=current_price,
        )

        formatted = engine.format_recommendation(recommendation)

        # Check key sections exist
        assert "BITCOIN PORTFOLIO ADVISOR" in formatted
        assert "RECOMMENDATION" in formatted
        assert str(current_price) in formatted or f"${current_price:,.2f}" in formatted
        assert "DISCLAIMER" in formatted.upper()

    def test_formatted_output_includes_reasoning(
        self, bullish_price_data, positive_articles, current_price
    ):
        """Test that formatted output includes reasoning"""
        tech_analyzer = TechnicalAnalyzer()
        technical_results = tech_analyzer.analyze(bullish_price_data)

        sent_analyzer = SentimentAnalyzer()
        sentiment_results = sent_analyzer.analyze_articles(positive_articles)

        engine = RecommendationEngine()
        recommendation = engine.generate_recommendation(
            technical_analysis=technical_results,
            news_sentiment_analysis=sentiment_results,
            reddit_sentiment_analysis=sentiment_results,
            historical_data={"Close": bullish_price_data["close"].tolist()},
            current_price=current_price,
        )

        formatted = engine.format_recommendation(recommendation)

        # Should include reasoning section
        assert "REASONING" in formatted or recommendation["reasoning"] in formatted


class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_missing_technical_fields(self, positive_articles, current_price, bullish_price_data):
        """Test handling of incomplete technical analysis"""
        # Incomplete technical analysis
        incomplete_technical = {
            "overall": {"recommendation": "buy", "confidence": 0.7}
            # Missing RSI, MACD, etc.
        }

        sent_analyzer = SentimentAnalyzer()
        sentiment_results = sent_analyzer.analyze_articles(positive_articles)

        engine = RecommendationEngine()

        # Should handle gracefully
        recommendation = engine.generate_recommendation(
            technical_analysis=incomplete_technical,
            news_sentiment_analysis=sentiment_results,
            reddit_sentiment_analysis=sentiment_results,
            historical_data={"Close": bullish_price_data["close"].tolist()},
            current_price=current_price,
        )

        assert "recommendation" in recommendation

    def test_zero_current_price(self, bullish_price_data, positive_articles):
        """Test handling of invalid zero price"""
        tech_analyzer = TechnicalAnalyzer()
        technical_results = tech_analyzer.analyze(bullish_price_data)

        sent_analyzer = SentimentAnalyzer()
        sentiment_results = sent_analyzer.analyze_articles(positive_articles)

        engine = RecommendationEngine()

        # Zero price is invalid but should not crash
        recommendation = engine.generate_recommendation(
            technical_analysis=technical_results,
            news_sentiment_analysis=sentiment_results,
            reddit_sentiment_analysis=sentiment_results,
            historical_data={"Close": bullish_price_data["close"].tolist()},
            current_price=0.0,
        )

        # Should still generate recommendation with zero price
        assert recommendation["current_price"] == 0.0
        assert "recommendation" in recommendation
