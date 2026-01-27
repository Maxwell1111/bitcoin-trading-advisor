#!/usr/bin/env python3
"""
Test PostgreSQL Connection

Use this to verify your PostgreSQL database connection works.
Set the DATABASE_URL environment variable before running.

Usage:
    export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
    python scripts/test_postgres_connection.py
"""

import os
import sys

# Check if DATABASE_URL is set
if "DATABASE_URL" not in os.environ:
    print("❌ ERROR: DATABASE_URL environment variable not set")
    print("\nSet it like this:")
    print('  export DATABASE_URL="postgresql://user:pass@host:5432/dbname"')
    print("\nOr get it from Render:")
    print("  1. Go to your PostgreSQL database on Render")
    print("  2. Copy the 'Internal Database URL'")
    print("  3. Run: export DATABASE_URL='<paste_url_here>'")
    sys.exit(1)

print("Testing PostgreSQL connection...")
print(f"DATABASE_URL: {os.environ['DATABASE_URL'][:30]}...")

try:
    from src.database.models import WeightHistory
    from src.database.session import get_db_session, get_engine, init_database

    # Test engine creation
    print("\n1. Creating database engine...")
    engine = get_engine()
    print(f"   ✓ Engine created: {engine.url.drivername}")

    # Test connection
    print("\n2. Testing connection...")
    with engine.connect() as conn:
        result = conn.execute("SELECT 1")
        print("   ✓ Connection successful!")

    # Test table creation
    print("\n3. Initializing database tables...")
    success = init_database()
    if success:
        print("   ✓ Tables created successfully")
    else:
        print("   ❌ Table creation failed")
        sys.exit(1)

    # Test query
    print("\n4. Testing query...")
    with get_db_session() as db:
        weight_count = db.query(WeightHistory).count()
        print(f"   ✓ Query successful! Found {weight_count} weight history records")

    print("\n" + "=" * 60)
    print("✅ PostgreSQL connection test PASSED!")
    print("=" * 60)
    print("\nYour database is ready to use.")
    print("Set this environment variable on Render:")
    print("  Key: DATABASE_URL")
    print(f"  Value: {os.environ['DATABASE_URL']}")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
