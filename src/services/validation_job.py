"""
Validation Job Service

Runs validation checks on pending recommendations at multiple time horizons.
Executes every 5 minutes to check 4h, 24h, 7d, and event-based validations.

Usage:
    job = ValidationJob(validation_service, price_fetcher_func)
    asyncio.create_task(job.run())
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Callable, Optional, Dict

from ..database import get_db_session
from ..database.models import Recommendation, PriceSnapshot, ValidationResult
from .validation_service import ValidationService

logger = logging.getLogger(__name__)


class ValidationJob:
    """
    Background job for validating recommendations

    Periodically checks pending recommendations at various time horizons
    and calculates accuracy metrics using the ValidationService.
    """

    def __init__(
        self,
        validation_service: ValidationService,
        price_fetcher: Callable[[], float],
        interval_seconds: int = 300,  # 5 minutes
        batch_size: int = 100
    ):
        """
        Initialize ValidationJob

        Args:
            validation_service: ValidationService instance
            price_fetcher: Async function that returns current BTC price
            interval_seconds: How often to run validation (default: 300s = 5min)
            batch_size: Max recommendations to process per run (default: 100)
        """
        self.validation_service = validation_service
        self.price_fetcher = price_fetcher
        self.interval = interval_seconds
        self.batch_size = batch_size

        self.last_run: Optional[datetime] = None
        self.total_validations_created = 0
        self.errors_count = 0

    async def _get_current_price(self) -> Optional[float]:
        """Fetch current Bitcoin price"""
        try:
            price = await self.price_fetcher()
            return price
        except Exception as e:
            logger.error(f"Failed to fetch price for validation: {e}")
            return None

    async def _validate_recommendation(
        self,
        rec: Recommendation,
        current_price: float
    ):
        """
        Run all applicable validations for a recommendation

        Args:
            rec: Recommendation database record
            current_price: Current Bitcoin price
        """
        now = datetime.utcnow()
        age = now - rec.timestamp
        age_hours = age.total_seconds() / 3600

        # Get recent accuracy for dynamic position sizing
        recent_accuracy = self.validation_service.get_recent_accuracy()

        # Calculate position size
        position_size = self.validation_service.calculate_position_size(
            rec,
            current_accuracy=recent_accuracy
        )

        # Check which validations to run based on age
        validations_to_run = []

        # Quick 4h validation
        if age_hours >= 4:
            validations_to_run.append(('quick_4h', 4))

        # Standard 24h validation
        if age_hours >= 24:
            validations_to_run.append(('standard_24h', 24))

        # Extended 7d validation
        if age_hours >= 168:  # 7 days
            validations_to_run.append(('extended_7d', 168))

        # Run each validation
        for validation_type, expected_hours in validations_to_run:
            try:
                # Check if already validated
                with get_db_session() as session:
                    existing = session.query(ValidationResult).filter(
                        ValidationResult.recommendation_id == rec.id,
                        ValidationResult.validation_type == validation_type
                    ).first()

                    if existing and existing.outcome != 'pending':
                        # Already validated, skip
                        continue

                # Get price snapshot at the appropriate time
                target_time = rec.timestamp + timedelta(hours=expected_hours)

                with get_db_session() as session:
                    snapshot = session.query(PriceSnapshot).filter(
                        PriceSnapshot.recommendation_id == rec.id,
                        PriceSnapshot.time_offset_hours >= expected_hours - 0.5,
                        PriceSnapshot.time_offset_hours <= expected_hours + 0.5
                    ).first()

                    if snapshot:
                        price_at_time = snapshot.price
                    else:
                        # Create snapshot with current price
                        # (approximation if we don't have historical snapshot)
                        snapshot = PriceSnapshot(
                            recommendation_id=rec.id,
                            snapshot_type=validation_type,
                            timestamp=now,
                            price=current_price,
                            time_offset_hours=age_hours
                        )
                        session.add(snapshot)
                        session.commit()
                        price_at_time = current_price

                # Run validation based on type
                if validation_type == 'quick_4h':
                    outcome, reason, price_change = self.validation_service.validate_quick_4h(
                        rec, price_at_time
                    )
                elif validation_type == 'standard_24h':
                    outcome, reason, price_change = self.validation_service.validate_standard_24h(
                        rec, price_at_time
                    )
                else:  # extended_7d
                    # Use standard validation logic (could be customized)
                    outcome, reason, price_change = self.validation_service.validate_standard_24h(
                        rec, price_at_time
                    )

                # Calculate P&L
                pnl = self.validation_service.calculate_pnl_with_position_sizing(
                    rec, price_at_time, position_size
                )

                # Calculate Kelly fraction
                if rec.target_1 and rec.stop_loss:
                    if 'buy' in rec.recommendation.lower():
                        win_payout = (rec.target_1 - rec.entry_price) / rec.entry_price
                        loss_payout = (rec.entry_price - rec.stop_loss) / rec.entry_price
                    else:
                        win_payout = (rec.entry_price - rec.target_1) / rec.entry_price
                        loss_payout = (rec.stop_loss - rec.entry_price) / rec.entry_price

                    kelly_fraction = self.validation_service.calculate_kelly_fraction(
                        rec.confidence, win_payout, loss_payout
                    )
                else:
                    kelly_fraction = 0.0

                # Save validation result
                self.validation_service.save_validation_result(
                    recommendation=rec,
                    validation_type=validation_type,
                    outcome=outcome,
                    outcome_reason=reason,
                    price_change_pct=price_change,
                    position_size=position_size,
                    pnl_pct=pnl,
                    kelly_fraction=kelly_fraction
                )

                self.total_validations_created += 1

            except Exception as e:
                logger.error(f"Failed to validate rec #{rec.id} at {validation_type}: {e}")
                self.errors_count += 1

        # Event-based validation (check if target/stop hit)
        try:
            result = self.validation_service.validate_event_based(rec, current_price)

            if result:
                outcome, reason, pnl_pct = result

                # Calculate position size for event-based
                position_size = self.validation_service.calculate_position_size(rec, recent_accuracy)

                # Calculate full P&L
                pnl = self.validation_service.calculate_pnl_with_position_sizing(
                    rec, current_price, position_size
                )

                # Save event-based validation
                self.validation_service.save_validation_result(
                    recommendation=rec,
                    validation_type='event_based',
                    outcome=outcome,
                    outcome_reason=reason,
                    price_change_pct=pnl_pct,
                    position_size=position_size,
                    pnl_pct=pnl,
                    kelly_fraction=0.0  # Not applicable for event-based
                )

                logger.info(f"Event-based validation for rec #{rec.id}: {outcome} ({reason})")
                self.total_validations_created += 1

        except Exception as e:
            logger.error(f"Event-based validation failed for rec #{rec.id}: {e}")
            self.errors_count += 1

    async def _run_validation_cycle(self):
        """Run one validation cycle"""
        logger.debug("Starting validation cycle...")

        # Get current price
        current_price = await self._get_current_price()

        if not current_price:
            logger.warning("Could not fetch price, skipping validation cycle")
            return

        # Find recommendations needing validation
        # Process most recent first, limited by batch size
        with get_db_session() as session:
            # Get recent recommendations (last 30 days)
            cutoff = datetime.utcnow() - timedelta(days=30)

            pending_recs = session.query(Recommendation).filter(
                Recommendation.timestamp >= cutoff
            ).order_by(
                Recommendation.timestamp.desc()
            ).limit(self.batch_size).all()

            logger.info(f"Found {len(pending_recs)} recommendations to check")

        # Validate each recommendation
        for rec in pending_recs:
            await self._validate_recommendation(rec, current_price)

        self.last_run = datetime.utcnow()
        logger.info(f"Validation cycle complete (checked {len(pending_recs)} recommendations)")

    async def run(self):
        """
        Main validation loop

        Runs validation cycle every `interval` seconds.
        """
        logger.info(f"Validation job started (interval: {self.interval}s, batch size: {self.batch_size})")

        while True:
            try:
                await self._run_validation_cycle()
                await asyncio.sleep(self.interval)

            except asyncio.CancelledError:
                logger.info("Validation job cancelled")
                break

            except Exception as e:
                logger.error(f"Error in validation job: {e}", exc_info=True)
                self.errors_count += 1
                # Continue after error
                await asyncio.sleep(self.interval)

    def get_stats(self) -> Dict:
        """
        Get validation job statistics

        Returns:
            Dictionary with job stats
        """
        return {
            'status': 'running' if self.last_run else 'not_started',
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'total_validations_created': self.total_validations_created,
            'errors_count': self.errors_count,
            'batch_size': self.batch_size,
            'interval_seconds': self.interval
        }
