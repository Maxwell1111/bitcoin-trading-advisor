"""
Recommendation engine that combines sentiment and technical analysis
"""

from typing import Dict, Tuple
import datetime


class RecommendationEngine:
    """Generate trading recommendations based on combined signals"""

    def __init__(self, technical_weight: float = 0.6, sentiment_weight: float = 0.4):
        """
        Initialize recommendation engine

        Args:
            technical_weight: Weight for technical analysis (0-1)
            sentiment_weight: Weight for sentiment analysis (0-1)
        """
        if not (0 <= technical_weight <= 1 and 0 <= sentiment_weight <= 1):
            raise ValueError("Weights must be between 0 and 1")

        if abs(technical_weight + sentiment_weight - 1.0) > 0.01:
            raise ValueError("Weights must sum to 1.0")

        self.technical_weight = technical_weight
        self.sentiment_weight = sentiment_weight

    def generate_recommendation(self, technical_analysis: Dict,
                               sentiment_analysis: Dict,
                               current_price: float) -> Dict:
        """
        Generate trading recommendation

        Args:
            technical_analysis: Results from technical analyzer
            sentiment_analysis: Results from sentiment analyzer
            current_price: Current Bitcoin price

        Returns:
            Dictionary with recommendation and details
        """
        # Extract signals
        technical_rec = technical_analysis['overall']['recommendation']
        technical_conf = technical_analysis['overall']['confidence']

        sentiment_rec = sentiment_analysis['recommendation']
        sentiment_conf = sentiment_analysis['confidence']

        # Convert recommendations to numerical scores (-1 to 1)
        tech_score = self._recommendation_to_score(technical_rec) * technical_conf
        sent_score = self._recommendation_to_score(sentiment_rec) * sentiment_conf

        # Calculate weighted combined score
        combined_score = (
            tech_score * self.technical_weight +
            sent_score * self.sentiment_weight
        )

        # Determine final recommendation
        recommendation, confidence = self._score_to_recommendation(combined_score)

        # Generate reasoning
        reasoning = self._generate_reasoning(
            technical_analysis, sentiment_analysis,
            technical_rec, sentiment_rec, recommendation
        )

        # Calculate target prices (simple estimation)
        targets = self._calculate_targets(current_price, recommendation, confidence)

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
                        'rsi': technical_analysis['rsi'],
                        'macd': technical_analysis['macd']
                    }
                },
                'sentiment': {
                    'recommendation': sentiment_rec,
                    'confidence': sentiment_conf,
                    'score': round(sent_score, 3),
                    'weight': self.sentiment_weight,
                    'details': {
                        'overall': sentiment_analysis['overall_sentiment'],
                        'compound': sentiment_analysis['average_compound'],
                        'article_count': sentiment_analysis['article_count']
                    }
                }
            },
            'current_price': current_price,
            'targets': targets,
            'reasoning': reasoning,
            'timestamp': datetime.datetime.now().isoformat()
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

    def _generate_reasoning(self, technical: Dict, sentiment: Dict,
                           tech_rec: str, sent_rec: str, final_rec: str) -> str:
        """Generate human-readable reasoning for recommendation"""

        reasons = []

        # Technical reasoning
        rsi_val = technical['rsi']['value']
        rsi_signal = technical['rsi']['signal']
        macd_signal = technical['macd']['signal']

        if 'overbought' in rsi_signal:
            reasons.append(f"RSI is overbought at {rsi_val:.1f}, suggesting potential pullback")
        elif 'oversold' in rsi_signal:
            reasons.append(f"RSI is oversold at {rsi_val:.1f}, indicating potential bounce")
        else:
            reasons.append(f"RSI at {rsi_val:.1f} is in neutral territory")

        if 'crossover' in macd_signal:
            reasons.append(f"MACD shows {macd_signal.replace('_', ' ')}, a strong signal")
        elif 'bullish' in macd_signal:
            reasons.append("MACD indicates bullish momentum")
        elif 'bearish' in macd_signal:
            reasons.append("MACD indicates bearish momentum")

        # Moving average reasoning
        if 'ma_trend' in technical:
            ma_trend = technical['ma_trend']
            trend = ma_trend['overall_trend']
            bullish_ratio = ma_trend.get('bullish_ratio', 0.5)

            if trend == 'strong_uptrend':
                reasons.append(f"Price is in a strong uptrend ({bullish_ratio*100:.0f}% above key moving averages)")
            elif trend == 'uptrend':
                reasons.append(f"Price shows uptrend momentum (above {bullish_ratio*100:.0f}% of moving averages)")
            elif trend == 'downtrend':
                reasons.append(f"Price is in a downtrend (below {(1-bullish_ratio)*100:.0f}% of moving averages)")

        # Moving average crossovers
        if 'ma_crossovers' in technical:
            crossovers = technical['ma_crossovers']
            if crossovers.get('golden_cross'):
                reasons.append("GOLDEN CROSS detected (50 SMA crossed above 200 SMA) - very bullish!")
            elif crossovers.get('death_cross'):
                reasons.append("DEATH CROSS detected (50 SMA crossed below 200 SMA) - very bearish!")

            if crossovers.get('short_term_bullish_cross'):
                reasons.append("Short-term bullish crossover (9 EMA above 21 EMA)")
            elif crossovers.get('short_term_bearish_cross'):
                reasons.append("Short-term bearish crossover (9 EMA below 21 EMA)")

        # Sentiment reasoning
        sent_overall = sentiment['overall_sentiment']
        article_count = sentiment['article_count']
        compound = sentiment['average_compound']

        reasons.append(
            f"News sentiment is {sent_overall} "
            f"(score: {compound:.2f} from {article_count} articles)"
        )

        # Agreement/disagreement
        if tech_rec == sent_rec:
            reasons.append("Technical and sentiment analysis are in agreement")
        else:
            reasons.append(
                f"Technical analysis suggests {tech_rec}, "
                f"while sentiment suggests {sent_rec}"
            )

        return ". ".join(reasons) + "."

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
        """
        Format recommendation as human-readable text

        Args:
            recommendation: Recommendation dictionary

        Returns:
            Formatted string
        """
        rec = recommendation['recommendation'].replace('_', ' ').upper()
        conf = recommendation['confidence'] * 100
        price = recommendation['current_price']

        output = f"""
╔══════════════════════════════════════════════════════════════╗
║           BITCOIN PORTFOLIO ADVISOR RECOMMENDATION           ║
╚══════════════════════════════════════════════════════════════╝

Date/Time: {recommendation['timestamp']}
Current BTC Price: ${price:,.2f}

═══════════════════════════════════════════════════════════════

RECOMMENDATION: {rec}
Confidence Level: {conf:.0f}%

═══════════════════════════════════════════════════════════════

ANALYSIS BREAKDOWN:

Technical Analysis ({self.technical_weight * 100:.0f}% weight):
  → Recommendation: {recommendation['signals']['technical']['recommendation'].upper()}
  → Confidence: {recommendation['signals']['technical']['confidence'] * 100:.0f}%
  → RSI: {recommendation['signals']['technical']['details']['rsi']['value']}
     ({recommendation['signals']['technical']['details']['rsi']['signal']})
  → MACD: {recommendation['signals']['technical']['details']['macd']['signal']}

Sentiment Analysis ({self.sentiment_weight * 100:.0f}% weight):
  → Recommendation: {recommendation['signals']['sentiment']['recommendation'].upper()}
  → Confidence: {recommendation['signals']['sentiment']['confidence'] * 100:.0f}%
  → Overall Sentiment: {recommendation['signals']['sentiment']['details']['overall'].upper()}
  → News Articles Analyzed: {recommendation['signals']['sentiment']['details']['article_count']}
  → Sentiment Score: {recommendation['signals']['sentiment']['details']['compound']}

═══════════════════════════════════════════════════════════════

REASONING:
{recommendation['reasoning']}

═══════════════════════════════════════════════════════════════

SUGGESTED TARGETS:
"""
        # Add targets
        targets = recommendation['targets']
        if 'target_1' in targets:
            output += f"""
Entry Point: ${targets['entry']:,.2f}
Target 1: ${targets['target_1']:,.2f} ({((targets['target_1']/price - 1) * 100):+.1f}%)
Target 2: ${targets['target_2']:,.2f} ({((targets['target_2']/price - 1) * 100):+.1f}%)
Stop Loss: ${targets['stop_loss']:,.2f} ({((targets['stop_loss']/price - 1) * 100):+.1f}%)
"""
        else:
            output += f"""
Current Level: ${targets['entry']:,.2f}
Support: ${targets.get('support', 'N/A'):,.2f}
Resistance: ${targets.get('resistance', 'N/A'):,.2f}
"""

        output += """
═══════════════════════════════════════════════════════════════

DISCLAIMER: This is for educational purposes only. Not financial
advice. Always do your own research and never invest more than
you can afford to lose.

═══════════════════════════════════════════════════════════════
"""

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
