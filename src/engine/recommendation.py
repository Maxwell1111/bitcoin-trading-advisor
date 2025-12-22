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
                        'macd': technical_analysis['macd'],
                        'ma_trend': technical_analysis.get('ma_trend'),
                        'ma_crossovers': technical_analysis.get('ma_crossovers'),
                        'moving_averages': technical_analysis.get('moving_averages')
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

        # MOVING AVERAGES FIRST - Most important for macro trend
        if 'moving_averages' in technical and technical['moving_averages']:
            mas = technical['moving_averages']

            # 200-Day SMA Analysis (Bull/Bear Market Status)
            if 'sma_200' in mas:
                sma_200_val = mas['sma_200']['value']
                sma_200_pos = mas['sma_200']['price_vs_ma']
                sma_200_dist = mas['sma_200']['distance_pct']

                if sma_200_pos == 'above':
                    reasons.append(f"MACRO BULL MARKET: Price is {sma_200_dist:.1f}% above the 200-day SMA (${sma_200_val:,.0f}), confirming we're in a macro bull trend")
                else:
                    reasons.append(f"CRYPTO WINTER WARNING: Price is {abs(sma_200_dist):.1f}% below the 200-day SMA (${sma_200_val:,.0f}), indicating bear market territory")

            # 21-Week EMA Analysis (Bull Market Support Band)
            if 'ema_147' in mas:
                ema_21w_val = mas['ema_147']['value']
                ema_21w_pos = mas['ema_147']['price_vs_ma']
                ema_21w_dist = mas['ema_147']['distance_pct']

                if ema_21w_pos == 'above':
                    reasons.append(f"BULL MARKET SUPPORT intact: Price is {ema_21w_dist:.1f}% above the 21-week EMA (${ema_21w_val:,.0f}), a historically reliable support level in bull markets")
                else:
                    reasons.append(f"SUPPORT LOST: Price is {abs(ema_21w_dist):.1f}% below the 21-week EMA (${ema_21w_val:,.0f}), which historically signals weakening bull momentum")

            # 50-Day SMA (Medium-term trend)
            if 'sma_50' in mas:
                sma_50_val = mas['sma_50']['value']
                sma_50_pos = mas['sma_50']['price_vs_ma']
                sma_50_dist = mas['sma_50']['distance_pct']

                if sma_50_pos == 'above':
                    reasons.append(f"Medium-term trend is bullish with price {sma_50_dist:.1f}% above 50-day SMA (${sma_50_val:,.0f})")
                else:
                    reasons.append(f"Medium-term weakness with price {abs(sma_50_dist):.1f}% below 50-day SMA (${sma_50_val:,.0f})")

        # Moving average crossovers (CRITICAL SIGNALS)
        if 'ma_crossovers' in technical:
            crossovers = technical['ma_crossovers']
            if crossovers.get('golden_cross'):
                reasons.append("🌟 GOLDEN CROSS DETECTED: 50 SMA crossed above 200 SMA - historically this signals major bull runs ahead!")
            elif crossovers.get('death_cross'):
                reasons.append("☠️ DEATH CROSS DETECTED: 50 SMA crossed below 200 SMA - historically this precedes extended bear markets!")

            if crossovers.get('short_term_bullish_cross'):
                reasons.append("Short-term bullish crossover detected (9 EMA above 21 EMA)")
            elif crossovers.get('short_term_bearish_cross'):
                reasons.append("Short-term bearish crossover detected (9 EMA below 21 EMA)")

        # RSI and MACD (Supporting Indicators)
        rsi_val = technical['rsi']['value']
        rsi_signal = technical['rsi']['signal']
        macd_signal = technical['macd']['signal']

        if 'overbought' in rsi_signal:
            reasons.append(f"RSI is overbought at {rsi_val:.1f}, suggesting potential short-term pullback")
        elif 'oversold' in rsi_signal:
            reasons.append(f"RSI is oversold at {rsi_val:.1f}, indicating potential short-term bounce")
        else:
            reasons.append(f"RSI at {rsi_val:.1f} is in neutral territory")

        if 'crossover' in macd_signal:
            reasons.append(f"MACD shows {macd_signal.replace('_', ' ')}, confirming momentum shift")
        elif 'bullish' in macd_signal:
            reasons.append("MACD indicates bullish momentum")
        elif 'bearish' in macd_signal:
            reasons.append("MACD indicates bearish momentum")

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
