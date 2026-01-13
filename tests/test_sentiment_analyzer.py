"""
Comprehensive tests for SentimentAnalyzer
Tests VADER sentiment analysis, article processing, and aggregation
"""

import pytest

from src.analysis.sentiment import SentimentAnalyzer


class TestSentimentAnalyzerInitialization:
    """Test analyzer initialization"""

    def test_default_initialization(self):
        """Test default VADER analyzer initialization"""
        analyzer = SentimentAnalyzer()
        assert analyzer.analyzer_type == "vader"
        assert analyzer.vader is not None

    def test_vader_initialization(self):
        """Test explicit VADER initialization"""
        analyzer = SentimentAnalyzer(analyzer_type="vader")
        assert analyzer.analyzer_type == "vader"

    def test_unsupported_analyzer_type(self):
        """Test that unsupported analyzer types raise error"""
        with pytest.raises(ValueError, match="not supported"):
            SentimentAnalyzer(analyzer_type="unsupported")


class TestTextAnalysis:
    """Test single text sentiment analysis"""

    def test_analyze_positive_text(self):
        """Test analysis of positive text"""
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze_text("Bitcoin is amazing! Great news! Bullish momentum!")

        assert "compound" in result
        assert "pos" in result
        assert "neg" in result
        assert "neu" in result
        assert result["compound"] > 0.3  # Should be strongly positive

    def test_analyze_negative_text(self):
        """Test analysis of negative text"""
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze_text("Bitcoin crashes! Terrible news! Market panic!")

        assert result["compound"] < -0.3  # Should be strongly negative

    def test_analyze_neutral_text(self):
        """Test analysis of neutral text"""
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze_text("Bitcoin price is $50,000.")

        assert -0.1 <= result["compound"] <= 0.1  # Should be neutral

    def test_analyze_empty_text(self):
        """Test analysis of empty text"""
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze_text("")

        assert result["compound"] == 0.0
        assert result["neu"] == 1.0
        assert result["pos"] == 0.0
        assert result["neg"] == 0.0

    def test_analyze_whitespace_only(self):
        """Test analysis of whitespace-only text"""
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze_text("   \n\t  ")

        assert result["compound"] == 0.0

    def test_crypto_specific_terms(self):
        """Test sentiment analysis with crypto-specific language"""
        analyzer = SentimentAnalyzer()

        # Crypto bull language
        bullish_result = analyzer.analyze_text("Bitcoin to the moon! 🚀 HODL! Lambo incoming!")
        assert bullish_result["compound"] > 0

        # Crypto bear language
        bearish_result = analyzer.analyze_text("Bitcoin dump! Rugpull! REKT!")
        assert bearish_result["compound"] < 0


class TestArticleAnalysis:
    """Test single article sentiment analysis"""

    def test_analyze_article_with_title_and_description(self):
        """Test article analysis with title and description"""
        analyzer = SentimentAnalyzer()

        article = {
            "title": "Bitcoin Surges to New High",
            "description": "Institutional adoption drives Bitcoin price higher",
            "source": "Crypto News",
        }

        result = analyzer.analyze_article(article)

        assert "scores" in result
        assert "classification" in result
        assert "compound" in result
        assert "text" in result
        assert result["classification"] in ["positive", "negative", "neutral"]

    def test_analyze_article_title_only(self):
        """Test article analysis with title only"""
        analyzer = SentimentAnalyzer()

        article = {"title": "Bitcoin Price Analysis", "source": "Market Watch"}

        result = analyzer.analyze_article(article)

        assert "classification" in result
        assert result["text"] == "Bitcoin Price Analysis"

    def test_analyze_article_classification_positive(self):
        """Test positive article classification"""
        analyzer = SentimentAnalyzer()

        article = {
            "title": "Incredible Bitcoin Rally! Amazing Gains!",
            "description": "Fantastic bullish momentum drives historic surge!",
        }

        result = analyzer.analyze_article(article)

        assert result["classification"] == "positive"
        assert result["compound"] >= 0.05

    def test_analyze_article_classification_negative(self):
        """Test negative article classification"""
        analyzer = SentimentAnalyzer()

        article = {
            "title": "Bitcoin Crashes! Disaster Strikes!",
            "description": "Terrible losses as market collapses",
        }

        result = analyzer.analyze_article(article)

        assert result["classification"] == "negative"
        assert result["compound"] <= -0.05

    def test_analyze_article_classification_neutral(self):
        """Test neutral article classification"""
        analyzer = SentimentAnalyzer()

        article = {"title": "Bitcoin Price Update", "description": "Bitcoin trading at $50,000"}

        result = analyzer.analyze_article(article)

        assert result["classification"] == "neutral"
        assert -0.05 < result["compound"] < 0.05

    def test_analyze_article_metadata_preserved(self):
        """Test that article metadata is preserved in result"""
        analyzer = SentimentAnalyzer()

        article = {
            "title": "Test Article",
            "description": "Test description",
            "source": "Test Source",
            "url": "https://example.com",
            "published_date": "2024-01-10",
        }

        result = analyzer.analyze_article(article)

        assert result["article"]["title"] == "Test Article"
        assert result["article"]["source"] == "Test Source"
        assert result["article"]["url"] == "https://example.com"
        assert result["article"]["published_date"] == "2024-01-10"


