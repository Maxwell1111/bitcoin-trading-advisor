"""
Weight Optimizer Service

Recalculates adaptive signal weights daily based on historical performance.
Uses Kelly Criterion backtesting and Sharpe ratio optimization.

Runs daily at midnight UTC.

Usage:
    optimizer = WeightOptimizer(validation_service)
    asyncio.create_task(optimizer.run())
"""

import asyncio
import logging
import statistics
from datetime import datetime, timedelta
from datetime import time as dt_time
from typing import Optional

from ..database import get_db_session
from ..database.models import Recommendation, ValidationResult, WeightHistory
from .validation_service import ValidationService

logger = logging.getLogger(__name__)


class WeightOptimizer:
    """
    Optimizes signal weights based on historical performance

    Runs daily to:
    1. Calculate Sharpe ratios for each signal type
    2. Optimize weights using Sharpe ratios
    3. Apply Bayesian priors for cold start
    4. Check for mode changes (degraded_preferred)
    5. Save new weights to database
    """

    def __init__(
        self,
        validation_service: ValidationService,
        rolling_window_days: int = 30,
        cold_start_days: int = 30,
        smoothing_factor: float = 0.3,
        initial_weights: Optional[dict[str, float]] = None,
    ):
        """
        Initialize WeightOptimizer

        Args:
            validation_service: ValidationService for Sharpe calculations
            rolling_window_days: Days to look back for weight calculation (default: 30)
            cold_start_days: Days before fully data-driven (default: 30)
            smoothing_factor: Weight given to new calculation vs current (default: 0.3)
            initial_weights: Bayesian priors (default: tech=0.6, reddit=0.25, news=0.15)
        """
        self.validation_service = validation_service
        self.rolling_window = rolling_window_days
        self.cold_start_days = cold_start_days
        self.smoothing_factor = smoothing_factor

        self.initial_weights = initial_weights or {"technical": 0.60, "reddit": 0.25, "news": 0.15}

        self.last_run: Optional[datetime] = None
        self.optimization_count = 0

    async def _sleep_until_midnight_utc(self):
        """Calculate and sleep until next midnight UTC"""
        now = datetime.utcnow()

        # Calculate next midnight
        tomorrow = now.date() + timedelta(days=1)
        next_midnight = datetime.combine(tomorrow, dt_time.min)

        # Time to sleep
        sleep_seconds = (next_midnight - now).total_seconds()

        logger.info(f"Sleeping {sleep_seconds / 3600:.1f} hours until next midnight UTC")
        await asyncio.sleep(sleep_seconds)

    def _attribute_to_dominant_signal(self, rec: Recommendation) -> str:
        """
        Determine which signal dominated this recommendation

        Args:
            rec: Recommendation record

        Returns:
            'technical', 'reddit', or 'news'
        """
        weights = {
            "technical": rec.weight_technical,
            "reddit": rec.weight_reddit,
            "news": rec.weight_news,
        }

        # Return signal with highest weight
        return max(weights.items(), key=lambda x: x[1])[0]

    def _calculate_sharpe_by_signal(
        self, signal_type: str, window_start: datetime
    ) -> Optional[float]:
        """
        Calculate Sharpe ratio for a specific signal type

        Uses dominant signal attribution: if a recommendation's highest
        weight is 'technical', attribute its P&L to technical.

        Args:
            signal_type: 'technical', 'reddit', or 'news'
            window_start: Start of rolling window

        Returns:
            Sharpe ratio, or None if insufficient data
        """
        try:
            with get_db_session() as session:
                # Get validated recommendations
                validations = (
                    session.query(ValidationResult)
                    .join(Recommendation)
                    .filter(
                        Recommendation.timestamp >= window_start,
                        ValidationResult.validation_type == "standard_24h",
                        ValidationResult.outcome.in_(["success", "failure"]),
                        ValidationResult.pnl_pct.isnot(None),
                    )
                    .all()
                )

                if len(validations) < 10:
                    logger.warning(
                        f"Insufficient data for {signal_type}: {len(validations)} validations"
                    )
                    return None

                # Filter to recommendations dominated by this signal
                signal_pnls = []

                for val in validations:
                    dominant_signal = self._attribute_to_dominant_signal(val.recommendation)

                    if dominant_signal == signal_type:
                        signal_pnls.append(val.pnl_pct)

                if len(signal_pnls) < 5:
                    logger.warning(
                        f"Insufficient {signal_type} recommendations: {len(signal_pnls)}"
                    )
                    return None

                # Calculate Sharpe ratio
                mean_return = statistics.mean(signal_pnls)
                std_return = statistics.stdev(signal_pnls) if len(signal_pnls) > 1 else 0.001

                if std_return == 0:
                    std_return = 0.001

                # Daily risk-free rate
                risk_free_daily = self.validation_service.risk_free_rate / 365

                sharpe = (mean_return - risk_free_daily) / std_return

                logger.info(
                    f"Sharpe ratio for {signal_type}: {sharpe:.3f} "
                    f"(mean={mean_return:.4f}, std={std_return:.4f}, n={len(signal_pnls)})"
                )

                return sharpe

        except Exception as e:
            logger.error(f"Failed to calculate Sharpe for {signal_type}: {e}", exc_info=True)
            return None

    def _apply_bayesian_prior(
        self, calculated_weights: dict[str, float], days_of_data: int
    ) -> dict[str, float]:
        """
        Apply Bayesian prior for cold start smoothing

        Args:
            calculated_weights: Weights from Sharpe optimization
            days_of_data: Days since first recommendation

        Returns:
            Smoothed weights
        """
        if days_of_data < self.cold_start_days:
            # Strong prior (70% weight on initial beliefs)
            prior_weight = 0.7
        elif days_of_data < 90:
            # Linear transition from 70% to 0% over days 30-90
            prior_weight = 0.7 * (90 - days_of_data) / 60
        else:
            # Fully data-driven
            prior_weight = 0.0

        if prior_weight > 0:
            logger.info(f"Applying Bayesian prior: {prior_weight:.1%} weight on initial beliefs")

            smoothed = {}
            for signal in ["technical", "reddit", "news"]:
                smoothed[signal] = (
                    prior_weight * self.initial_weights[signal]
                    + (1 - prior_weight) * calculated_weights[signal]
                )

            return smoothed
        return calculated_weights

    def _normalize_weights(self, weights: dict[str, float]) -> dict[str, float]:
        """Ensure weights sum to 1.0"""
        total = sum(weights.values())

        if total == 0:
            return self.initial_weights.copy()

        return {k: v / total for k, v in weights.items()}

    async def _recalculate_weights(self):
        """
        Recalculate weights based on rolling window performance

        Main optimization logic:
        1. Calculate Sharpe ratios for each signal
        2. Normalize Sharpes to weights
        3. Apply Bayesian prior
        4. Apply smoothing
        5. Save to database
        """
        logger.info("=" * 60)
        logger.info("STARTING WEIGHT OPTIMIZATION")
        logger.info("=" * 60)

        try:
            window_start = datetime.utcnow() - timedelta(days=self.rolling_window)

            # Calculate Sharpe ratios
            sharpe_technical = self._calculate_sharpe_by_signal("technical", window_start)
            sharpe_reddit = self._calculate_sharpe_by_signal("reddit", window_start)
            sharpe_news = self._calculate_sharpe_by_signal("news", window_start)

            # Check if we have enough data
            sharpes = {"technical": sharpe_technical, "reddit": sharpe_reddit, "news": sharpe_news}

            # Replace None with 0 (treat as neutral if no data)
            sharpes = {k: (v if v is not None else 0.0) for k, v in sharpes.items()}

            # Ensure all Sharpes are positive for weighting
            # If negative, set to small positive (signal is unprofitable, give minimal weight)
            min_sharpe = 0.1  # Minimum weight even for bad signals
            sharpes_positive = {k: max(v, min_sharpe) for k, v in sharpes.items()}

            # Normalize Sharpes to weights
            total_sharpe = sum(sharpes_positive.values())
            calculated_weights = {k: v / total_sharpe for k, v in sharpes_positive.items()}

            logger.info(f"Calculated weights from Sharpe: {calculated_weights}")

            # Get days of data
            with get_db_session() as session:
                first_rec = (
                    session.query(Recommendation).order_by(Recommendation.timestamp.asc()).first()
                )

                days_of_data = (datetime.utcnow() - first_rec.timestamp).days if first_rec else 0

            # Apply Bayesian prior
            prior_adjusted = self._apply_bayesian_prior(calculated_weights, days_of_data)
            logger.info(f"After Bayesian prior: {prior_adjusted}")

            # Apply smoothing (combine with current weights)
            with get_db_session() as session:
                current = (
                    session.query(WeightHistory).order_by(WeightHistory.timestamp.desc()).first()
                )

                if current:
                    smoothed_weights = {}
                    for signal in ["technical", "reddit", "news"]:
                        current_val = getattr(current, f"weight_{signal}")
                        new_val = prior_adjusted[signal]

                        # Smoothing: 70% current, 30% new
                        smoothed_weights[signal] = (
                            1 - self.smoothing_factor
                        ) * current_val + self.smoothing_factor * new_val

                    logger.info(f"After smoothing: {smoothed_weights}")
                else:
                    smoothed_weights = prior_adjusted

            # Normalize to ensure sum = 1.0
            final_weights = self._normalize_weights(smoothed_weights)

            logger.info(f"Final weights: {final_weights}")

            # Calculate combined Sharpe
            with get_db_session() as session:
                all_validations = (
                    session.query(ValidationResult)
                    .join(Recommendation)
                    .filter(
                        Recommendation.timestamp >= window_start,
                        ValidationResult.validation_type == "standard_24h",
                        ValidationResult.outcome.in_(["success", "failure"]),
                        ValidationResult.pnl_pct.isnot(None),
                    )
                    .all()
                )

                if all_validations:
                    pnls = [v.pnl_pct for v in all_validations]
                    mean_return = statistics.mean(pnls)
                    std_return = statistics.stdev(pnls) if len(pnls) > 1 else 0.001
                    risk_free_daily = self.validation_service.risk_free_rate / 365
                    sharpe_combined = (mean_return - risk_free_daily) / std_return
                else:
                    sharpe_combined = None

            # Save new weights
            with get_db_session() as session:
                new_weight_record = WeightHistory(
                    timestamp=datetime.utcnow(),
                    weight_technical=final_weights["technical"],
                    weight_reddit=final_weights["reddit"],
                    weight_news=final_weights["news"],
                    trigger_reason="daily_recalc",
                    days_of_data=days_of_data,
                    prior_weight_factor=(0.7 if days_of_data < 30 else 0.0),
                    sharpe_technical=sharpes["technical"],
                    sharpe_reddit=sharpes["reddit"],
                    sharpe_news=sharpes["news"],
                    sharpe_combined=sharpe_combined,
                )

                session.add(new_weight_record)
                session.commit()

                logger.info(f"✓ Weights saved to database (ID: {new_weight_record.id})")

            # Check for mode changes (degraded_preferred logic)
            # TODO: Implement mode change detection

            self.last_run = datetime.utcnow()
            self.optimization_count += 1

            logger.info("=" * 60)
            logger.info("WEIGHT OPTIMIZATION COMPLETE")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Weight optimization failed: {e}", exc_info=True)
            raise

    async def run(self):
        """
        Main optimization loop

        Runs daily at midnight UTC.
        """
        logger.info("Weight optimizer started (runs daily at midnight UTC)")

        while True:
            try:
                # Sleep until next midnight UTC
                await self._sleep_until_midnight_utc()

                # Run optimization
                await self._recalculate_weights()

                # Sleep ~24h (next iteration will recalculate exact time)
                await asyncio.sleep(86400)

            except asyncio.CancelledError:
                logger.info("Weight optimizer cancelled")
                break

            except Exception as e:
                logger.error(f"Error in weight optimizer: {e}", exc_info=True)
                # Sleep 1 hour and retry
                await asyncio.sleep(3600)

    def get_stats(self) -> dict:
        """
        Get optimizer statistics

        Returns:
            Dictionary with optimizer stats
        """
        return {
            "status": "active" if self.last_run else "waiting_for_first_run",
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "optimization_count": self.optimization_count,
            "rolling_window_days": self.rolling_window,
            "cold_start_days": self.cold_start_days,
            "smoothing_factor": self.smoothing_factor,
        }
