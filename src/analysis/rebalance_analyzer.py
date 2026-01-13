"""
Bitcoin/Gold Rebalancing Analyzer

Analyzes momentum and volatility indicators to generate rebalancing signals
between Bitcoin and Gold allocations.
"""

import numpy as np
import pandas as pd


class RebalanceAnalyzer:
    """
    Generates rebalancing signals between Bitcoin and Gold based on:
    - Momentum indicators (RSI, MACD, Rate of Change)
    - Volatility indicators (ATR, Bollinger Bands, Historical Volatility)
    - Correlation analysis
    - Relative strength comparison
    """

    def __init__(
        self,
        rsi_period: int = 14,
        atr_period: int = 14,
        bb_period: int = 20,
        bb_std: float = 2.0,
        momentum_period: int = 10,
        correlation_window: int = 30,
    ):
        """
        Initialize rebalance analyzer

        Args:
            rsi_period: RSI calculation period
            atr_period: ATR calculation period
            bb_period: Bollinger Bands period
            bb_std: Bollinger Bands standard deviation multiplier
            momentum_period: Rate of change period
            correlation_window: Rolling correlation window
        """
        self.rsi_period = rsi_period
        self.atr_period = atr_period
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.momentum_period = momentum_period
        self.correlation_window = correlation_window

    # ===== MOMENTUM INDICATORS =====

    def calculate_rsi(self, prices: pd.Series) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = prices.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(window=self.rsi_period, min_periods=1).mean()
        avg_loss = loss.rolling(window=self.rsi_period, min_periods=1).mean()

        rs = avg_gain / avg_loss.replace(0, np.inf)
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_macd(self, prices: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD (12, 26, 9)"""
        ema_12 = prices.ewm(span=12, adjust=False).mean()
        ema_26 = prices.ewm(span=26, adjust=False).mean()
        macd_line = ema_12 - ema_26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    def calculate_roc(self, prices: pd.Series) -> pd.Series:
        """Calculate Rate of Change (momentum)"""
        return (
            (prices - prices.shift(self.momentum_period)) / prices.shift(self.momentum_period)
        ) * 100

    # ===== VOLATILITY INDICATORS =====

    def calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
        """Calculate Average True Range"""
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return true_range.rolling(window=self.atr_period).mean()

    def calculate_bollinger_bands(
        self, prices: pd.Series
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands"""
        middle = prices.rolling(window=self.bb_period).mean()
        std = prices.rolling(window=self.bb_period).std()
        upper = middle + (std * self.bb_std)
        lower = middle - (std * self.bb_std)
        return upper, middle, lower

    def calculate_historical_volatility(self, prices: pd.Series, window: int = 20) -> pd.Series:
        """Calculate annualized historical volatility"""
        log_returns = np.log(prices / prices.shift(1))
        return log_returns.rolling(window=window).std() * np.sqrt(252) * 100

    def calculate_volatility_ratio(self, btc_vol: float, gold_vol: float) -> float:
        """Calculate BTC/Gold volatility ratio"""
        if gold_vol == 0:
            return float("inf")
        return btc_vol / gold_vol

    # ===== CORRELATION & RELATIVE STRENGTH =====

    def calculate_correlation(self, btc_prices: pd.Series, gold_prices: pd.Series) -> pd.Series:
        """Calculate rolling correlation between BTC and Gold"""
        # Align the indices
        combined = pd.DataFrame({"btc": btc_prices, "gold": gold_prices}).dropna()
        if len(combined) < self.correlation_window:
            return pd.Series([np.nan] * len(btc_prices))

        btc_returns = combined["btc"].pct_change()
        gold_returns = combined["gold"].pct_change()
        return btc_returns.rolling(window=self.correlation_window).corr(gold_returns)

    def calculate_relative_strength(
        self, btc_prices: pd.Series, gold_prices: pd.Series
    ) -> pd.Series:
        """Calculate BTC/Gold ratio for relative strength"""
        return btc_prices / gold_prices

    def calculate_relative_strength_momentum(self, rs_ratio: pd.Series) -> dict:
        """Analyze momentum of BTC/Gold ratio"""
        if len(rs_ratio) < 20:
            return {"trend": "insufficient_data", "momentum": 0}

        current = rs_ratio.iloc[-1]
        sma_20 = rs_ratio.rolling(20).mean().iloc[-1]
        roc = (
            ((current - rs_ratio.iloc[-10]) / rs_ratio.iloc[-10]) * 100
            if len(rs_ratio) >= 10
            else 0
        )

        if current > sma_20 and roc > 0:
            trend = "btc_outperforming"
        elif current < sma_20 and roc < 0:
            trend = "gold_outperforming"
        else:
            trend = "neutral"

        return {
            "trend": trend,
            "current_ratio": round(current, 4),
            "sma_20": round(sma_20, 4),
            "momentum_roc": round(roc, 2),
        }

    # ===== MAIN ANALYSIS =====

    def analyze(self, btc_data: pd.DataFrame, gold_data: pd.DataFrame) -> dict:
        """
        Perform full rebalancing analysis

        Args:
            btc_data: Bitcoin OHLCV DataFrame
            gold_data: Gold OHLCV DataFrame

        Returns:
            Dictionary with rebalancing recommendation and details
        """
        # Normalize timezones - convert to date-only index for alignment
        btc_data = btc_data.copy()
        gold_data = gold_data.copy()

        # Convert to date-only (remove time and timezone) for proper alignment
        btc_data.index = pd.to_datetime(btc_data.index).tz_localize(None).normalize()
        gold_data.index = pd.to_datetime(gold_data.index).tz_localize(None).normalize()

        # Remove any duplicate dates (keep last)
        btc_data = btc_data[~btc_data.index.duplicated(keep="last")]
        gold_data = gold_data[~gold_data.index.duplicated(keep="last")]

        # Align data by date
        btc_close = btc_data["close"]
        gold_close = gold_data["close"]

        # Use common dates
        common_idx = btc_close.index.intersection(gold_close.index)
        if len(common_idx) < 30:
            return self._insufficient_data_response()

        btc_close = btc_close.loc[common_idx]
        gold_close = gold_close.loc[common_idx]
        btc_aligned = btc_data.loc[common_idx]
        gold_aligned = gold_data.loc[common_idx]

        # === BITCOIN ANALYSIS ===
        btc_rsi = self.calculate_rsi(btc_close)
        btc_macd, btc_signal, btc_hist = self.calculate_macd(btc_close)
        btc_roc = self.calculate_roc(btc_close)
        btc_atr = self.calculate_atr(btc_aligned["high"], btc_aligned["low"], btc_close)
        btc_bb_upper, btc_bb_mid, btc_bb_lower = self.calculate_bollinger_bands(btc_close)
        btc_vol = self.calculate_historical_volatility(btc_close)

        # === GOLD ANALYSIS ===
        gold_rsi = self.calculate_rsi(gold_close)
        gold_macd, gold_signal, gold_hist = self.calculate_macd(gold_close)
        gold_roc = self.calculate_roc(gold_close)
        gold_atr = self.calculate_atr(gold_aligned["high"], gold_aligned["low"], gold_close)
        gold_bb_upper, gold_bb_mid, gold_bb_lower = self.calculate_bollinger_bands(gold_close)
        gold_vol = self.calculate_historical_volatility(gold_close)

        # === CORRELATION & RELATIVE STRENGTH ===
        correlation = self.calculate_correlation(btc_close, gold_close)
        rs_ratio = self.calculate_relative_strength(btc_close, gold_close)
        rs_momentum = self.calculate_relative_strength_momentum(rs_ratio)

        # Get current values
        btc_current = {
            "price": round(btc_close.iloc[-1], 2),
            "rsi": round(btc_rsi.iloc[-1], 2),
            "macd_histogram": round(btc_hist.iloc[-1], 2),
            "roc": round(btc_roc.iloc[-1], 2) if not pd.isna(btc_roc.iloc[-1]) else 0,
            "volatility": round(btc_vol.iloc[-1], 2) if not pd.isna(btc_vol.iloc[-1]) else 0,
            "atr": round(btc_atr.iloc[-1], 2) if not pd.isna(btc_atr.iloc[-1]) else 0,
            "bb_position": self._bb_position(
                btc_close.iloc[-1],
                btc_bb_upper.iloc[-1],
                btc_bb_mid.iloc[-1],
                btc_bb_lower.iloc[-1],
            ),
        }

        gold_current = {
            "price": round(gold_close.iloc[-1], 2),
            "rsi": round(gold_rsi.iloc[-1], 2),
            "macd_histogram": round(gold_hist.iloc[-1], 2),
            "roc": round(gold_roc.iloc[-1], 2) if not pd.isna(gold_roc.iloc[-1]) else 0,
            "volatility": round(gold_vol.iloc[-1], 2) if not pd.isna(gold_vol.iloc[-1]) else 0,
            "atr": round(gold_atr.iloc[-1], 2) if not pd.isna(gold_atr.iloc[-1]) else 0,
            "bb_position": self._bb_position(
                gold_close.iloc[-1],
                gold_bb_upper.iloc[-1],
                gold_bb_mid.iloc[-1],
                gold_bb_lower.iloc[-1],
            ),
        }

        current_correlation = correlation.iloc[-1] if not pd.isna(correlation.iloc[-1]) else 0
        vol_ratio = self.calculate_volatility_ratio(
            btc_current["volatility"], gold_current["volatility"]
        )

        # Generate rebalancing signal
        signal = self._generate_signal(
            btc_current, gold_current, current_correlation, vol_ratio, rs_momentum
        )

        return {
            "recommendation": signal["recommendation"],
            "confidence": signal["confidence"],
            "suggested_allocation": signal["allocation"],
            "reasoning": signal["reasoning"],
            "bitcoin": {
                "current": btc_current,
                "momentum": self._interpret_momentum(btc_current),
                "volatility_status": self._interpret_volatility(btc_current["volatility"], "btc"),
            },
            "gold": {
                "current": gold_current,
                "momentum": self._interpret_momentum(gold_current),
                "volatility_status": self._interpret_volatility(gold_current["volatility"], "gold"),
            },
            "correlation": {
                "current": round(current_correlation, 3),
                "interpretation": self._interpret_correlation(current_correlation),
            },
            "relative_strength": rs_momentum,
            "volatility_ratio": round(vol_ratio, 2),
            "risk_assessment": self._assess_risk(btc_current, gold_current, vol_ratio),
        }

    def _bb_position(self, price: float, upper: float, mid: float, lower: float) -> str:
        """Determine Bollinger Band position"""
        if pd.isna(upper) or pd.isna(lower):
            return "unknown"
        if price >= upper:
            return "above_upper"
        if price <= lower:
            return "below_lower"
        if price > mid:
            return "upper_half"
        return "lower_half"

    def _interpret_momentum(self, indicators: dict) -> str:
        """Interpret momentum indicators"""
        score = 0

        # RSI
        if indicators["rsi"] > 70:
            score -= 1  # Overbought
        elif indicators["rsi"] < 30:
            score += 1  # Oversold
        elif indicators["rsi"] > 50:
            score += 0.5

        # MACD Histogram
        if indicators["macd_histogram"] > 0:
            score += 0.5
        else:
            score -= 0.5

        # ROC
        if indicators["roc"] > 5:
            score += 1
        elif indicators["roc"] < -5:
            score -= 1

        if score >= 1.5:
            return "strong_bullish"
        if score >= 0.5:
            return "bullish"
        if score <= -1.5:
            return "strong_bearish"
        if score <= -0.5:
            return "bearish"
        return "neutral"

    def _interpret_volatility(self, vol: float, asset: str) -> str:
        """Interpret volatility level"""
        if asset == "btc":
            if vol > 80:
                return "extreme"
            if vol > 60:
                return "high"
            if vol > 40:
                return "moderate"
            return "low"
        # gold
        if vol > 25:
            return "high"
        if vol > 15:
            return "moderate"
        return "low"

    def _interpret_correlation(self, corr: float) -> str:
        """Interpret correlation value"""
        if corr > 0.7:
            return "strong_positive"
        if corr > 0.3:
            return "moderate_positive"
        if corr > -0.3:
            return "weak_or_none"
        if corr > -0.7:
            return "moderate_negative"
        return "strong_negative"

    def _assess_risk(self, btc: dict, gold: dict, vol_ratio: float) -> dict:
        """Assess overall portfolio risk"""
        btc_risk = (
            "high" if btc["volatility"] > 60 or btc["rsi"] > 75 or btc["rsi"] < 25 else "moderate"
        )
        gold_risk = "low" if gold["volatility"] < 20 else "moderate"

        if vol_ratio > 5:
            diversification_benefit = "high"
        elif vol_ratio > 3:
            diversification_benefit = "moderate"
        else:
            diversification_benefit = "low"

        return {
            "btc_risk": btc_risk,
            "gold_risk": gold_risk,
            "diversification_benefit": diversification_benefit,
            "overall": "elevated" if btc_risk == "high" else "moderate",
        }

    def _generate_signal(
        self, btc: dict, gold: dict, correlation: float, vol_ratio: float, rs_momentum: dict
    ) -> dict:
        """Generate the rebalancing signal with confidence interval"""
        btc_score = 0
        gold_score = 0
        reasons = []

        # 1. Momentum comparison
        btc_mom = self._interpret_momentum(btc)
        gold_mom = self._interpret_momentum(gold)

        if btc_mom in ["strong_bullish", "bullish"] and gold_mom in ["bearish", "strong_bearish"]:
            btc_score += 2
            reasons.append("BTC showing stronger momentum than Gold")
        elif gold_mom in ["strong_bullish", "bullish"] and btc_mom in ["bearish", "strong_bearish"]:
            gold_score += 2
            reasons.append("Gold showing stronger momentum than BTC")

        # 2. RSI extremes (contrarian)
        if btc["rsi"] > 75:
            gold_score += 1.5
            reasons.append("BTC overbought (RSI > 75), consider rotating to Gold")
        elif btc["rsi"] < 25:
            btc_score += 1.5
            reasons.append("BTC oversold (RSI < 25), accumulation opportunity")

        if gold["rsi"] > 75:
            btc_score += 1
            reasons.append("Gold overbought, consider rotating to BTC")
        elif gold["rsi"] < 25:
            gold_score += 1
            reasons.append("Gold oversold, accumulation opportunity")

        # 3. Volatility adjustment
        if btc["volatility"] > 70:
            gold_score += 1
            reasons.append("BTC volatility elevated, Gold offers stability")
        elif btc["volatility"] < 40:
            btc_score += 0.5
            reasons.append("BTC volatility subdued, favorable risk environment")

        # 4. Relative strength trend
        if rs_momentum["trend"] == "btc_outperforming":
            btc_score += 1
            reasons.append("BTC outperforming Gold on relative strength")
        elif rs_momentum["trend"] == "gold_outperforming":
            gold_score += 1
            reasons.append("Gold outperforming BTC on relative strength")

        # 5. Bollinger Band positions
        if btc["bb_position"] == "below_lower":
            btc_score += 1
            reasons.append("BTC at lower Bollinger Band - potential bounce")
        elif btc["bb_position"] == "above_upper":
            gold_score += 0.5
            reasons.append("BTC extended at upper Bollinger Band")

        # 6. Correlation-based diversification
        if correlation < 0.2:
            reasons.append(f"Low correlation ({correlation:.2f}) - good diversification benefit")

        # Calculate net score and recommendation
        net_score = btc_score - gold_score
        total_score = btc_score + gold_score

        # Base allocation: 50/50
        base_btc = 50
        base_gold = 50

        # Adjust based on score (max ±25% swing)
        adjustment = min(abs(net_score) * 5, 25)

        if net_score > 0:
            suggested_btc = min(base_btc + adjustment, 75)
            suggested_gold = max(base_gold - adjustment, 25)
            recommendation = "increase_btc" if net_score > 1 else "slight_increase_btc"
        elif net_score < 0:
            suggested_btc = max(base_btc - adjustment, 25)
            suggested_gold = min(base_gold + adjustment, 75)
            recommendation = "increase_gold" if net_score < -1 else "slight_increase_gold"
        else:
            suggested_btc = 50
            suggested_gold = 50
            recommendation = "hold_current"

        # Confidence calculation
        if total_score == 0:
            confidence = 0.5
        else:
            confidence = min(0.5 + (abs(net_score) / total_score) * 0.4, 0.95)

        # Add confidence interval (using simple standard error approximation)
        confidence_interval = {
            "lower": round(max(confidence - 0.15, 0.1), 2),
            "upper": round(min(confidence + 0.15, 0.99), 2),
        }

        return {
            "recommendation": recommendation,
            "confidence": round(confidence, 2),
            "confidence_interval": confidence_interval,
            "allocation": {
                "btc_pct": round(suggested_btc, 1),
                "gold_pct": round(suggested_gold, 1),
            },
            "reasoning": (
                ". ".join(reasons)
                if reasons
                else "Balanced indicators suggest maintaining current allocation."
            ),
            "scores": {
                "btc_score": round(btc_score, 2),
                "gold_score": round(gold_score, 2),
                "net_score": round(net_score, 2),
            },
        }

    def generate_rebalance_signal(
        self,
        btc_data: pd.DataFrame,
        gold_data: pd.DataFrame,
        current_btc_pct: float = 100.0,
        current_gold_pct: float = 0.0,
        target_btc_pct: float = 70.0,
        target_gold_pct: float = 30.0,
    ) -> dict:
        """
        Generate a rebalance signal for moving from current allocation to target.
        Uses Kelly Criterion principles for position sizing.

        Args:
            btc_data: Bitcoin OHLCV DataFrame
            gold_data: Gold OHLCV DataFrame
            current_btc_pct: Current BTC allocation (default 100%)
            current_gold_pct: Current Gold allocation (default 0%)
            target_btc_pct: Target BTC allocation (default 70% - Kelly optimal)
            target_gold_pct: Target Gold allocation (default 30%)

        Returns:
            Dictionary with rebalance signal and trigger conditions
        """
        # Get full analysis first
        analysis = self.analyze(btc_data, gold_data)

        if analysis.get("recommendation") == "insufficient_data":
            return {
                "should_rebalance_now": False,
                "urgency": "none",
                "confidence": 0,
                "error": "Insufficient data for analysis",
            }

        btc = analysis["bitcoin"]["current"]
        gold = analysis["gold"]["current"]
        btc_momentum = analysis["bitcoin"]["momentum"]
        gold_momentum = analysis["gold"]["momentum"]
        correlation = analysis["correlation"]["current"]
        vol_ratio = analysis["volatility_ratio"]

        # Calculate how much rebalancing is needed
        btc_to_sell_pct = current_btc_pct - target_btc_pct  # e.g., 100 - 70 = 30% to move

        # === TRIGGER CONDITIONS ===
        triggers = {
            "rsi_overbought": btc["rsi"] > 70,
            "rsi_extreme_overbought": btc["rsi"] > 80,
            "volatility_elevated": btc["volatility"] > 50,
            "volatility_extreme": btc["volatility"] > 70,
            "at_upper_bollinger": btc["bb_position"] == "above_upper",
            "gold_outperforming": analysis["relative_strength"]["trend"] == "gold_outperforming",
            "negative_momentum": btc_momentum in ["bearish", "strong_bearish"],
            "gold_positive_momentum": gold_momentum in ["bullish", "strong_bullish"],
            "low_correlation": correlation < 0.3,  # Good diversification opportunity
            "macd_bearish": btc["macd_histogram"] < 0,
        }

        # Count how many triggers are active
        active_triggers = sum(triggers.values())
        total_triggers = len(triggers)

        # === URGENCY CALCULATION ===
        urgency_score = 0

        # High priority triggers (worth 2 points each)
        if triggers["rsi_extreme_overbought"]:
            urgency_score += 2
        if triggers["volatility_extreme"]:
            urgency_score += 2
        if triggers["at_upper_bollinger"]:
            urgency_score += 2

        # Medium priority triggers (worth 1 point each)
        if triggers["rsi_overbought"]:
            urgency_score += 1
        if triggers["volatility_elevated"]:
            urgency_score += 1
        if triggers["gold_outperforming"]:
            urgency_score += 1
        if triggers["negative_momentum"]:
            urgency_score += 1
        if triggers["macd_bearish"]:
            urgency_score += 1

        # Low priority / supporting triggers (worth 0.5 points each)
        if triggers["low_correlation"]:
            urgency_score += 0.5
        if triggers["gold_positive_momentum"]:
            urgency_score += 0.5

        # Determine urgency level
        if urgency_score >= 5:
            urgency = "high"
        elif urgency_score >= 3:
            urgency = "medium"
        elif urgency_score >= 1:
            urgency = "low"
        else:
            urgency = "none"

        # === SHOULD REBALANCE NOW? ===
        # Rebalance if we have at least 2 active triggers
        should_rebalance = active_triggers >= 2 and urgency != "none"

        # === KELLY CRITERION POSITION SIZING ===
        # Simplified Kelly: f* = (p * b - q) / b
        # where p = win probability, q = 1-p, b = win/loss ratio
        # For rebalancing, we use volatility-adjusted sizing

        # Base rebalance amount (staged approach)
        if urgency == "high":
            base_rebalance_pct = min(15, btc_to_sell_pct)  # Up to 15% at once
        elif urgency == "medium":
            base_rebalance_pct = min(10, btc_to_sell_pct)  # Up to 10%
        elif urgency == "low":
            base_rebalance_pct = min(5, btc_to_sell_pct)  # Up to 5%
        else:
            base_rebalance_pct = 0

        # Kelly adjustment based on volatility ratio
        # Higher BTC volatility relative to gold = smaller position changes
        kelly_factor = min(1.0, 2.0 / vol_ratio) if vol_ratio > 0 else 1.0
        suggested_rebalance_pct = round(base_rebalance_pct * kelly_factor, 1)

        # === PRICE TARGETS ===
        current_btc_price = btc["price"]

        # Calculate price levels for rebalancing
        # These are rough guidelines based on current momentum
        price_targets = {
            "current_price": current_btc_price,
            "consider_rebalance_above": round(current_btc_price * 1.05, 2),  # +5%
            "strong_rebalance_above": round(current_btc_price * 1.10, 2),  # +10%
            "aggressive_rebalance_above": round(current_btc_price * 1.20, 2),  # +20%
            "hold_below": round(current_btc_price * 0.95, 2),  # -5%
        }

        # === BUILD REASONING ===
        reasons = []
        if triggers["rsi_overbought"]:
            reasons.append(f"BTC RSI at {btc['rsi']:.0f} (overbought)")
        if triggers["volatility_elevated"]:
            reasons.append(f"BTC volatility elevated at {btc['volatility']:.0f}%")
        if triggers["at_upper_bollinger"]:
            reasons.append("BTC at upper Bollinger Band - extended")
        if triggers["gold_outperforming"]:
            reasons.append("Gold showing relative strength vs BTC")
        if triggers["negative_momentum"]:
            reasons.append("BTC momentum turning negative")
        if triggers["low_correlation"]:
            reasons.append(f"Low correlation ({correlation:.2f}) - good diversification")

        if not reasons:
            reasons.append("No strong rebalance triggers currently active")

        # === CONFIDENCE CALCULATION ===
        confidence = min(0.5 + (active_triggers / total_triggers) * 0.5, 0.95)
        confidence_interval = {
            "lower": round(max(confidence - 0.12, 0.1), 2),
            "upper": round(min(confidence + 0.12, 0.99), 2),
        }

        # === NEW ALLOCATION AFTER REBALANCE ===
        new_btc_pct = current_btc_pct - suggested_rebalance_pct
        new_gold_pct = current_gold_pct + suggested_rebalance_pct

        return {
            "should_rebalance_now": should_rebalance,
            "urgency": urgency,
            "confidence": round(confidence, 2),
            "confidence_interval": confidence_interval,
            "current_allocation": {"btc_pct": current_btc_pct, "gold_pct": current_gold_pct},
            "target_allocation": {"btc_pct": target_btc_pct, "gold_pct": target_gold_pct},
            "remaining_to_target": {
                "btc_to_sell": round(current_btc_pct - target_btc_pct, 1),
                "gold_to_buy": round(target_gold_pct - current_gold_pct, 1),
            },
            "suggested_action": {
                "rebalance_pct": suggested_rebalance_pct,
                "new_btc_pct": round(new_btc_pct, 1),
                "new_gold_pct": round(new_gold_pct, 1),
                "action": (
                    f"Sell {suggested_rebalance_pct}% BTC, Buy {suggested_rebalance_pct}% Gold"
                    if suggested_rebalance_pct > 0
                    else "Hold current position"
                ),
            },
            "trigger_conditions": triggers,
            "active_triggers": active_triggers,
            "urgency_score": round(urgency_score, 1),
            "price_targets": price_targets,
            "reasoning": ". ".join(reasons),
            "indicators": {
                "btc_rsi": btc["rsi"],
                "btc_volatility": btc["volatility"],
                "btc_momentum": btc_momentum,
                "gold_rsi": gold["rsi"],
                "gold_momentum": gold_momentum,
                "correlation": correlation,
                "volatility_ratio": vol_ratio,
                "kelly_factor": round(kelly_factor, 2),
            },
        }

    def _insufficient_data_response(self) -> dict:
        """Return response when insufficient data"""
        return {
            "recommendation": "insufficient_data",
            "confidence": 0,
            "confidence_interval": {"lower": 0, "upper": 0},
            "suggested_allocation": {"btc_pct": 50, "gold_pct": 50},
            "reasoning": "Insufficient overlapping data for analysis. Need at least 30 days.",
            "bitcoin": None,
            "gold": None,
            "correlation": None,
            "relative_strength": None,
            "volatility_ratio": None,
            "risk_assessment": None,
        }


if __name__ == "__main__":
    # Test the analyzer
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    from src.data.gold_fetcher import GoldFetcher
    from src.data.price_fetcher import PriceFetcher

    print("Testing Rebalance Analyzer...\n")

    # Fetch data
    btc_fetcher = PriceFetcher(provider="yfinance")
    gold_fetcher = GoldFetcher()

    print("Fetching Bitcoin data...")
    btc_data = btc_fetcher.fetch_historical_data(days=90)

    print("Fetching Gold data...")
    gold_data = gold_fetcher.fetch_historical_data(days=90)

    # Analyze
    analyzer = RebalanceAnalyzer()
    result = analyzer.analyze(btc_data, gold_data)

    print("\n=== REBALANCING ANALYSIS ===\n")
    print(f"Recommendation: {result['recommendation'].upper()}")
    print(
        f"Confidence: {result['confidence'] * 100:.0f}% "
        f"(CI: {result['confidence_interval']['lower'] * 100:.0f}%-{result['confidence_interval']['upper'] * 100:.0f}%)"
    )
    print("\nSuggested Allocation:")
    print(f"  Bitcoin: {result['suggested_allocation']['btc_pct']}%")
    print(f"  Gold: {result['suggested_allocation']['gold_pct']}%")
    print(f"\nReasoning: {result['reasoning']}")
    print(
        f"\nCorrelation: {result['correlation']['current']} ({result['correlation']['interpretation']})"
    )
    print(f"Volatility Ratio (BTC/Gold): {result['volatility_ratio']}x")