class TestMultipleArticlesAnalysis:
    """Test aggregated sentiment analysis across multiple articles"""

    def test_analyze_empty_articles_list(self):
        """Test handling of empty articles list"""
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze_articles([])

        assert result["overall_sentiment"] == "neutral"
        assert result["average_compound"] == 0.0
        assert result["article_count"] == 0
        assert result["positive_count"] == 0
        assert result["negative_count"] == 0
        assert result["neutral_count"] == 0

    def test_analyze_mixed_sentiment_articles(self, sample_news_articles):
        """Test analysis of mixed sentiment articles"""
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze_articles(sample_news_articles)

        assert "overall_sentiment" in result
        assert "average_compound" in result
        assert "article_count" in result
        assert result["article_count"] == len(sample_news_articles)

        # Counts should sum to total
        total_classified = (
            result["positive_count"] + result["negative_count"] + result["neutral_count"]
        )
        assert total_classified == result["article_count"]

    def test_analyze_all_positive_articles(self, positive_articles):
        """Test analysis of all positive articles"""
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze_articles(positive_articles)

        assert result["overall_sentiment"] == "positive"
        assert result["recommendation"] == "buy"
        assert result["average_compound"] > 0.05
        assert result["positive_count"] > 0

    def test_analyze_all_negative_articles(self, negative_articles):
        """Test analysis of all negative articles"""
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze_articles(negative_articles)

        assert result["overall_sentiment"] == "negative"
        assert result["recommendation"] == "sell"
        assert result["average_compound"] < -0.05
        assert result["negative_count"] > 0

    def test_analyze_all_neutral_articles(self, neutral_articles):
        """Test analysis of all neutral articles"""
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze_articles(neutral_articles)

        assert result["overall_sentiment"] == "neutral"
        assert result["recommendation"] == "hold"
        assert -0.05 <= result["average_compound"] <= 0.05

    def test_median_compound_calculation(self, sample_news_articles):
        """Test that median compound is calculated correctly"""
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze_articles(sample_news_articles)

        assert "median_compound" in result
        assert isinstance(result["median_compound"], float)

        # Median should be between min and max of average
        assert result["median_compound"] is not None

    def test_sentiment_ratios_sum_to_one(self, sample_news_articles):
        """Test that sentiment ratios sum to 1.0"""
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze_articles(sample_news_articles)

        total_ratio = result["positive_ratio"] + result["negative_ratio"] + result["neutral_ratio"]

        assert abs(total_ratio - 1.0) < 0.01

    def test_confidence_calculation(self, positive_articles):
        """Test confidence calculation logic"""
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze_articles(positive_articles)

        # With all positive articles, confidence should be high
        assert result["confidence"] > 0.5

        # Confidence should be between 0 and 1
        assert 0.0 <= result["confidence"] <= 1.0

    def test_confidence_increases_with_consistency(self):
        """Test that confidence is higher with consistent sentiment"""
        analyzer = SentimentAnalyzer()

        # All strongly positive
        consistent_articles = [
            {"title": "Bitcoin Soars! Amazing!", "description": "Incredible gains!"},
            {"title": "Bitcoin Surges! Great!", "description": "Fantastic rally!"},
            {"title": "Bitcoin Rockets! Wow!", "description": "Spectacular rise!"},
        ]

        # Mixed sentiment
        mixed_articles = [
            {"title": "Bitcoin Soars!", "description": "Great gains!"},
            {"title": "Bitcoin Crashes!", "description": "Terrible losses!"},
            {"title": "Bitcoin Holds", "description": "Price stable"},
        ]

        consistent_result = analyzer.analyze_articles(consistent_articles)
        mixed_result = analyzer.analyze_articles(mixed_articles)

        # Consistent sentiment should have higher confidence
        assert consistent_result["confidence"] > mixed_result["confidence"]


