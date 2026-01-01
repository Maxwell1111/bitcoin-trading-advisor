"""
Price Monitor Service

Monitors Bitcoin price for volatility spikes and invalidates cache when needed.
Runs every 30 seconds in the background.

Usage:
    monitor = PriceMonitor(volatility_threshold=0.03)
    asyncio.create_task(monitor.run())
"""

import asyncio
import logging
from datetime import datetime
from collections import deque
from typing import Optional, Dict, Callable
import requests

from ..utils.cache import get_cache

logger = logging.getLogger(__name__)


class PriceMonitor:
    """
    Monitors Bitcoin price for volatility spikes

    Polls price every 30 seconds, maintains 5-minute price history,
    and triggers cache invalidation when volatility threshold is exceeded.
    """

    def __init__(
        self,
        volatility_threshold: float = 0.03,
        poll_interval: int = 30,
        webhook_callback: Optional[Callable] = None
    ):
        """
        Initialize PriceMonitor

        Args:
            volatility_threshold: Price change % to trigger invalidation (default: 3%)
            poll_interval: Seconds between price checks (default: 30)
            webhook_callback: Optional function to call on volatility events
        """
        self.volatility_threshold = volatility_threshold
        self.poll_interval = poll_interval
        self.webhook_callback = webhook_callback

        # Price history (last 10 samples = 5 minutes at 30s intervals)
        self.price_history = deque(maxlen=10)

        # Error handling
        self.retry_delay = poll_interval
        self.max_retry_delay = 600  # 10 minutes
        self.last_successful_poll: Optional[datetime] = None
        self.consecutive_failures = 0

        # Cache
        self.cache = get_cache()

    async def _fetch_current_price(self) -> Optional[float]:
        """
        Fetch current Bitcoin price from CoinGecko

        Returns:
            Current BTC price in USD, or None if fetch fails
        """
        try:
            # Use CoinGecko simple price endpoint (no API key needed)
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                'ids': 'bitcoin',
                'vs_currencies': 'usd'
            }

            # Make synchronous request (run in executor to avoid blocking)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(url, params=params, timeout=5)
            )

            if response.status_code == 200:
                data = response.json()
                price = data.get('bitcoin', {}).get('usd')
                return float(price) if price else None
            else:
                logger.warning(f"CoinGecko returned status {response.status_code}")
                return None

        except requests.exceptions.Timeout:
            logger.warning("Price fetch timed out")
            return None
        except Exception as e:
            logger.error(f"Failed to fetch price: {e}")
            return None

    def _is_volatile(self) -> bool:
        """
        Check if recent price movement exceeds threshold

        Returns:
            True if volatility threshold exceeded
        """
        if len(self.price_history) < 2:
            return False

        oldest_price = self.price_history[0]['price']
        newest_price = self.price_history[-1]['price']

        pct_change = abs((newest_price - oldest_price) / oldest_price)

        return pct_change >= self.volatility_threshold

    def _get_price_change_pct(self) -> float:
        """Get current price change percentage"""
        if len(self.price_history) < 2:
            return 0.0

        oldest = self.price_history[0]['price']
        newest = self.price_history[-1]['price']

        return (newest - oldest) / oldest

    async def _handle_volatility(self):
        """Handle detected volatility event"""
        change_pct = self._get_price_change_pct()
        current_price = self.price_history[-1]['price']

        logger.warning(
            f"Volatility spike detected: {change_pct:+.2%} "
            f"(current price: ${current_price:,.2f})"
        )

        # Clear cache
        self.cache.clear()
        logger.info("Recommendation cache invalidated due to volatility")

        # Call webhook if configured
        if self.webhook_callback:
            try:
                await self.webhook_callback({
                    'event_type': 'volatility_event',
                    'timestamp': datetime.utcnow().isoformat(),
                    'details': {
                        'price_change_pct': round(change_pct, 4),
                        'current_price': current_price,
                        'threshold': self.volatility_threshold
                    }
                })
            except Exception as e:
                logger.error(f"Webhook callback failed: {e}")

    async def _exponential_backoff(self):
        """Apply exponential backoff after failures"""
        self.consecutive_failures += 1
        self.retry_delay = min(
            self.retry_delay * 2,
            self.max_retry_delay
        )

        logger.info(f"Backing off: {self.retry_delay}s (failures: {self.consecutive_failures})")
        await asyncio.sleep(self.retry_delay)

    async def run(self):
        """
        Main monitoring loop

        Polls price every `poll_interval` seconds, maintains history,
        and triggers actions on volatility spikes.
        """
        logger.info(
            f"Price monitor started (threshold: {self.volatility_threshold:.1%}, "
            f"interval: {self.poll_interval}s)"
        )

        while True:
            try:
                # Fetch current price
                price = await self._fetch_current_price()

                if price is not None:
                    # Success - reset backoff
                    self.retry_delay = self.poll_interval
                    self.consecutive_failures = 0
                    self.last_successful_poll = datetime.utcnow()

                    # Add to history
                    self.price_history.append({
                        'price': price,
                        'timestamp': datetime.utcnow()
                    })

                    logger.debug(f"Price fetched: ${price:,.2f}")

                    # Check for volatility
                    if self._is_volatile():
                        await self._handle_volatility()

                    # Normal sleep
                    await asyncio.sleep(self.poll_interval)

                else:
                    # Fetch failed - use backoff
                    logger.warning("Price fetch failed, using last known price")

                    # If we have history, continue with last known price
                    if self.price_history:
                        logger.debug("Continuing with cached price history")
                        await asyncio.sleep(self.poll_interval)
                    else:
                        # No history - apply backoff
                        await self._exponential_backoff()

            except asyncio.CancelledError:
                logger.info("Price monitor cancelled")
                break

            except Exception as e:
                logger.error(f"Error in price monitor: {e}", exc_info=True)
                await self._exponential_backoff()

    def get_current_price(self) -> Optional[float]:
        """
        Get last known price from history

        Returns:
            Latest price, or None if no history
        """
        if self.price_history:
            return self.price_history[-1]['price']
        return None

    def get_stats(self) -> Dict:
        """
        Get monitor statistics for observability

        Returns:
            Dictionary with monitor stats
        """
        return {
            'status': 'healthy' if self.consecutive_failures == 0 else 'degraded',
            'last_successful_poll': self.last_successful_poll.isoformat() if self.last_successful_poll else None,
            'consecutive_failures': self.consecutive_failures,
            'retry_delay_seconds': self.retry_delay,
            'current_price': self.get_current_price(),
            'price_history_length': len(self.price_history),
            'volatility_threshold': self.volatility_threshold
        }
