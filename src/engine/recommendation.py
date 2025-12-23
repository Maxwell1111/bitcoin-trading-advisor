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

    def _analyze_rsi(self, rsi_value: float) -> Tuple[float, str]:
        """
        Analyze RSI for overbought/oversold conditions
        Returns: (score from -1 to 1, signal description)
        """
        if rsi_value >= 70:
            # Overbought - bearish signal
            severity = min((rsi_value - 70) / 30, 1.0)  # Scale 70-100 to 0-1
            return (-0.5 - severity * 0.5, f"Overbought (RSI: {rsi_value:.1f})")
        elif rsi_value <= 30:
            # Oversold - bullish signal
            severity = min((30 - rsi_value) / 30, 1.0)  # Scale 0-30 to 1-0
            return (0.5 + severity * 0.5, f"Oversold (RSI: {rsi_value:.1f})")
        elif 40 <= rsi_value <= 60:
            # Neutral zone
            return (0.0, f"Neutral (RSI: {rsi_value:.1f})")
        elif rsi_value > 60:
            # Moderately overbought
            return (-0.3, f"Moderate strength (RSI: {rsi_value:.1f})")
        else:
            # Moderately oversold
            return (0.3, f"Moderate weakness (RSI: {rsi_value:.1f})")

    def _analyze_moving_averages(self, current_price: float, technical_analysis: Dict,
                                 ma_trend: str, ma_crossovers: Dict) -> Tuple[float, str]:
        """
        Analyze moving average trends and crossovers
        Returns: (score from -1 to 1, signal description)
        """
        score = 0.0
        signals = []

        # Check trend
        if ma_trend == 'strong_bullish':
            score += 0.8
            signals.append("Strong uptrend")
        elif ma_trend == 'bullish':
            score += 0.5
            signals.append("Uptrend")
        elif ma_trend == 'bearish':
            score -= 0.5
            signals.append("Downtrend")
        elif ma_trend == 'strong_bearish':
            score -= 0.8
            signals.append("Strong downtrend")

        # Check for golden/death cross
        if ma_crossovers.get('golden_cross'):
            score += 0.3
            signals.append("Golden Cross")
        if ma_crossovers.get('death_cross'):
            score -= 0.3
            signals.append("Death Cross")

        # Check 21-week EMA (Bull Market Support Band)
        moving_averages = technical_analysis.get('moving_averages', {})
        ema_21week = moving_averages.get('ema_147')
        if ema_21week:
            if current_price > ema_21week * 1.05:
                score += 0.2
                signals.append("Above 21W EMA")
            elif current_price < ema_21week * 0.95:
                score -= 0.2
                signals.append("Below 21W EMA")

        score = max(-1.0, min(1.0, score))  # Clamp to [-1, 1]
        signal_text = ", ".join(signals) if signals else "Neutral MA structure"

        return (score, signal_text)

    def _analyze_power_law(self, status: str, current_price: float, fair_value: float,
                          power_law_analysis: Dict) -> Tuple[float, str]:
        """
        Analyze Power Law positioning
        Returns: (score from -1 to 1, signal description)
        """
        deviation = ((current_price - fair_value) / fair_value) * 100

        if status == "Deep Value":
            # Strong buy signal - historically great entry
            return (1.0, f"Deep Value: {deviation:.1f}% below fair value")
        elif status == "Bubble Risk":
            # Strong sell signal - historically peaks
            return (-1.0, f"Bubble Risk: {deviation:.1f}% above fair value")
        elif deviation < -20:
            # Undervalued
            return (0.6, f"Undervalued: {deviation:.1f}% below fair value")
        elif deviation < -10:
            # Slightly undervalued
            return (0.3, f"Below fair value: {deviation:.1f}%")
        elif deviation > 50:
            # Significantly overvalued
            return (-0.7, f"Overvalued: +{deviation:.1f}% above fair value")
        elif deviation > 20:
            # Moderately overvalued
            return (-0.4, f"Above fair value: +{deviation:.1f}%")
        else:
            # Near fair value
            return (0.1, f"Fair Value Zone: {deviation:+.1f}%")

    def _analyze_macd(self, macd: Dict) -> Tuple[float, str]:
        """
        Analyze MACD momentum
        Returns: (score from -1 to 1, signal description)
        """
        signal = macd.get('signal', 'neutral')
        histogram = macd.get('histogram', 0)

        if signal == 'bullish':
            # Histogram magnitude indicates strength
            strength = min(abs(histogram) / 1000, 1.0) if histogram else 0.5
            return (0.3 + strength * 0.4, "Bullish momentum")
        elif signal == 'bearish':
            strength = min(abs(histogram) / 1000, 1.0) if histogram else 0.5
            return (-0.3 - strength * 0.4, "Bearish momentum")
        else:
            return (0.0, "Neutral momentum")

    def _analyze_sentiment(self, reddit_score: float, news_score: float) -> Tuple[float, str]:
        """
        Analyze market sentiment with contrarian adjustments
        Returns: (score from -1 to 1, signal description)
        """
        avg_sentiment = (reddit_score + news_score) / 2

        # Extreme sentiment gets contrarian treatment
        if reddit_score > 0.85 or news_score > 0.85:
            return (-0.6, f"Extreme euphoria (contrarian bearish)")
        elif reddit_score < 0.15 or news_score < 0.15:
            return (0.6, f"Extreme fear (contrarian bullish)")
        elif avg_sentiment > 0.6:
            return (0.4, f"Positive sentiment")
        elif avg_sentiment > 0.3:
            return (0.2, f"Moderately positive")
        elif avg_sentiment < -0.3:
            return (-0.4, f"Negative sentiment")
        elif avg_sentiment < -0.1:
            return (-0.2, f"Moderately negative")
        else:
            return (0.0, f"Neutral sentiment")

    def _analyze_signal_confluence(self, rsi_signal: str, ma_signal: str,
                                   pl_signal: str, macd_signal: str,
                                   sentiment_signal: str) -> str:
        """
        Analyze whether signals are in agreement or diverging
        """
        signals_summary = [
            f"• RSI: {rsi_signal}",
            f"• Moving Averages: {ma_signal}",
            f"• Power Law: {pl_signal}",
            f"• MACD: {macd_signal}",
            f"• Sentiment: {sentiment_signal}"
        ]

        return "\n".join(signals_summary)

    def generate_recommendation(self, power_law_analysis: Dict,
                               technical_analysis: Dict,
                               news_sentiment_analysis: Dict,
                               reddit_sentiment_analysis: Dict,
                               current_price: float) -> Dict:
        """
        Generate holistic trading recommendation based on multiple factors:
        - RSI levels and momentum
        - Moving average trends and crossovers
        - Power Law macro positioning
        - Historical pattern recognition
        - Market sentiment (as one factor, not dominant)
        """
        logging.info("--- Holistic Recommendation Engine ---")
        logging.info(f"Analyzing multiple factors for comprehensive recommendation")

        # Extract key metrics
        rsi = technical_analysis.get('rsi', {})
        rsi_value = rsi.get('value', 50)
        macd = technical_analysis.get('macd', {})
        ma_trend = technical_analysis.get('ma_trend', 'neutral')
        ma_crossovers = technical_analysis.get('ma_crossovers', {})

        power_law_status = power_law_analysis['status']
        power_law_fair_value = power_law_analysis['fair_value']

        reddit_score_raw = reddit_sentiment_analysis['average_compound']
        news_score_raw = news_sentiment_analysis['average_compound']

        # === HOLISTIC SCORING SYSTEM ===

        # 1. RSI Analysis (Weight: 20%)
        rsi_score, rsi_signal = self._analyze_rsi(rsi_value)
        logging.info(f"RSI Score: {rsi_score:.2f} | Signal: {rsi_signal}")

        # 2. Moving Average Analysis (Weight: 25%)
        ma_score, ma_signal = self._analyze_moving_averages(current_price, technical_analysis, ma_trend, ma_crossovers)
        logging.info(f"MA Score: {ma_score:.2f} | Signal: {ma_signal}")

        # 3. Power Law Analysis (Weight: 25%)
        pl_score, pl_signal = self._analyze_power_law(power_law_status, current_price, power_law_fair_value, power_law_analysis)
        logging.info(f"Power Law Score: {pl_score:.2f} | Signal: {pl_signal}")

        # 4. MACD Momentum (Weight: 15%)
        macd_score, macd_signal = self._analyze_macd(macd)
        logging.info(f"MACD Score: {macd_score:.2f} | Signal: {macd_signal}")

        # 5. Sentiment Analysis (Weight: 15%) - reduced from dominant position
        sentiment_score, sentiment_signal = self._analyze_sentiment(reddit_score_raw, news_score_raw)
        logging.info(f"Sentiment Score: {sentiment_score:.2f} | Signal: {sentiment_signal}")

        # Calculate weighted composite score
        composite_score = (
            rsi_score * 0.20 +
            ma_score * 0.25 +
            pl_score * 0.25 +
            macd_score * 0.15 +
            sentiment_score * 0.15
        )

        logging.info(f"Composite Score: {composite_score:.2f}")

        # Generate divergence/confluence analysis
        divergence_signal = self._analyze_signal_confluence(
            rsi_signal, ma_signal, pl_signal, macd_signal, sentiment_signal
        )

        # Convert composite score to recommendation
        recommendation, confidence = self._score_to_recommendation(composite_score)

        # Generate detailed reasoning
        reasoning = self._generate_holistic_reasoning(
            rsi_signal, ma_signal, pl_signal, macd_signal, sentiment_signal,
            composite_score, recommendation
        )

        # For backward compatibility, also calculate legacy scores
        technical_rec = technical_analysis['overall']['recommendation']
        technical_conf = technical_analysis['overall']['confidence']
        news_rec = news_sentiment_analysis['recommendation']
        news_conf = news_sentiment_analysis['confidence']
        reddit_rec = reddit_sentiment_analysis['recommendation']
        reddit_conf = reddit_sentiment_analysis['confidence']

        tech_score = self._recommendation_to_score(technical_rec) * technical_conf
        news_score = self._recommendation_to_score(news_rec) * news_conf
        reddit_score = self._recommendation_to_score(reddit_rec) * reddit_conf

        # Legacy combined score for display
        combined_sentiment = {
            'recommendation': reddit_rec if reddit_conf > news_conf else news_rec,
            'confidence': max(reddit_conf, news_conf)
        }

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
            'composite_score': round(composite_score, 3),
            'combined_score': round(composite_score, 3),  # Alias for backward compatibility
            'reasoning': reasoning,
            'current_price': current_price,
            'timestamp': datetime.datetime.now().isoformat(),
            'targets': targets,
            'divergence_signal': divergence_signal,
            'factor_scores': {
                'rsi': round(rsi_score, 3),
                'moving_averages': round(ma_score, 3),
                'power_law': round(pl_score, 3),
                'macd': round(macd_score, 3),
                'sentiment': round(sentiment_score, 3)
            },
            'factor_weights': {
                'rsi': 0.20,
                'moving_averages': 0.25,
                'power_law': 0.25,
                'macd': 0.15,
                'sentiment': 0.15
            },
            'power_law_data': {
                'fair_value': power_law_analysis['fair_value'],
                'support_value': power_law_analysis['support_value'],
                'resistance_value': power_law_analysis['resistance_value'],
                'status': power_law_analysis['status']
            },
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
                },
                'reddit_sentiment': {
                    'recommendation': reddit_rec,
                    'confidence': reddit_conf,
                    'details': reddit_sentiment_analysis
                },
                'news_sentiment': {
                    'recommendation': news_rec,
                    'confidence': news_conf,
                    'details': news_sentiment_analysis
                }
            }
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

    def _create_power_law_alert(self, message: str, alert_type: str, current_price: float, power_law_analysis: Dict) -> Dict:
        """Creates a special dictionary for power law alerts."""
        return {
            'recommendation': 'POWER_LAW_ALERT',
            'confidence': 1.0,
            'reasoning': message,
            'alert_type': alert_type,
            'current_price': current_price,
            'timestamp': datetime.datetime.now().isoformat(),
            'power_law_data': {
                'fair_value': power_law_analysis['fair_value'],
                'support_value': power_law_analysis['support_value'],
                'resistance_value': power_law_analysis['resistance_value'],
                'status': power_law_analysis['status']
            },
            'targets': {},
            'signals': {}
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

    def _generate_holistic_reasoning(self, rsi_signal: str, ma_signal: str,
                                     pl_signal: str, macd_signal: str,
                                     sentiment_signal: str, composite_score: float,
                                     recommendation: str) -> str:
        """Generate comprehensive reasoning based on all factors."""

        reasoning_parts = []

        # Start with the overall assessment
        reasoning_parts.append(f"Holistic Analysis - {recommendation.replace('_', ' ').upper()}")
        reasoning_parts.append("")

        # Explain each factor
        reasoning_parts.append(f"📊 Technical Indicators:")
        reasoning_parts.append(f"  • RSI: {rsi_signal}")
        reasoning_parts.append(f"  • MACD: {macd_signal}")
        reasoning_parts.append(f"  • Moving Averages: {ma_signal}")
        reasoning_parts.append("")

        reasoning_parts.append(f"📈 Macro Analysis:")
        reasoning_parts.append(f"  • Power Law: {pl_signal}")
        reasoning_parts.append("")

        reasoning_parts.append(f"🗣️ Market Sentiment:")
        reasoning_parts.append(f"  • {sentiment_signal}")
        reasoning_parts.append("")

        # Composite score interpretation
        score_pct = composite_score * 100
        if composite_score > 0.7:
            reasoning_parts.append(f"✅ Strong confluence of bullish signals (score: {score_pct:+.0f})")
        elif composite_score > 0.3:
            reasoning_parts.append(f"↗️ Moderately bullish setup (score: {score_pct:+.0f})")
        elif composite_score < -0.7:
            reasoning_parts.append(f"❌ Strong confluence of bearish signals (score: {score_pct:+.0f})")
        elif composite_score < -0.3:
            reasoning_parts.append(f"↘️ Moderately bearish setup (score: {score_pct:+.0f})")
        else:
            reasoning_parts.append(f"➡️ Neutral / Mixed signals (score: {score_pct:+.0f})")

        return "\n".join(reasoning_parts)

    def _generate_reasoning(self, technical: Dict, news: Dict, reddit: Dict, divergence: str, final_rec: str) -> str:
        """Legacy method - kept for backward compatibility."""
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

        # Handle Power Law Alert
        if recommendation.get('recommendation') == 'POWER_LAW_ALERT':
            pl_data = recommendation.get('power_law_data', {})
            return f"""
╔══════════════════════════════════════════════════════════════╗
║              BITCOIN POWER LAW ANALYSIS ALERT                ║
╚══════════════════════════════════════════════════════════════╝

Date/Time: {recommendation['timestamp']}
Current BTC Price: ${recommendation['current_price']:,.2f}

═══════════════════════════════════════════════════════════════

{recommendation.get('alert_type', '').upper()}

POWER LAW CORRIDOR LEVELS:
  Resistance (Bubble Risk): ${pl_data.get('resistance_value', 0):,.2f}
  Fair Value:               ${pl_data.get('fair_value', 0):,.2f}
  Support (Deep Value):     ${pl_data.get('support_value', 0):,.2f}

═══════════════════════════════════════════════════════════════

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

POWER LAW MACRO ANALYSIS:

Status: {recommendation['power_law_data']['status']}
  → Current Price:     ${price:,.2f}
  → Fair Value:        ${recommendation['power_law_data']['fair_value']:,.2f}
  → Support Level:     ${recommendation['power_law_data']['support_value']:,.2f}
  → Resistance Level:  ${recommendation['power_law_data']['resistance_value']:,.2f}

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