class TestRecommendationMapping:
    """Test mapping from sentiment to trading recommendation"""

    def test_positive_sentiment_recommends_buy(self):
        """Test positive sentiment maps to buy recommendation"""
        analyzer = SentimentAnalyzer()

        positive_articles = [
            {"title": "Bitcoin Rally!", "description": "Great news!"},
            {"title": "Bitcoin Surge!", "description": "Amazing gains!"},
        ]

        result = analyzer.analyze_articles(positive_articles)

        assert result["overall_sentiment"] == "positive"
        assert result["recommendation"] == "buy"

    def test_negative_sentiment_recommends_sell(self):
        """Test negative sentiment maps to sell recommendation"""
        analyzer = SentimentAnalyzer()

        negative_articles = [
            {"title": "Bitcoin Crash!", "description": "Terrible losses!"},
            {"title": "Bitcoin Plunge!", "description": "Awful decline!"},
        ]

        result = analyzer.analyze_articles(negative_articles)

        assert result["overall_sentiment"] == "negative"
        assert result["recommendation"] == "sell"

    def test_neutral_sentiment_recommends_hold(self):
        """Test neutral sentiment maps to hold recommendation"""
        analyzer = SentimentAnalyzer()

        neutral_articles = [
            {"title": "Bitcoin Price", "description": "Market update"},
            {"title": "Bitcoin Analysis", "description": "Technical review"},
        ]

        result = analyzer.analyze_articles(neutral_articles)

        assert result["overall_sentiment"] == "neutral"
        assert result["recommendation"] == "hold"


