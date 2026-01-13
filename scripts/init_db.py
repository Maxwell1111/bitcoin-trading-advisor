#!/usr/bin/env python3
"""
Initialize the Bitcoin Advisor database

Creates the database schema and inserts default weights.
Run this before starting the API for the first time.

Usage:
    python scripts/init_db.py                    # Create tables
    python scripts/init_db.py --reset            # Drop and recreate (DANGER!)
    python scripts/init_db.py --check            # Just check status
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import get_db_session, init_database
from src.database.models import AccuracyAggregate, Recommendation, WeightHistory


def check_database_status():
    """Check and display database status"""
    try:
        with get_db_session() as session:
            rec_count = session.query(Recommendation).count()
            weight_count = session.query(WeightHistory).count()
            agg_count = session.query(AccuracyAggregate).count()

            print("\n" + "=" * 60)
            print("DATABASE STATUS")
            print("=" * 60)
            print(f"Recommendations:      {rec_count:,}")
            print(f"Weight History:       {weight_count:,}")
            print(f"Accuracy Aggregates:  {agg_count:,}")

            if weight_count > 0:
                latest_weight = (
                    session.query(WeightHistory).order_by(WeightHistory.timestamp.desc()).first()
                )
                print("\nLatest Weights:")
                print(f"  Technical: {latest_weight.weight_technical:.2%}")
                print(f"  Reddit:    {latest_weight.weight_reddit:.2%}")
                print(f"  News:      {latest_weight.weight_news:.2%}")
                print(f"  Updated:   {latest_weight.timestamp}")
                print(f"  Reason:    {latest_weight.trigger_reason}")

            print("=" * 60 + "\n")
            return True

    except Exception as e:
        print(f"\n❌ Error checking database: {e}\n")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Initialize Bitcoin Advisor database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/init_db.py              # Initialize database
  python scripts/init_db.py --reset      # Reset database (WARNING: deletes data!)
  python scripts/init_db.py --check      # Check database status
        """,
    )
    parser.add_argument(
        "--reset", action="store_true", help="Drop and recreate all tables (DELETES ALL DATA!)"
    )
    parser.add_argument(
        "--check", action="store_true", help="Check database status without modifying"
    )

    args = parser.parse_args()

    if args.check:
        check_database_status()
        return

    if args.reset:
        response = input(
            "\n⚠️  WARNING: This will DELETE ALL DATA in the database!\n"
            "Are you sure you want to continue? (type 'yes' to confirm): "
        )
        if response.lower() != "yes":
            print("❌ Reset cancelled.")
            return

    print("\n" + "=" * 60)
    print("INITIALIZING DATABASE")
    print("=" * 60)

    success = init_database(drop_existing=args.reset)

    if success:
        print("✅ Database initialized successfully!\n")
        check_database_status()
    else:
        print("❌ Database initialization failed!\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
