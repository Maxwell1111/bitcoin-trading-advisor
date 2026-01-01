#!/usr/bin/env python3
"""
Quick integration test for adaptive system

Tests that all services can be instantiated and basic operations work.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.database import init_database, get_db_session
from src.database.models import Recommendation, WeightHistory
from src.services import (
    get_weight_manager,
    HistoryTracker,
    ValidationService
)

def test_database():
    """Test database initialization"""
    print("Testing database...")

    success = init_database()
    print(f"  Database init: {'✓' if success else '✗'}")

    # Check if we can query
    with get_db_session() as session:
        count = session.query(Recommendation).count()
        print(f"  Recommendations in DB: {count}")

    return success

def test_weight_manager():
    """Test WeightManager"""
    print("\nTesting WeightManager...")

    wm = get_weight_manager()
    weights = wm.get_current_weights()

    print(f"  Current weights: tech={weights['technical_weight']:.2f}, "
          f"reddit={weights['reddit_weight']:.2f}, news={weights['news_weight']:.2f}")

    total = sum(weights.values())
    assert abs(total - 1.0) < 0.01, f"Weights don't sum to 1.0: {total}"
    print(f"  Weights sum to 1.0: ✓")

    return True

def test_history_tracker():
    """Test HistoryTracker"""
    print("\nTesting HistoryTracker...")

    ht = HistoryTracker()

    # Create a mock recommendation
    mock_rec = {
        'recommendation': 'buy',
        'confidence': 0.72,
        'signals': {
            'technical': {
                'recommendation': 'buy',
                'confidence': 0.65,
                'score': 0.39,
                'weight': 0.6
            },
            'sentiment': {
                'recommendation': 'buy',
                'confidence': 0.72,
                'score': 0.288,
                'weight': 0.4
            }
        },
        'targets': {
            'entry': 60000,
            'target_1': 63000,
            'target_2': 66000,
            'stop_loss': 58200
        },
        'reasoning': 'Test recommendation'
    }

    try:
        rec_id = ht.save_recommendation(
            rec_data=mock_rec,
            current_price=60000,
            weights={'technical_weight': 0.6, 'reddit_weight': 0.25, 'news_weight': 0.15},
            operating_mode='normal'
        )
        print(f"  Saved test recommendation: ID={rec_id} ✓")

        # Retrieve it
        retrieved = ht.get_recommendation(rec_id)
        assert retrieved is not None
        print(f"  Retrieved recommendation: ✓")

        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        return False

def test_validation_service():
    """Test ValidationService"""
    print("\nTesting ValidationService...")

    vs = ValidationService()

    # Test Kelly Criterion calculation
    kelly = vs.calculate_kelly_fraction(
        confidence=0.72,
        win_payout_pct=0.05,
        loss_payout_pct=0.03
    )
    print(f"  Kelly fraction (72% conf, 5% win, 3% loss): {kelly:.3f} ✓")

    return True

def main():
    print("=" * 60)
    print("BITCOIN ADVISOR - INTEGRATION TEST")
    print("=" * 60)

    results = []

    results.append(("Database", test_database()))
    results.append(("WeightManager", test_weight_manager()))
    results.append(("HistoryTracker", test_history_tracker()))
    results.append(("ValidationService", test_validation_service()))

    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)

    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {name:20s} {status}")

    all_passed = all(success for _, success in results)

    print("=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("⚠️  SOME TESTS FAILED")
    print("=" * 60)

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