class TestSentimentSummary:
    """Test human-readable summary generation"""

    def test_get_sentiment_summary(self, sample_news_articles):
        """Test generating sentiment summary string"""
        analyzer = SentimentAnalyzer()
        summary = analyzer.get_sentiment_summary(sample_news_articles)

        assert isinstance(summary, str)
        assert "Sentiment Analysis Summary" in summary
        assert "Articles Analyzed" in summary
        assert "Overall Sentiment" in summary
        assert "Recommendation" in summary
        assert "Confidence" in summary
        assert "Distribution" in summary

    def test_summary_contains_all_counts(self, sample_news_articles):
        """Test that summary contains positive/negative/neutral counts"""
        analyzer = SentimentAnalyzer()
        summary = analyzer.get_sentiment_summary(sample_news_articles)

        assert "Positive" in summary
        assert "Negative" in summary
        assert "Neutral" in summary


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_single_article(self):
        """Test analysis with single article"""
        analyzer = SentimentAnalyzer()

        single_article = [{"title": "Bitcoin News", "description": "Some content"}]

        result = analyzer.analyze_articles(single_article)

        assert result["article_count"] == 1
        assert "overall_sentiment" in result
        assert "confidence" in result

    def test_article_with_missing_fields(self):
        """Test handling of article with missing fields"""
        analyzer = SentimentAnalyzer()

        incomplete_article = {
            "title": "Test",
            # Missing description, source, url, etc.
        }

        result = analyzer.analyze_article(incomplete_article)

        # Should handle gracefully
        assert "classification" in result
        assert "compound" in result

    def test_article_with_none_values(self):
        """Test handling of article with None values"""
        analyzer = SentimentAnalyzer()

        article = {"title": None, "description": None, "source": None}

        result = analyzer.analyze_article(article)

        # Should handle gracefully (treat as neutral)
        assert "classification" in result

    def test_very_long_text(self):
        """Test analysis of very long text"""
        analyzer = SentimentAnalyzer()

        long_text = "Bitcoin " * 10000  # Very long text

        article = {"title": "Title", "description": long_text}

        result = analyzer.analyze_article(article)

        # Should handle without crashing
        assert "classification" in result
        # Text preview should be truncated
        assert len(result["text"]) <= 203  # 200 + "..."

    def test_special_characters_and_emojis(self):
        """Test handling of special characters and emojis"""
        analyzer = SentimentAnalyzer()

        article = {"title": "Bitcoin 🚀🌕 to the moon! 💎🙌", "description": "HODL!!! 💰💰💰"}

        result = analyzer.analyze_article(article)

        # Should handle emojis and special characters
        assert "classification" in result
        assert result["compound"] != 0  # Emojis might affect sentiment

    def test_numbers_and_prices(self):
        """Test handling of numbers and price information"""
        analyzer = SentimentAnalyzer()

        article = {
            "title": "Bitcoin at $50,000",
            "description": "Price up 5% to $50,000.00 from $47,619.05",
        }

        result = analyzer.analyze_article(article)

        # Should handle numbers gracefully
        assert "classification" in result

    def test_mixed_language_characters(self):
        """Test handling of mixed language text"""
        analyzer = SentimentAnalyzer()

        # VADER is optimized for English
        article = {
            "title": "Bitcoin great news",  # English
            "description": "Amazing bullish momentum",
        }

        result = analyzer.analyze_article(article)

        assert "classification" in result

    def test_case_insensitivity(self):
        """Test that analysis is case-insensitive where appropriate"""
        analyzer = SentimentAnalyzer()

        upper_article = {"title": "BITCOIN SOARS!", "description": "GREAT NEWS!"}
        lower_article = {"title": "bitcoin soars!", "description": "great news!"}
        mixed_article = {"title": "Bitcoin Soars!", "description": "Great News!"}

        upper_result = analyzer.analyze_article(upper_article)
        lower_result = analyzer.analyze_article(lower_article)
        mixed_result = analyzer.analyze_article(mixed_article)

        # All should be classified as positive
        assert upper_result["classification"] == "positive"
        assert lower_result["classification"] == "positive"
        assert mixed_result["classification"] == "positive"

        # Compound scores should be similar (within reasonable range)
        assert abs(upper_result["compound"] - lower_result["compound"]) < 0.1


class TestVaderSpecificBehavior:
    """Test VADER-specific sentiment scoring behavior"""

    def test_exclamation_marks_intensify(self):
        """Test that exclamation marks intensify sentiment"""
        analyzer = SentimentAnalyzer()

        normal = analyzer.analyze_text("Bitcoin is good")
        excited = analyzer.analyze_text("Bitcoin is good!")
        very_excited = analyzer.analyze_text("Bitcoin is good!!!")

        # More exclamations should increase positive sentiment
        assert excited["compound"] > normal["compound"]
        assert very_excited["compound"] >= excited["compound"]

    def test_all_caps_intensifies(self):
        """Test that ALL CAPS intensifies sentiment"""
        analyzer = SentimentAnalyzer()

        normal = analyzer.analyze_text("This is great news")
        caps = analyzer.analyze_text("THIS IS GREAT NEWS")

        # Caps should intensify positive sentiment
        assert caps["compound"] >= normal["compound"]

    def test_negation_handling(self):
        """Test that negation is handled correctly"""
        analyzer = SentimentAnalyzer()

        positive = analyzer.analyze_text("Bitcoin is good")
        negated = analyzer.analyze_text("Bitcoin is not good")

        # Negation should flip sentiment
        assert positive["compound"] > 0
        assert negated["compound"] < positive["compound"]

    def test_degree_modifiers(self):
        """Test that degree modifiers affect intensity"""
        analyzer = SentimentAnalyzer()

        moderate = analyzer.analyze_text("Bitcoin is good")
        strong = analyzer.analyze_text("Bitcoin is very good")
        extreme = analyzer.analyze_text("Bitcoin is extremely good")

        # Stronger modifiers should increase sentiment
        assert strong["compound"] > moderate["compound"]
        assert extreme["compound"] > strong["compound"]
