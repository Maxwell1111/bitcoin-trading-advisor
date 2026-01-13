"""
Database session management and initialization

Uses scoped_session for thread-safe session handling in FastAPI
"""

import logging
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import StaticPool

from .models import Base, WeightHistory

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_DIR = Path(__file__).parent.parent.parent / "data"
DATABASE_PATH = DATABASE_DIR / "advisor.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Global engine and session factory
_engine = None
_Session = None


def get_engine():
    """Get or create the database engine"""
    global _engine

    if _engine is None:
        # Ensure data directory exists
        DATABASE_DIR.mkdir(parents=True, exist_ok=True)

        # Create engine with appropriate settings for SQLite
        _engine = create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False},  # Needed for SQLite with multiple threads
            poolclass=StaticPool,  # Use static pool for SQLite
            echo=False,  # Set to True for SQL debugging
        )

        logger.info(f"Database engine created: {DATABASE_PATH}")

    return _engine


def get_session_factory():
    """Get or create the session factory"""
    global _Session

    if _Session is None:
        engine = get_engine()
        session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
        _Session = scoped_session(session_factory)
        logger.info("Session factory created")

    return _Session


def get_db_session():
    """
    Get a database session

    Usage:
        with get_db_session() as session:
            # Use session here
            session.commit()

    The session will automatically close when exiting the context
    """
    Session = get_session_factory()
    return Session()


def init_database(drop_existing=False):
    """
    Initialize the database

    Creates all tables and inserts default data if needed.

    Args:
        drop_existing: If True, drops all existing tables first (DANGER!)

    Returns:
        True if successful, False otherwise
    """
    try:
        engine = get_engine()

        if drop_existing:
            logger.warning("Dropping all existing tables!")
            Base.metadata.drop_all(engine)

        # Create all tables (will skip if already exist)
        try:
            Base.metadata.create_all(engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            # Tables likely already exist, which is fine
            if "already exists" in str(e):
                logger.info("Database tables already exist (skipping creation)")
            else:
                raise

        # Check if we need to initialize default weights
        Session = get_session_factory()
        with Session() as session:
            weight_count = session.query(WeightHistory).count()

            if weight_count == 0:
                # Insert initial weights (60% technical, 25% reddit, 15% news)
                initial_weights = WeightHistory(
                    weight_technical=0.60,
                    weight_reddit=0.25,
                    weight_news=0.15,
                    trigger_reason="initial_setup",
                    days_of_data=0,
                    prior_weight_factor=1.0,
                )
                session.add(initial_weights)
                session.commit()
                logger.info("Initial weights inserted: tech=0.60, reddit=0.25, news=0.15")

        logger.info(f"Database initialized at: {DATABASE_PATH}")
        return True

    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        return False


def close_database():
    """Close all database connections"""
    global _Session, _engine

    if _Session:
        _Session.remove()
        _Session = None
        logger.info("Database sessions closed")

    if _engine:
        _engine.dispose()
        _engine = None
        logger.info("Database engine disposed")


# For backwards compatibility and convenience
def get_db():
    """Alias for get_db_session()"""
    return get_db_session()
