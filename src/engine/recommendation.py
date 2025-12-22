"""
Recommendation engine that combines sentiment and technical analysis
"""

from typing import Dict, Tuple
import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)


class RecommendationEngine:
    """Generate trading recommendations based on combined signals"""

    def __init__(self, reddit_weight: float = 0.4, news_weight: float = 0.3, technical_weight: float = 0.3):
        """
        Initialize recommendation engine

        Args:
            reddit_weight: Weight for Reddit sentiment analysis (0-1)
            news_weight: Weight for news sentiment analysis (0-1)
            technical_weight: Weight for technical analysis (0-1)
        """
        if not (0 <= reddit_weight <= 1 and 0 <= news_weight <= 1 and 0 <= technical_weight <= 1):
            raise ValueError("Weights must be between 0 and 1")

        if abs(reddit_weight + news_weight + technical_weight - 1.0) > 0.01:
            raise ValueError("Weights must sum to 1.0")

        self.reddit_weight = reddit_weight
        self.news_weight = news_weight
        self.technical_weight = technical_weight

    def _check_divergence(self, historical_data: Dict, reddit_sentiment_score: float) -> str:
        """
        Checks for bearish divergence between price and Reddit sentiment.
        A simple implementation: checks if price is at a 30-day high while sentiment is not.
        """
        close_prices = historical_data.get('Close')
        if close_prices is None or len(close_prices) < 30:
            return "Not enough data for divergence check."

        # Use standard list operations instead of pandas methods
        recent_prices = close_prices[-30:]
        max_price = max(recent_prices)
        current_price = recent_prices[-1]

        # A very basic check: is price at a high but sentiment is low?
        if current_price >= max_price and reddit_sentiment_score < 0.5:
            return "BEARISH DIVERGENCE: Price is hitting new highs, but Reddit sentiment remains low. This could signal underlying weakness."
        
        return "No significant divergence detected."

    def generate_recommendation(self, technical_analysis: Dict,
                               news_sentiment_analysis: Dict,
                               reddit_sentiment_analysis: Dict,
                               historical_data: Dict,
                               current_price: float) -> Dict:
        """
        Generate trading recommendation
        """
        logging.info("--- Inside Recommendation Engine ---")
        logging.info(f"Received technical analysis: {technical_analysis['overall']['recommendation']}")
        logging.info(f"Received news sentiment: {news_sentiment_analysis['overall_sentiment']}")
        logging.info(f"Received reddit sentiment: {reddit_sentiment_analysis['overall_sentiment']}")

        # --- Priority 1: Contrarian Logic Gate ---
        reddit_score_raw = reddit_sentiment_analysis['average_compound']
        logging.info(f"Checking contrarian logic with Reddit score: {reddit_score_raw:.3f}")
        if reddit_score_raw > 0.85:
            logging.warning("!! CONTRARIAN ALERT: Extreme Euphoria detected !!")
            return self._create_contrarian_alert(
                "CONTRARIAN ALERT: Market sentiment is unsustainably bullish. Historically, this precedes a pullback. Consider a cautious stance.",
                "Extreme Euphoria",
                current_price
            )
        if reddit_score_raw < 0.15:
            logging.warning("!! CONTRARIAN ALERT: Extreme Fear detected !!")
            return self._create_contrarian_alert(
                "CONTRARIAN ALERT: Maximum fear detected. Potential local bottom. Historically, this is an accumulation zone.",
                "Extreme Fear",
                current_price
            )

        # --- Priority 2: Divergence Check ---
        logging.info("Checking for sentiment/price divergence...")
        divergence_signal = self._check_divergence(historical_data, reddit_score_raw)
        logging.info(f"Divergence check result: {divergence_signal}")

        # --- Priority 3: Weighted Signal Combination ---
        # (The rest of the method remains the same)
        technical_rec = technical_analysis['overall']['recommendation']
        technical_conf = technical_analysis['overall']['confidence']

        news_rec = news_sentiment_analysis['recommendation']
        news_conf = news_sentiment_analysis['confidence']
        
        reddit_rec = reddit_sentiment_analysis['recommendation']
        reddit_conf = reddit_sentiment_analysis['confidence']

        tech_score = self._recommendation_to_score(technical_rec) * technical_conf
        news_score = self._recommendation_to_score(news_rec) * news_conf
        reddit_score = self._recommendation_to_score(reddit_rec) * reddit_conf

        combined_score = (
            reddit_score * self.reddit_weight +
            news_score * self.news_weight +
            tech_score * self.technical_weight
        )
        logging.info(f"Final combined score: {combined_score:.3f}")

        recommendation, confidence = self._score_to_recommendation(combined_score)

        reasoning = self._generate_reasoning(
            technical_analysis, news_sentiment_analysis, reddit_sentiment_analysis,
            divergence_signal, recommendation
        )

        targets = self._calculate_targets(current_price, recommendation, confidence)

        # Combine Reddit and News for backward compatibility with frontend
        combined_compound = (reddit_sentiment_analysis['average_compound'] * self.reddit_weight +
                            news_sentiment_analysis['average_compound'] * self.news_weight) / \
                           (self.reddit_weight + self.news_weight)

        combined_sentiment = {
            'overall_sentiment': reddit_sentiment_analysis['overall_sentiment'],  # Use Reddit as primary
            'overall': reddit_sentiment_analysis['overall_sentiment'],  # Alias for compatibility
            'compound': combined_compound,  # Frontend expects 'compound'
            'average_compound': combined_compound,  # Keep both for compatibility
            'article_count': reddit_sentiment_analysis['article_count'] + news_sentiment_analysis['article_count'],
            'recommendation': reddit_rec if reddit_conf > news_conf else news_rec,
            'confidence': max(reddit_conf, news_conf)
        }

        return {
            'recommendation': recommendation,
            'confidence': round(confidence, 2),
            'combined_score': round(combined_score, 3),
            'signals': {
                'technical': {
                    'recommendation': technical_rec,
                    'confidence': technical_conf,
                    'score': round(tech_score, 3),
                    'weight': self.technical_weight,
                    'details': {
                        'rsi': technical_analysis.get('rsi', {}),
                        'macd': technical_analysis.get('macd', {}),
                        'ma_trend': technical_analysis.get('ma_trend'),
                        'ma_crossovers': technical_analysis.get('ma_crossovers'),
                        'moving_averages': technical_analysis.get('moving_averages')
                    }
                },
                'sentiment': {
                    'recommendation': combined_sentiment['recommendation'],
                    'confidence': combined_sentiment['confidence'],
                    'score': round((reddit_score * self.reddit_weight + news_score * self.news_weight) /
                                 (self.reddit_weight + self.news_weight), 3),
                    'weight': self.reddit_weight + self.news_weight,
                    'details': combined_sentiment
                }
            },
            'current_price': current_price,
            'targets': targets,
            'reasoning': reasoning,
            'divergence_signal': divergence_signal,
            'timestamp': datetime.datetime.now().isoformat()
        }


    def _create_contrarian_alert(self, message: str, alert_type: str, current_price: float) -> Dict:
        """Creates a special dictionary for contrarian alerts."""
        return {
            'recommendation': 'CONTRARIAN_ALERT',
            'confidence': 1.0,
            'reasoning': message,
            'alert_type': alert_type,
            'current_price': current_price,
            'timestamp': datetime.datetime.now().isoformat(),
            'combined_score': 0.0,
            'targets': {
                'entry': round(current_price, 2),
                'support': round(current_price * 0.95, 2),
                'resistance': round(current_price * 1.05, 2)
            },
            'signals': {
                'technical': {
                    'recommendation': 'hold',
                    'confidence': 0.5,
                    'score': 0.0,
                    'weight': 0.6,
                    'details': {
                        'rsi': {'value': 50, 'signal': 'neutral'},
                        'macd': {'signal': 'neutral'}
                    }
                },
                'sentiment': {
                    'recommendation': 'hold',
                    'confidence': 1.0,
                    'score': 1.0 if alert_type == "Extreme Fear" else -1.0,
                    'weight': 0.4,
                    'details': {
                        'overall_sentiment': alert_type.lower().replace(' ', '_'),
                        'overall': alert_type.lower().replace(' ', '_'),
                        'compound': 0.1 if alert_type == "Extreme Fear" else 0.9,
                        'average_compound': 0.1 if alert_type == "Extreme Fear" else 0.9,
                        'article_count': 0
                    }
                }
            }
        }


    def _recommendation_to_score(self, recommendation: str) -> float:
        """
        Convert recommendation to numerical score

        Args:
            recommendation: 'buy', 'sell', or 'hold'

        Returns:
            Score between -1 and 1
        """
        mapping = {
            'buy': 1.0,
            'hold': 0.0,
            'sell': -1.0
        }
        return mapping.get(recommendation.lower(), 0.0)

    def _score_to_recommendation(self, score: float) -> Tuple[str, float]:
        """
        Convert combined score to recommendation and confidence

        Args:
            score: Combined score (-1 to 1)

        Returns:
            Tuple of (recommendation, confidence)
        """
        abs_score = abs(score)

        if score >= 0.7:
            return "strong_buy", min(abs_score, 1.0)
        elif score >= 0.3:
            return "buy", abs_score
        elif score <= -0.7:
            return "strong_sell", min(abs_score, 1.0)
        elif score <= -0.3:
            return "sell", abs_score
        else:
            return "hold", 1.0 - abs_score

    def _generate_reasoning(self, technical: Dict, news: Dict, reddit: Dict, divergence: str, final_rec: str) -> str:
        """Generate human-readable reasoning for the recommendation."""
        reasons = [divergence]
        
        # Social, News, and Technical summaries
        reasons.append(f"Reddit sentiment is {reddit['overall_sentiment']} (score: {reddit['average_compound']:.2f}).")
        reasons.append(f"News sentiment is {news['overall_sentiment']} (score: {news['average_compound']:.2f}).")
        reasons.append(f"Technical analysis suggests a {technical['overall']['recommendation']} state.")
        
        # Agreement/disagreement
        if technical['overall']['recommendation'] == news['recommendation'] == reddit['recommendation']:
            reasons.append("Social sentiment, news sentiment, and technical analysis are all in agreement.")
        else:
            reasons.append("There is some disagreement between signals, requiring a weighted approach.")

        return ". ".join(filter(None, reasons)) + "."

    def _calculate_targets(self, current_price: float, recommendation: str,
                          confidence: float) -> Dict:
        """
        Calculate target prices

        Simple estimation based on recommendation and confidence
        """
        if 'buy' in recommendation:
            # Upside targets
            target_1 = current_price * (1 + 0.05 * confidence)
            target_2 = current_price * (1 + 0.10 * confidence)
            stop_loss = current_price * (1 - 0.03 * confidence)

            return {
                'entry': round(current_price, 2),
                'target_1': round(target_1, 2),
                'target_2': round(target_2, 2),
                'stop_loss': round(stop_loss, 2)
            }

        elif 'sell' in recommendation:
            # Downside targets
            target_1 = current_price * (1 - 0.05 * confidence)
            target_2 = current_price * (1 - 0.10 * confidence)
            stop_loss = current_price * (1 + 0.03 * confidence)

            return {
                'entry': round(current_price, 2),
                'target_1': round(target_1, 2),
                'target_2': round(target_2, 2),
                'stop_loss': round(stop_loss, 2)
            }

        else:  # hold
            return {
                'entry': round(current_price, 2),
                'support': round(current_price * 0.95, 2),
                'resistance': round(current_price * 1.05, 2)
            }

    def format_recommendation(self, recommendation: Dict) -> str:
        """Formats the recommendation dictionary into a human-readable string."""
        # Handle Contrarian Alert
        if recommendation.get('recommendation') == 'CONTRARIAN_ALERT':
            return f"""
╔══════════════════════════════════════════════════════════════╗
║                   BITCOIN PORTFOLIO ADVISOR                  ║
╚══════════════════════════════════════════════════════════════╝

Date/Time: {recommendation['timestamp']}
Current BTC Price: ${recommendation['current_price']:,.2f}

═══════════════════════════════════════════════════════════════

{recommendation.get('alert_type', '').upper()}
{recommendation['reasoning']}

═══════════════════════════════════════════════════════════════
"""
        
        rec = recommendation['recommendation'].replace('_', ' ').upper()
        conf = recommendation['confidence'] * 100
        price = recommendation['current_price']

        output = f"""
╔══════════════════════════════════════════════════════════════╗
║           BITCOIN PORTFOLIO ADVISOR RECOMMENDATION           ║
╚══════════════════════════════════════════════════════════════╝

**Based on Reddit Sentiment Analysis (High Priority)...**

Date/Time: {recommendation['timestamp']}
Current BTC Price: ${price:,.2f}

═══════════════════════════════════════════════════════════════

RECOMMENDATION: {rec}
Confidence Level: {conf:.0f}%

═══════════════════════════════════════════════════════════════

ANALYSIS BREAKDOWN:

Social Sentiment (Reddit) ({self.reddit_weight * 100:.0f}% weight):
  → Recommendation: {recommendation['signals']['reddit_sentiment']['recommendation'].upper()}
  → Confidence: {recommendation['signals']['reddit_sentiment']['confidence'] * 100:.0f}%
  → Overall Sentiment: {recommendation['signals']['reddit_sentiment']['details']['overall_sentiment'].upper()}

News Sentiment ({self.news_weight * 100:.0f}% weight):
  → Recommendation: {recommendation['signals']['news_sentiment']['recommendation'].upper()}
  → Confidence: {recommendation['signals']['news_sentiment']['confidence'] * 100:.0f}%
  → Overall Sentiment: {recommendation['signals']['news_sentiment']['details']['overall_sentiment'].upper()}

Technical Analysis ({self.technical_weight * 100:.0f}% weight):
  → Recommendation: {recommendation['signals']['technical']['recommendation'].upper()}
  → Confidence: {recommendation['signals']['technical']['confidence'] * 100:.0f}%

═══════════════════════════════════════════════════════════════

REASONING:
{recommendation['reasoning']}

═══════════════════════════════════════════════════════════════

SUGGESTED TARGETS:
"""
        targets = recommendation['targets']
        if 'target_1' in targets:
            output += f"Entry: ${targets['entry']:,.2f}, Target 1: ${targets['target_1']:,.2f}, Stop: ${targets['stop_loss']:,.2f}"
        else:
            output += f"Support: ${targets.get('support', 'N/A'):,.2f}, Resistance: ${targets.get('resistance', 'N/A'):,.2f}"

        output += "\n═══════════════════════════════════════════════════════════════\n"
        output += "DISCLAIMER: For educational purposes only. Not financial advice."
        return output.strip()


if __name__ == "__main__":
    # Test recommendation engine
    print("Testing Recommendation Engine...\n")

    # Mock technical analysis
    mock_technical = {
        'rsi': {
            'value': 58.2,
            'signal': 'neutral',
            'recommendation': 'hold'
        },
        'macd': {
            'macd_line': 125.5,
            'signal_line': 110.2,
            'histogram': 15.3,
            'signal': 'bullish',
            'recommendation': 'buy'
        },
        'overall': {
            'recommendation': 'buy',
            'confidence': 0.65,
            'buy_signals': 1,
            'sell_signals': 0
        }
    }

    # Mock sentiment analysis
    mock_sentiment = {
        'overall_sentiment': 'positive',
        'recommendation': 'buy',
        'confidence': 0.72,
        'average_compound': 0.245,
        'article_count': 25,
        'positive_count': 18,
        'negative_count': 4,
        'neutral_count': 3
    }

    # Generate recommendation
    engine = RecommendationEngine(technical_weight=0.6, sentiment_weight=0.4)
    rec = engine.generate_recommendation(
        technical_analysis=mock_technical,
        sentiment_analysis=mock_sentiment,
        current_price=65432.50
    )

    # Display
    print(engine.format_recommendation(rec))
