#!/usr/bin/env python3
"""
Backfill Weight History

Creates daily weight history entries for historical dates where recommendations exist
but weight history is missing. This allows the Weight Evolution chart to show trends.
"""

import logging
from datetime import datetime, timedelta

from src.database.models import Recommendation, WeightHistory
from src.database.session import get_db_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def backfill_weight_history():
    """
    Backfill weight history with daily entries.

    Strategy:
    1. Find the date range of existing recommendations
    2. For each day in that range, check if a weight history entry exists
    3. If not, create one using:
       - Existing weight if available (from nearest optimization)
       - Default prior weights if no optimization has run yet
    """

    with get_db_session() as session:
        # Get existing weight history
        existing_weights = session.query(WeightHistory).order_by(WeightHistory.timestamp).all()

        if not existing_weights:
            logger.warning("No existing weight history found. Run weight optimization first.")
            return

        # Get recommendation date range
        first_rec = session.query(Recommendation).order_by(Recommendation.timestamp).first()

        if not first_rec:
            logger.warning("No recommendations found. Nothing to backfill.")
            return

        start_date = first_rec.timestamp.date()
        end_date = datetime.utcnow().date()

        logger.info(f"Backfilling weight history from {start_date} to {end_date}")

        # Get existing weight dates to avoid duplicates
        existing_dates = {w.timestamp.date() for w in existing_weights}

        # Create weight history for each day
        current_date = start_date
        added_count = 0

        # Use the first existing weight as starting point
        current_weights = {
            "technical": existing_weights[0].weight_technical,
            "reddit": existing_weights[0].weight_reddit,
            "news": existing_weights[0].weight_news,
            "sharpe_technical": existing_weights[0].sharpe_technical,
            "sharpe_reddit": existing_weights[0].sharpe_reddit,
            "sharpe_news": existing_weights[0].sharpe_news,
        }

        # Calculate days from first recommendation for Bayesian factor
        days_from_start = 0

        while current_date <= end_date:
            if current_date not in existing_dates:
                # Check if there's an optimization on this day (from existing_weights)
                opt_on_day = None
                for w in existing_weights:
                    if w.timestamp.date() == current_date:
                        opt_on_day = w
                        break

                # If there's an optimization, use its weights
                if opt_on_day:
                    current_weights = {
                        "technical": opt_on_day.weight_technical,
                        "reddit": opt_on_day.weight_reddit,
                        "news": opt_on_day.weight_news,
                        "sharpe_technical": opt_on_day.sharpe_technical,
                        "sharpe_reddit": opt_on_day.sharpe_reddit,
                        "sharpe_news": opt_on_day.sharpe_news,
                    }

                # Calculate Bayesian prior factor (decreases over time)
                prior_factor = max(0.0, 0.7 - (days_from_start / 30.0) * 0.7)

                # Create weight history entry
                new_entry = WeightHistory(
                    timestamp=datetime.combine(current_date, datetime.min.time()),
                    weight_technical=current_weights["technical"],
                    weight_reddit=current_weights["reddit"],
                    weight_news=current_weights["news"],
                    trigger_reason="backfill_daily",
                    days_of_data=days_from_start,
                    prior_weight_factor=prior_factor,
                    sharpe_technical=current_weights["sharpe_technical"],
                    sharpe_reddit=current_weights["sharpe_reddit"],
                    sharpe_news=current_weights["sharpe_news"],
                )
                session.add(new_entry)
                added_count += 1

                if added_count % 10 == 0:
                    logger.info(f"Added {added_count} entries...")

            current_date += timedelta(days=1)
            days_from_start += 1

        session.commit()
        logger.info(f"Backfill complete! Added {added_count} weight history entries.")


if __name__ == "__main__":
    backfill_weight_history()
