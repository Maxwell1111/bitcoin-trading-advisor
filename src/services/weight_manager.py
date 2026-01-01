"""
Weight Manager Service

Manages adaptive signal weights (technical, reddit, news).
Loads weights from database and refreshes periodically.

Usage:
    # In app startup:
    weight_manager = get_weight_manager()
    weight_manager.start_refresh_task()

    # In recommendation engine:
    weights = weight_manager.get_current_weights()
    engine = RecommendationEngine(**weights)
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass

from ..database import get_db_session
from ..database.models import WeightHistory

logger = logging.getLogger(__name__)


@dataclass
class WeightConfig:
    """Current weight configuration"""
    technical: float
    reddit: float
    news: float
    last_updated: datetime
    trigger_reason: str
    sharpe_technical: Optional[float] = None
    sharpe_reddit: Optional[float] = None
    sharpe_news: Optional[float] = None


class WeightManager:
    """
    Manages adaptive signal weights

    Singleton service that loads weights from database and keeps
    them cached in memory. Refreshes periodically to pick up changes
    from the WeightOptimizer background service.
    """

    def __init__(self, refresh_interval_seconds: int = 300):
        """
        Initialize WeightManager

        Args:
            refresh_interval_seconds: How often to reload weights from DB (default: 300 = 5 minutes)
        """
        self.refresh_interval = refresh_interval_seconds
        self._current_weights: Optional[WeightConfig] = None
        self._refresh_task: Optional[asyncio.Task] = None
        self._fallback_weights = WeightConfig(
            technical=0.60,
            reddit=0.25,
            news=0.15,
            last_updated=datetime.utcnow(),
            trigger_reason='fallback_defaults'
        )

        # Load initial weights
        self._load_weights_from_db()

    def _load_weights_from_db(self) -> bool:
        """
        Load latest weights from database

        Returns:
            True if successful, False if using fallback
        """
        try:
            with get_db_session() as session:
                latest_weight = session.query(WeightHistory).order_by(
                    WeightHistory.timestamp.desc()
                ).first()

                if latest_weight:
                    self._current_weights = WeightConfig(
                        technical=latest_weight.weight_technical,
                        reddit=latest_weight.weight_reddit,
                        news=latest_weight.weight_news,
                        last_updated=latest_weight.timestamp,
                        trigger_reason=latest_weight.trigger_reason or 'unknown',
                        sharpe_technical=latest_weight.sharpe_technical,
                        sharpe_reddit=latest_weight.sharpe_reddit,
                        sharpe_news=latest_weight.sharpe_news
                    )
                    logger.info(
                        f"Loaded weights from DB: tech={self._current_weights.technical:.2%}, "
                        f"reddit={self._current_weights.reddit:.2%}, "
                        f"news={self._current_weights.news:.2%} "
                        f"(updated: {self._current_weights.last_updated})"
                    )
                    return True
                else:
                    logger.warning("No weights found in database, using fallback")
                    self._current_weights = self._fallback_weights
                    return False

        except Exception as e:
            logger.error(f"Failed to load weights from DB: {e}", exc_info=True)
            if self._current_weights is None:
                logger.warning("Using fallback weights due to DB error")
                self._current_weights = self._fallback_weights
            return False

    def get_current_weights(self) -> Dict[str, float]:
        """
        Get current signal weights

        Returns:
            Dictionary with keys: 'technical_weight', 'reddit_weight', 'news_weight'
        """
        if self._current_weights is None:
            logger.warning("Weights not initialized, loading now...")
            self._load_weights_from_db()

        return {
            'technical_weight': self._current_weights.technical,
            'reddit_weight': self._current_weights.reddit,
            'news_weight': self._current_weights.news
        }

    def get_weight_config(self) -> WeightConfig:
        """
        Get full weight configuration including metadata

        Returns:
            WeightConfig object with all weight details
        """
        if self._current_weights is None:
            self._load_weights_from_db()

        return self._current_weights

    def force_refresh(self) -> bool:
        """
        Force immediate reload of weights from database

        Useful for manual triggering or testing.

        Returns:
            True if successful, False otherwise
        """
        logger.info("Force refreshing weights from database")
        return self._load_weights_from_db()

    async def _periodic_refresh(self):
        """Background task that periodically refreshes weights"""
        logger.info(f"Starting periodic weight refresh (interval: {self.refresh_interval}s)")

        while True:
            try:
                await asyncio.sleep(self.refresh_interval)
                self._load_weights_from_db()

            except asyncio.CancelledError:
                logger.info("Periodic weight refresh cancelled")
                break
            except Exception as e:
                logger.error(f"Error in periodic weight refresh: {e}", exc_info=True)
                # Continue despite errors

    def start_refresh_task(self):
        """
        Start the background refresh task

        Call this in your FastAPI startup event.
        """
        if self._refresh_task is None or self._refresh_task.done():
            self._refresh_task = asyncio.create_task(self._periodic_refresh())
            logger.info("Weight refresh task started")
        else:
            logger.warning("Weight refresh task already running")

    def stop_refresh_task(self):
        """
        Stop the background refresh task

        Call this in your FastAPI shutdown event.
        """
        if self._refresh_task and not self._refresh_task.done():
            self._refresh_task.cancel()
            logger.info("Weight refresh task stopped")

    def get_stats(self) -> Dict:
        """
        Get weight statistics for monitoring/observability

        Returns:
            Dictionary with current weights and metadata
        """
        config = self.get_weight_config()

        return {
            'current_weights': {
                'technical': round(config.technical, 4),
                'reddit': round(config.reddit, 4),
                'news': round(config.news, 4)
            },
            'last_updated': config.last_updated.isoformat(),
            'trigger_reason': config.trigger_reason,
            'sharpe_ratios': {
                'technical': round(config.sharpe_technical, 3) if config.sharpe_technical else None,
                'reddit': round(config.sharpe_reddit, 3) if config.sharpe_reddit else None,
                'news': round(config.sharpe_news, 3) if config.sharpe_news else None
            }
        }


# Global singleton instance
_weight_manager: Optional[WeightManager] = None


def get_weight_manager(refresh_interval_seconds: int = 300) -> WeightManager:
    """
    Get the global WeightManager singleton

    Args:
        refresh_interval_seconds: Refresh interval (only used on first call)

    Returns:
        WeightManager instance
    """
    global _weight_manager

    if _weight_manager is None:
        _weight_manager = WeightManager(refresh_interval_seconds)
        logger.info("WeightManager singleton created")

    return _weight_manager
