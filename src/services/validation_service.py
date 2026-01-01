"""
Validation Service

Validates recommendations at multiple time horizons using Kelly Criterion
for position sizing and P&L calculation.

Handles:
- Multi-horizon validation (4h, 24h, 7d, event-based)
- Kelly Criterion position sizing with constraints
- Sharpe ratio calculation for adaptive weighting
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
import statistics

from ..database import get_db_session
from ..database.models import Recommendation, PriceSnapshot, ValidationResult

logger = logging.getLogger(__name__)


class ValidationService:
    """
    Multi-horizon recommendation validation

    Validates recommendations at different time horizons and calculates
    risk-adjusted returns using Kelly Criterion position sizing.
    """

    def __init__(
        self,
        max_position_pct: float = 0.25,
        min_confidence: float = 0.60,
        risk_free_rate: float = 0.045
    ):
        """
        Initialize ValidationService

        Args:
            max_position_pct: Maximum position size (default: 25%)
            min_confidence: Minimum confidence to trade (default: 60%)
            risk_free_rate: Annual risk-free rate for Sharpe (default: 4.5%)
        """
        self.max_position = max_position_pct
        self.min_confidence = min_confidence
        self.risk_free_rate = risk_free_rate

    def calculate_kelly_fraction(
        self,
        confidence: float,
        win_payout_pct: float,
        loss_payout_pct: float
    ) -> float:
        """
        Calculate Kelly Criterion position size

        Formula: kelly = (win_prob * win_payout - loss_prob * loss_payout) / win_payout

        Args:
            confidence: Win probability (0-1)
            win_payout_pct: Expected gain if win (e.g., 0.05 for 5%)
            loss_payout_pct: Expected loss if loss (e.g., 0.03 for 3%)

        Returns:
            Kelly fraction (position size as % of portfolio)
        """
        if win_payout_pct <= 0:
            logger.warning(f"Invalid win payout: {win_payout_pct}")
            return 0.0

        win_prob = confidence
        loss_prob = 1 - confidence

        # Kelly formula
        kelly = (win_prob * win_payout_pct - loss_prob * loss_payout_pct) / win_payout_pct

        # Kelly can be negative (bad bet) - don't trade
        if kelly < 0:
            return 0.0

        return kelly

    def calculate_position_size(
        self,
        recommendation: Recommendation,
        current_accuracy: Optional[float] = None
    ) -> float:
        """
        Calculate position size with all constraints applied

        Args:
            recommendation: Recommendation database record
            current_accuracy: Recent accuracy rate (for dynamic cap)

        Returns:
            Position size as decimal (0.25 = 25%)
        """
        # Check minimum confidence threshold
        if recommendation.confidence < self.min_confidence:
            logger.debug(f"Confidence {recommendation.confidence:.2f} below minimum {self.min_confidence}")
            return 0.0

        # Calculate Kelly fraction
        if recommendation.recommendation.lower() in ['buy', 'strong_buy']:
            # For buy: win = reach target, loss = hit stop
            win_payout = (recommendation.target_1 - recommendation.entry_price) / recommendation.entry_price if recommendation.target_1 else 0.05
            loss_payout = (recommendation.entry_price - recommendation.stop_loss) / recommendation.entry_price if recommendation.stop_loss else 0.03

        elif recommendation.recommendation.lower() in ['sell', 'strong_sell']:
            # For sell: win = price drops to target, loss = hits stop
            win_payout = (recommendation.entry_price - recommendation.target_1) / recommendation.entry_price if recommendation.target_1 else 0.05
            loss_payout = (recommendation.stop_loss - recommendation.entry_price) / recommendation.entry_price if recommendation.stop_loss else 0.03

        else:  # hold
            # Don't size positions for hold
            return 0.0

        kelly_fraction = self.calculate_kelly_fraction(
            recommendation.confidence,
            win_payout,
            loss_payout
        )

        # Apply maximum position cap
        position = min(kelly_fraction, self.max_position)

        # Apply dynamic cap based on recent accuracy
        if current_accuracy is not None and current_accuracy < 0.55:
            # Reduce position if recent accuracy is poor
            reduction_factor = current_accuracy / 0.55  # Scales from 0 to 1
            position *= reduction_factor
            logger.debug(f"Applied dynamic cap: accuracy={current_accuracy:.2f}, factor={reduction_factor:.2f}")

        return position

    def validate_quick_4h(
        self,
        recommendation: Recommendation,
        price_4h: float
    ) -> Tuple[str, str, float]:
        """
        Validate 4-hour quick check

        Args:
            recommendation: Recommendation record
            price_4h: Price at 4 hours after recommendation

        Returns:
            Tuple of (outcome, reason, pnl_pct)
        """
        entry = recommendation.entry_price
        pct_change = (price_4h - entry) / entry

        rec_type = recommendation.recommendation.lower()

        if 'buy' in rec_type:
            # Success if price moved up >0.5%
            if pct_change >= 0.005:
                return 'success', 'directional_up', pct_change
            else:
                return 'failure', 'insufficient_movement', pct_change

        elif 'sell' in rec_type:
            # Success if price moved down >0.5%
            if pct_change <= -0.005:
                return 'success', 'directional_down', abs(pct_change)
            else:
                return 'failure', 'insufficient_movement', pct_change

        else:  # hold
            # Success if price stayed within ±5%
            if abs(pct_change) <= 0.05:
                return 'success', 'stayed_in_band', 0.0
            else:
                return 'failure', 'broke_out_of_band', abs(pct_change)

    def validate_standard_24h(
        self,
        recommendation: Recommendation,
        price_24h: float
    ) -> Tuple[str, str, float]:
        """
        Validate 24-hour standard check

        Args:
            recommendation: Recommendation record
            price_24h: Price at 24 hours

        Returns:
            Tuple of (outcome, reason, pnl_pct)
        """
        entry = recommendation.entry_price
        pct_change = (price_24h - entry) / entry

        rec_type = recommendation.recommendation.lower()

        if 'buy' in rec_type:
            # Success if price moved up >1% OR hit target
            if pct_change >= 0.01:
                return 'success', 'directional', pct_change
            elif recommendation.target_1 and price_24h >= recommendation.target_1:
                return 'success', 'target_reached', pct_change
            else:
                return 'failure', 'insufficient_gain', pct_change

        elif 'sell' in rec_type:
            # Success if price moved down >1% OR hit target
            if pct_change <= -0.01:
                return 'success', 'directional', abs(pct_change)
            elif recommendation.target_1 and price_24h <= recommendation.target_1:
                return 'success', 'target_reached', abs(pct_change)
            else:
                return 'failure', 'insufficient_drop', pct_change

        else:  # hold
            # Success if stayed within ±5%
            if abs(pct_change) <= 0.05:
                return 'success', 'stayed_in_band', 0.0
            else:
                return 'failure', 'broke_out', abs(pct_change)

    def validate_event_based(
        self,
        recommendation: Recommendation,
        current_price: float
    ) -> Optional[Tuple[str, str, float]]:
        """
        Check if target or stop-loss has been hit

        Args:
            recommendation: Recommendation record
            current_price: Current Bitcoin price

        Returns:
            Tuple of (outcome, reason, pnl_pct) if triggered, None otherwise
        """
        entry = recommendation.entry_price
        rec_type = recommendation.recommendation.lower()

        if 'buy' in rec_type:
            if recommendation.target_1 and current_price >= recommendation.target_1:
                pnl = (recommendation.target_1 - entry) / entry
                return 'success', 'target_reached', pnl
            elif recommendation.stop_loss and current_price <= recommendation.stop_loss:
                pnl = (recommendation.stop_loss - entry) / entry
                return 'failure', 'stop_loss_hit', pnl

        elif 'sell' in rec_type:
            if recommendation.target_1 and current_price <= recommendation.target_1:
                pnl = (entry - recommendation.target_1) / entry
                return 'success', 'target_reached', pnl
            elif recommendation.stop_loss and current_price >= recommendation.stop_loss:
                pnl = (entry - recommendation.stop_loss) / entry
                return 'failure', 'stop_loss_hit', pnl

        return None  # No event triggered

    def calculate_pnl_with_position_sizing(
        self,
        recommendation: Recommendation,
        exit_price: float,
        position_size: float
    ) -> float:
        """
        Calculate P&L considering position sizing

        Args:
            recommendation: Recommendation record
            exit_price: Exit price
            position_size: Position size as decimal (0.25 = 25%)

        Returns:
            P&L as percentage of total portfolio
        """
        entry = recommendation.entry_price
        price_change_pct = (exit_price - entry) / entry

        rec_type = recommendation.recommendation.lower()

        if 'buy' in rec_type:
            # Long position: profit when price goes up
            pnl = position_size * price_change_pct
        elif 'sell' in rec_type:
            # Short position: profit when price goes down
            pnl = position_size * (-price_change_pct)
        else:  # hold
            pnl = 0.0

        return pnl

    def save_validation_result(
        self,
        recommendation: Recommendation,
        validation_type: str,
        outcome: str,
        outcome_reason: str,
        price_change_pct: float,
        position_size: float,
        pnl_pct: float,
        kelly_fraction: float
    ) -> int:
        """
        Save validation result to database

        Args:
            recommendation: Recommendation record
            validation_type: 'quick_4h', 'standard_24h', 'extended_7d', 'event_based'
            outcome: 'success', 'failure', 'expired', 'pending'
            outcome_reason: Detailed reason
            price_change_pct: Actual price change
            position_size: Position size used
            pnl_pct: Calculated P&L
            kelly_fraction: Kelly fraction calculated

        Returns:
            ValidationResult ID
        """
        try:
            with get_db_session() as session:
                # Check if validation already exists
                existing = session.query(ValidationResult).filter(
                    ValidationResult.recommendation_id == recommendation.id,
                    ValidationResult.validation_type == validation_type
                ).first()

                if existing:
                    # Update existing
                    existing.validated_at = datetime.utcnow()
                    existing.outcome = outcome
                    existing.outcome_reason = outcome_reason
                    existing.price_change_pct = price_change_pct
                    existing.position_size_pct = position_size
                    existing.pnl_pct = pnl_pct
                    existing.kelly_fraction = kelly_fraction
                    existing.target_reached = (outcome == 'success' and 'target' in outcome_reason)

                    session.commit()
                    logger.debug(f"Updated validation for rec #{recommendation.id}, type={validation_type}")
                    return existing.id

                else:
                    # Create new validation
                    validation = ValidationResult(
                        recommendation_id=recommendation.id,
                        validation_type=validation_type,
                        validated_at=datetime.utcnow(),
                        outcome=outcome,
                        outcome_reason=outcome_reason,
                        price_change_pct=price_change_pct,
                        position_size_pct=position_size,
                        pnl_pct=pnl_pct,
                        kelly_fraction=kelly_fraction,
                        target_reached=(outcome == 'success' and 'target' in outcome_reason),
                        time_to_outcome_hours=None  # Set by caller if known
                    )

                    session.add(validation)
                    session.commit()

                    logger.info(f"Created validation for rec #{recommendation.id}: {validation_type} = {outcome}")
                    return validation.id

        except Exception as e:
            logger.error(f"Failed to save validation result: {e}", exc_info=True)
            raise

    def calculate_sharpe_ratio(
        self,
        signal_type: str,
        lookback_days: int = 30
    ) -> Optional[float]:
        """
        Calculate Sharpe ratio for a signal type

        Args:
            signal_type: 'technical', 'reddit', 'news', or 'combined'
            lookback_days: Number of days to look back

        Returns:
            Sharpe ratio, or None if insufficient data
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)

            with get_db_session() as session:
                # Get validated recommendations
                query = session.query(ValidationResult).join(
                    Recommendation
                ).filter(
                    Recommendation.timestamp >= cutoff_date,
                    ValidationResult.validation_type == 'standard_24h',
                    ValidationResult.outcome.in_(['success', 'failure']),
                    ValidationResult.pnl_pct.isnot(None)
                )

                # Filter by signal type if needed
                if signal_type != 'combined':
                    # This would require tracking which signal was dominant
                    # For now, use all recommendations
                    pass

                validations = query.all()

                if len(validations) < 10:
                    logger.warning(f"Insufficient data for Sharpe calculation: {len(validations)} validations")
                    return None

                # Extract P&L percentages
                pnls = [v.pnl_pct for v in validations if v.pnl_pct is not None]

                if len(pnls) < 10:
                    return None

                # Calculate Sharpe ratio
                mean_return = statistics.mean(pnls)
                std_return = statistics.stdev(pnls) if len(pnls) > 1 else 0.001

                if std_return == 0:
                    std_return = 0.001  # Avoid division by zero

                # Risk-free rate per day (assuming 24h holding period)
                risk_free_daily = self.risk_free_rate / 365

                sharpe = (mean_return - risk_free_daily) / std_return

                logger.info(
                    f"Sharpe ratio for {signal_type}: {sharpe:.3f} "
                    f"(mean={mean_return:.4f}, std={std_return:.4f}, n={len(pnls)})"
                )

                return sharpe

        except Exception as e:
            logger.error(f"Failed to calculate Sharpe ratio: {e}", exc_info=True)
            return None

    def get_recent_accuracy(self, horizon: str = 'standard_24h', days: int = 7) -> float:
        """
        Get recent accuracy rate for dynamic position sizing

        Args:
            horizon: Validation type to check
            days: Lookback period

        Returns:
            Accuracy rate (0.0 to 1.0)
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            with get_db_session() as session:
                total = session.query(ValidationResult).join(
                    Recommendation
                ).filter(
                    Recommendation.timestamp >= cutoff_date,
                    ValidationResult.validation_type == horizon,
                    ValidationResult.outcome.in_(['success', 'failure'])
                ).count()

                if total == 0:
                    return 0.65  # Default to reasonable accuracy

                successes = session.query(ValidationResult).join(
                    Recommendation
                ).filter(
                    Recommendation.timestamp >= cutoff_date,
                    ValidationResult.validation_type == horizon,
                    ValidationResult.outcome == 'success'
                ).count()

                accuracy = successes / total
                return accuracy

        except Exception as e:
            logger.error(f"Failed to get recent accuracy: {e}")
            return 0.65  # Default

    def get_validation_stats(self) -> Dict:
        """
        Get validation statistics for monitoring

        Returns:
            Dictionary with validation metrics
        """
        try:
            with get_db_session() as session:
                total = session.query(ValidationResult).count()

                # By outcome
                successes = session.query(ValidationResult).filter(
                    ValidationResult.outcome == 'success'
                ).count()

                # By type
                quick_count = session.query(ValidationResult).filter(
                    ValidationResult.validation_type == 'quick_4h'
                ).count()
                standard_count = session.query(ValidationResult).filter(
                    ValidationResult.validation_type == 'standard_24h'
                ).count()

                accuracy = successes / total if total > 0 else 0.0

                return {
                    'total_validations': total,
                    'successes': successes,
                    'overall_accuracy': round(accuracy, 3),
                    'by_type': {
                        'quick_4h': quick_count,
                        'standard_24h': standard_count
                    }
                }

        except Exception as e:
            logger.error(f"Failed to get validation stats: {e}")
            return {'error': str(e)}
