"""
Sentiment analysis module for crypto news
"""

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from typing import List, Dict
import statistics


class SentimentAnalyzer:
    """Analyze sentiment of cryptocurrency news"""

    def __init__(self, analyzer_type: str = "vader"):
        """
        Initialize sentiment analyzer

        Args:
            analyzer_type: Type of analyzer ('vader' or 'textblob')
        """
        self.analyzer_type = analyzer_type.lower()

        if self.analyzer_type == "vader":
            self.vader = SentimentIntensityAnalyzer()
        else:
            raise ValueError(f"Analyzer type '{analyzer_type}' not supported yet")

    def analyze_text(self, text: str) -> Dict:
        """
        Analyze sentiment of a single text

        Args:
            text: Text to analyze

        Returns:
            Dictionary with sentiment scores
        """
        if self.analyzer_type == "vader":
            return self._analyze_vader(text)
        else:
            raise ValueError(f"Analyzer type '{self.analyzer_type}' not supported")

    def _analyze_vader(self, text: str) -> Dict:
        """
        Analyze sentiment using VADER

        Returns:
            Dict with neg, neu, pos, compound scores
        """
        if not text or not text.strip():
            return {
                'neg': 0.0,
                'neu': 1.0,
                'pos': 0.0,
                'compound': 0.0
            }

        scores = self.vader.polarity_scores(text)
        return scores

    def analyze_article(self, article: Dict) -> Dict:
        """
        Analyze sentiment of a news article

        Args:
            article: Article dictionary with 'title', 'description', 'content'

        Returns:
            Dictionary with sentiment analysis results
        """
        # Combine text from article
        text_parts = []

        if article.get('title'):
            text_parts.append(article['title'])

        if article.get('description'):
            text_parts.append(article['description'])

        # Don't include full content as it may dilute headline sentiment
        # Headlines typically have stronger sentiment signals

        combined_text = " ".join(text_parts)

        # Analyze sentiment
        scores = self.analyze_text(combined_text)

        # Classify sentiment
        compound = scores['compound']
        if compound >= 0.05:
            classification = "positive"
        elif compound <= -0.05:
            classification = "negative"
        else:
            classification = "neutral"

        return {
            'text': combined_text[:200] + "..." if len(combined_text) > 200 else combined_text,
            'scores': scores,
            'classification': classification,
            'compound': compound,
            'article': {
                'title': article.get('title', ''),
                'source': article.get('source', ''),
                'url': article.get('url', ''),
                'published_date': article.get('published_date', '')
            }
        }

    def analyze_articles(self, articles: List[Dict]) -> Dict:
        """
        Analyze sentiment across multiple articles

        Args:
            articles: List of article dictionaries

        Returns:
            Aggregated sentiment analysis
        """
        if not articles:
            return {
                'overall_sentiment': 'neutral',
                'average_compound': 0.0,
                'article_count': 0,
                'positive_count': 0,
                'negative_count': 0,
                'neutral_count': 0,
                'articles': []
            }

        # Analyze each article
        analyzed_articles = []
        compound_scores = []

        for article in articles:
            result = self.analyze_article(article)
            analyzed_articles.append(result)
            compound_scores.append(result['compound'])

        # Calculate aggregated metrics
        avg_compound = statistics.mean(compound_scores) if compound_scores else 0.0
        median_compound = statistics.median(compound_scores) if compound_scores else 0.0

        # Count sentiments
        positive_count = sum(1 for a in analyzed_articles if a['classification'] == 'positive')
        negative_count = sum(1 for a in analyzed_articles if a['classification'] == 'negative')
        neutral_count = sum(1 for a in analyzed_articles if a['classification'] == 'neutral')

        # Overall sentiment classification
        if avg_compound >= 0.05:
            overall_sentiment = "positive"
            recommendation = "buy"
        elif avg_compound <= -0.05:
            overall_sentiment = "negative"
            recommendation = "sell"
        else:
            overall_sentiment = "neutral"
            recommendation = "hold"

        # Calculate confidence based on consistency and strength
        sentiment_ratio = max(positive_count, negative_count, neutral_count) / len(analyzed_articles)
        strength = abs(avg_compound)
        confidence = (sentiment_ratio * 0.5 + strength * 0.5)

        return {
            'overall_sentiment': overall_sentiment,
            'recommendation': recommendation,
            'confidence': round(confidence, 2),
            'average_compound': round(avg_compound, 3),
            'median_compound': round(median_compound, 3),
            'article_count': len(articles),
            'positive_count': positive_count,
            'negative_count': negative_count,
            'neutral_count': neutral_count,
            'positive_ratio': round(positive_count / len(articles), 2),
            'negative_ratio': round(negative_count / len(articles), 2),
            'neutral_ratio': round(neutral_count / len(articles), 2),
            'articles': analyzed_articles
        }

    def get_sentiment_summary(self, articles: List[Dict]) -> str:
        """
        Get human-readable sentiment summary

        Args:
            articles: List of articles

        Returns:
            Formatted summary string
        """
        analysis = self.analyze_articles(articles)

        summary = f"""
Sentiment Analysis Summary:
---------------------------
Articles Analyzed: {analysis['article_count']}
Overall Sentiment: {analysis['overall_sentiment'].upper()} ({analysis['average_compound']})
Recommendation: {analysis['recommendation'].upper()}
Confidence: {analysis['confidence'] * 100:.0f}%

Distribution:
  Positive: {analysis['positive_count']} ({analysis['positive_ratio'] * 100:.0f}%)
  Negative: {analysis['negative_count']} ({analysis['negative_ratio'] * 100:.0f}%)
  Neutral: {analysis['neutral_count']} ({analysis['neutral_ratio'] * 100:.0f}%)
"""
        return summary.strip()


if __name__ == "__main__":
    # Test sentiment analyzer
    print("Testing Sentiment Analyzer...\n")

    # Sample articles
    sample_articles = [
        {
            'title': 'Bitcoin Soars to New All-Time High!',
            'description': 'Bitcoin price surges past $70,000 as institutional demand grows.',
            'source': 'Crypto News',
            'url': 'https://example.com/1'
        },
        {
            'title': 'Regulatory Concerns Shake Crypto Market',
            'description': 'New regulations cause uncertainty among Bitcoin investors.',
            'source': 'Financial Times',
            'url': 'https://example.com/2'
        },
        {
            'title': 'Bitcoin Adoption Increases in Developing Nations',
            'description': 'More countries are embracing Bitcoin as legal tender.',
            'source': 'Global Finance',
            'url': 'https://example.com/3'
        },
        {
            'title': 'Expert Analysis: Bitcoin Price Prediction',
            'description': 'Analysts discuss potential Bitcoin price movements for next quarter.',
            'source': 'Crypto Insider',
            'url': 'https://example.com/4'
        }
    ]

    # Analyze
    analyzer = SentimentAnalyzer(analyzer_type="vader")

    print("Individual Article Analysis:")
    print("=" * 60)
    for article in sample_articles[:2]:
        result = analyzer.analyze_article(article)
        print(f"\nTitle: {article['title']}")
        print(f"Sentiment: {result['classification'].upper()} (compound: {result['compound']})")
        print(f"Scores: {result['scores']}")

    print("\n\n" + "=" * 60)
    print(analyzer.get_sentiment_summary(sample_articles))
