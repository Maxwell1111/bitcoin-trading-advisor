"""
History Tracker Service

Persists recommendations and initial price snapshots to database.
Handles data validation and ensures complete audit trail.

Usage:
    history_tracker = HistoryTracker()
    rec_id = history_tracker.save_recommendation(recommendation_data, current_price)
"""

import json
import logging
from datetime import datetime
from typing import Any, Optional

from ..database import get_db_session
from ..database.models import PriceSnapshot, Recommendation, WeightHistory

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when recommendation data fails validation"""

    pass


class HistoryTracker:
    """
    Tracks and persists recommendation history

    Saves recommendations to database with initial price snapshot.
    Performs basic data validation to ensure integrity.
    """

    def __init__(self):
        """Initialize HistoryTracker"""
        pass

    def _ensure_daily_weight_snapshot(self, weights: dict[str, float], session) -> None:
        """
        Ensure a weight snapshot exists for today.

        Creates a daily weight history entry if one doesn't exist for the current date.
        This ensures the Weight Evolution chart always has up-to-date data.

        Args:
            weights: Dict with 'technical_weight', 'reddit_weight', 'news_weight'
            session: Database session to use
        """
        try:
            today = datetime.utcnow().date()

            # Check if a weight entry already exists for today
            existing_entry = (
                session.query(WeightHistory)
                .filter(
                    WeightHistory.timestamp >= datetime.combine(today, datetime.min.time()),
                    WeightHistory.timestamp < datetime.combine(today, datetime.max.time()),
                )
                .first()
            )

            if existing_entry:
                # Entry already exists for today, no need to create another
                logger.debug(f"Weight snapshot already exists for {today}")
                return

            # Get days of data (from first recommendation)
            first_rec = session.query(Recommendation).order_by(Recommendation.timestamp).first()
            days_of_data = 0
            if first_rec:
                days_of_data = (datetime.utcnow() - first_rec.timestamp).days

            # Calculate Bayesian prior factor (decreases over time)
            prior_factor = max(0.0, 0.7 - (days_of_data / 30.0) * 0.7)

            # Create new weight snapshot for today
            weight_snapshot = WeightHistory(
                timestamp=datetime.utcnow(),
                weight_technical=weights.get("technical_weight", 0.6),
                weight_reddit=weights.get("reddit_weight", 0.25),
                weight_news=weights.get("news_weight", 0.15),
                trigger_reason="daily_snapshot",
                days_of_data=days_of_data,
                prior_weight_factor=prior_factor,
            )
            session.add(weight_snapshot)
            logger.info(
                f"Created daily weight snapshot: tech={weight_snapshot.weight_technical:.2%}, "
                f"reddit={weight_snapshot.weight_reddit:.2%}, news={weight_snapshot.weight_news:.2%}"
            )

        except Exception as e:
            logger.warning(f"Failed to create daily weight snapshot: {e}")
            # Don't raise - this is a non-critical operation

    def _validate_recommendation_data(self, rec_data: dict[str, Any], current_price: float):
        """
        Validate recommendation data before saving

        Performs basic integrity checks:
        - Required fields present
        - Weights sum to ~1.0
        - Confidence in valid range
        - Price is positive

        Args:
            rec_data: Recommendation dictionary
            current_price: Current Bitcoin price

        Raises:
            ValidationError: If data is invalid
        """
        # Check required fields
        required_fields = ["recommendation", "confidence", "signals"]
        for field in required_fields:
            if field not in rec_data:
                raise ValidationError(f"Missing required field: {field}")

        # Validate confidence
        confidence = rec_data["confidence"]
        if not (0 <= confidence <= 1):
            raise ValidationError(f"Confidence must be in [0, 1], got {confidence}")

        # Validate price
        if current_price <= 0:
            raise ValidationError(f"Price must be positive, got {current_price}")

        # Validate signals structure
        if "technical" not in rec_data["signals"] or "sentiment" not in rec_data["signals"]:
            raise ValidationError("Missing 'technical' or 'sentiment' in signals")

        # Note: We don't validate weights sum here because weights come from
        # request params (which might have 3 weights: reddit, news, technical)
        # and we trust the RecommendationEngine to normalize them

    def save_recommendation(
        self,
        rec_data: dict[str, Any],
        current_price: float,
        weights: dict[str, float],
        operating_mode: str = "normal",
        request_params: Optional[dict] = None,
    ) -> int:
        """
        Save recommendation to database with initial price snapshot

        Args:
            rec_data: Recommendation dictionary from RecommendationEngine
            current_price: Current Bitcoin price
            weights: Dict with 'technical_weight', 'reddit_weight', 'news_weight'
            operating_mode: 'normal', 'degraded', or 'degraded_preferred'
            request_params: Original request parameters (days, news_days, etc.)

        Returns:
            Database ID of created recommendation

        Raises:
            ValidationError: If data validation fails
        """
        try:
            # Validate data
            self._validate_recommendation_data(rec_data, current_price)

            # Extract signal details
            signals = rec_data["signals"]
            technical = signals.get("technical", {})
            sentiment = signals.get("sentiment", {})

            # Determine which signals were actually used
            signal_sources = []
            if technical.get("weight", 0) > 0:
                signal_sources.append("technical")
            if sentiment.get("weight", 0) > 0:
                # Sentiment is combination of reddit + news
                signal_sources.extend(["reddit", "news"])

            # Create recommendation record
            recommendation = Recommendation(
                timestamp=datetime.utcnow(),
                recommendation=rec_data["recommendation"],
                confidence=rec_data["confidence"],
                current_price=current_price,
                # Weights
                weight_technical=weights.get("technical_weight", 0.6),
                weight_reddit=weights.get("reddit_weight", 0.25),
                weight_news=weights.get("news_weight", 0.15),
                # Signal scores
                technical_score=technical.get("score", 0.0),
                reddit_score=sentiment.get("score", 0.0)
                * weights.get("reddit_weight", 0.25)
                / (
                    weights.get("reddit_weight", 0.25) + weights.get("news_weight", 0.15)
                ),  # Proportional split
                news_score=sentiment.get("score", 0.0)
                * weights.get("news_weight", 0.15)
                / (weights.get("reddit_weight", 0.25) + weights.get("news_weight", 0.15)),
                # Individual recommendations
                technical_recommendation=technical.get("recommendation"),
                reddit_recommendation=sentiment.get("recommendation"),  # Using combined sentiment
                news_recommendation=sentiment.get("recommendation"),
                # Targets
                entry_price=rec_data.get("targets", {}).get("entry", current_price),
                target_1=rec_data.get("targets", {}).get("target_1"),
                target_2=rec_data.get("targets", {}).get("target_2"),
                stop_loss=rec_data.get("targets", {}).get("stop_loss"),
                # Metadata
                operating_mode=operating_mode,
                signal_sources=json.dumps(signal_sources),
                request_params=json.dumps(request_params) if request_params else None,
                # Full details
                full_signals=rec_data["signals"],
                reasoning=rec_data.get("reasoning", ""),
            )

            # Save to database
            with get_db_session() as session:
                session.add(recommendation)
                session.flush()  # Get the ID

                # Create initial price snapshot
                initial_snapshot = PriceSnapshot(
                    recommendation_id=recommendation.id,
                    snapshot_type="initial",
                    timestamp=datetime.utcnow(),
                    price=current_price,
                    time_offset_hours=0.0,
                )
                session.add(initial_snapshot)

                # Ensure daily weight snapshot exists
                self._ensure_daily_weight_snapshot(weights, session)

                session.commit()

                rec_id = recommendation.id
                logger.info(
                    f"Saved recommendation #{rec_id}: {rec_data['recommendation']} "
                    f"(confidence={rec_data['confidence']:.2f}, price=${current_price:,.2f})"
                )

                return rec_id

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to save recommendation: {e}", exc_info=True)
            raise

    def get_recommendation(self, rec_id: int) -> Optional[dict]:
        """
        Retrieve a recommendation by ID

        Args:
            rec_id: Recommendation database ID

        Returns:
            Recommendation data as dictionary, or None if not found
        """
        try:
            with get_db_session() as session:
                rec = session.query(Recommendation).filter(Recommendation.id == rec_id).first()

                if not rec:
                    return None

                return {
                    "id": rec.id,
                    "timestamp": rec.timestamp.isoformat(),
                    "recommendation": rec.recommendation,
                    "confidence": rec.confidence,
                    "current_price": rec.current_price,
                    "weights": {
                        "technical": rec.weight_technical,
                        "reddit": rec.weight_reddit,
                        "news": rec.weight_news,
                    },
                    "targets": {
                        "entry": rec.entry_price,
                        "target_1": rec.target_1,
                        "target_2": rec.target_2,
                        "stop_loss": rec.stop_loss,
                    },
                    "operating_mode": rec.operating_mode,
                    "reasoning": rec.reasoning,
                    "full_signals": rec.full_signals,
                }

        except Exception as e:
            logger.error(f"Failed to retrieve recommendation {rec_id}: {e}")
            return None

    def get_recent_recommendations(self, limit: int = 10) -> list:
        """
        Get most recent recommendations

        Args:
            limit: Maximum number of recommendations to return

        Returns:
            List of recommendation dictionaries
        """
        try:
            with get_db_session() as session:
                recs = (
                    session.query(Recommendation)
                    .order_by(Recommendation.timestamp.desc())
                    .limit(limit)
                    .all()
                )

                return [
                    {
                        "id": r.id,
                        "timestamp": r.timestamp.isoformat(),
                        "recommendation": r.recommendation,
                        "confidence": r.confidence,
                        "price": r.current_price,
                        "mode": r.operating_mode,
                    }
                    for r in recs
                ]

        except Exception as e:
            logger.error(f"Failed to get recent recommendations: {e}")
            return []

    def get_stats(self) -> dict:
        """
        Get history statistics for monitoring

        Returns:
            Dictionary with statistics about stored recommendations
        """
        try:
            with get_db_session() as session:
                total = session.query(Recommendation).count()

                # Count by recommendation type
                buy_count = (
                    session.query(Recommendation)
                    .filter(Recommendation.recommendation.like("%buy%"))
                    .count()
                )
                sell_count = (
                    session.query(Recommendation)
                    .filter(Recommendation.recommendation.like("%sell%"))
                    .count()
                )
                hold_count = (
                    session.query(Recommendation)
                    .filter(Recommendation.recommendation == "hold")
                    .count()
                )

                # Latest recommendation
                latest = (
                    session.query(Recommendation).order_by(Recommendation.timestamp.desc()).first()
                )

                return {
                    "total_recommendations": total,
                    "by_type": {"buy": buy_count, "sell": sell_count, "hold": hold_count},
                    "latest_recommendation": (
                        {
                            "id": latest.id,
                            "type": latest.recommendation,
                            "timestamp": latest.timestamp.isoformat(),
                        }
                        if latest
                        else None
                    ),
                }

        except Exception as e:
            logger.error(f"Failed to get history stats: {e}")
            return {"error": str(e)}
