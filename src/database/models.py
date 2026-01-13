"""
SQLAlchemy models for adaptive recommendation system

Based on TECHNICAL_SPEC.md data models section
"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Recommendation(Base):
    """
    Primary storage for all issued recommendations

    Stores complete recommendation data including signals, weights used,
    and targets for later validation and accuracy tracking.
    """

    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Core recommendation
    recommendation = Column(String(50), nullable=False, index=True)  # 'buy', 'sell', 'hold', etc.
    confidence = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)

    # Weights used at time of recommendation
    weight_technical = Column(Float, nullable=False)
    weight_reddit = Column(Float, nullable=False)
    weight_news = Column(Float, nullable=False)

    # Signal scores
    technical_score = Column(Float, nullable=False)
    reddit_score = Column(Float, nullable=False)
    news_score = Column(Float, nullable=False)

    # Individual signal recommendations
    technical_recommendation = Column(String(50))
    reddit_recommendation = Column(String(50))
    news_recommendation = Column(String(50))

    # Targets for validation
    entry_price = Column(Float)
    target_1 = Column(Float)
    target_2 = Column(Float)
    stop_loss = Column(Float)

    # Operating metadata
    operating_mode = Column(
        String(50), nullable=False, index=True
    )  # 'normal', 'degraded', 'degraded_preferred'
    signal_sources = Column(Text)  # JSON array: ['technical', 'reddit', 'news']
    request_params = Column(Text)  # JSON: {days, news_days, max_articles}

    # Full details stored as JSON
    full_signals = Column(JSON)  # Complete technical + sentiment breakdown
    reasoning = Column(Text)

    # Relationships
    price_snapshots = relationship(
        "PriceSnapshot", back_populates="recommendation", cascade="all, delete-orphan"
    )
    validation_results = relationship(
        "ValidationResult", back_populates="recommendation", cascade="all, delete-orphan"
    )

    # Indexes defined in __table_args__
    __table_args__ = (
        Index("idx_timestamp", "timestamp"),
        Index("idx_mode", "operating_mode"),
        Index("idx_recommendation", "recommendation"),
    )

    def __repr__(self):
        return f"<Recommendation(id={self.id}, rec={self.recommendation}, conf={self.confidence:.2f}, time={self.timestamp})>"


class PriceSnapshot(Base):
    """
    Price tracking for validation

    Stores Bitcoin price at various time offsets from recommendation
    for multi-horizon accuracy validation.
    """

    __tablename__ = "price_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recommendation_id = Column(
        Integer, ForeignKey("recommendations.id"), nullable=False, index=True
    )

    snapshot_type = Column(String(20), nullable=False)  # 'initial', '4h', '24h', '7d', 'event'
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    price = Column(Float, nullable=False)
    time_offset_hours = Column(Float)  # Hours since recommendation

    # Relationship
    recommendation = relationship("Recommendation", back_populates="price_snapshots")

    __table_args__ = (
        Index("idx_rec_id", "recommendation_id"),
        Index("idx_timestamp", "timestamp"),
    )

    def __repr__(self):
        return f"<PriceSnapshot(rec_id={self.recommendation_id}, type={self.snapshot_type}, price={self.price})>"


class ValidationResult(Base):
    """
    Pre-calculated accuracy outcomes

    Stores the results of validating recommendations at different
    time horizons and with different validation methods.
    """

    __tablename__ = "validation_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recommendation_id = Column(
        Integer, ForeignKey("recommendations.id"), nullable=False, index=True
    )

    validation_type = Column(
        String(20), nullable=False, index=True
    )  # 'quick_4h', 'standard_24h', 'extended_7d', 'event_based'
    validated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Outcome
    outcome = Column(
        String(20), nullable=False, index=True
    )  # 'success', 'failure', 'expired', 'pending'
    outcome_reason = Column(
        String(100)
    )  # 'target_reached', 'stop_loss_hit', 'directional', 'timeout'

    # Performance metrics
    price_change_pct = Column(Float)
    target_reached = Column(Boolean)
    time_to_outcome_hours = Column(Float)

    # Simulated trading (Kelly Criterion)
    position_size_pct = Column(Float)  # What % of portfolio was simulated
    pnl_pct = Column(Float)  # Profit/loss %
    kelly_fraction = Column(Float)  # Kelly criterion fraction used

    # Relationship
    recommendation = relationship("Recommendation", back_populates="validation_results")

    __table_args__ = (
        Index("idx_rec_id", "recommendation_id"),
        Index("idx_type", "validation_type"),
        Index("idx_outcome", "outcome"),
    )

    def __repr__(self):
        return f"<ValidationResult(rec_id={self.recommendation_id}, type={self.validation_type}, outcome={self.outcome})>"


class AccuracyAggregate(Base):
    """
    Daily rollup statistics for fast queries

    Pre-aggregated statistics by day for efficient dashboard queries
    and trend analysis without scanning individual recommendations.
    """

    __tablename__ = "accuracy_aggregates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False, unique=True, index=True)

    # Volume
    total_recommendations = Column(Integer, nullable=False, default=0)
    buy_count = Column(Integer, default=0)
    sell_count = Column(Integer, default=0)
    hold_count = Column(Integer, default=0)

    # Accuracy by horizon
    quick_4h_accuracy = Column(Float)
    standard_24h_accuracy = Column(Float)
    extended_7d_accuracy = Column(Float)
    event_based_accuracy = Column(Float)

    # By signal source
    technical_only_accuracy = Column(Float)
    reddit_only_accuracy = Column(Float)
    news_only_accuracy = Column(Float)
    combined_accuracy = Column(Float)

    # Risk metrics
    sharpe_ratio_technical = Column(Float)
    sharpe_ratio_reddit = Column(Float)
    sharpe_ratio_news = Column(Float)
    sharpe_ratio_combined = Column(Float)

    # Operating mode
    mode = Column(String(50))  # Dominant mode for the day
    degraded_time_pct = Column(Float)  # % of day in degraded mode

    __table_args__ = (Index("idx_date", "date"),)

    def __repr__(self):
        return f"<AccuracyAggregate(date={self.date.date()}, total={self.total_recommendations}, acc={self.standard_24h_accuracy})>"


class WeightHistory(Base):
    """
    Track weight changes over time

    Records every change to signal weights with metadata about
    what triggered the change and supporting statistics.
    """

    __tablename__ = "weight_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Weights (must sum to 1.0)
    weight_technical = Column(Float, nullable=False)
    weight_reddit = Column(Float, nullable=False)
    weight_news = Column(Float, nullable=False)

    # What triggered the change
    trigger_reason = Column(
        String(100)
    )  # 'daily_recalc', 'mode_change', 'manual_override', 'initial_setup'

    # Supporting data
    days_of_data = Column(Integer)
    prior_weight_factor = Column(Float)  # For Bayesian cold start

    sharpe_technical = Column(Float)
    sharpe_reddit = Column(Float)
    sharpe_news = Column(Float)
    sharpe_combined = Column(Float)

    __table_args__ = (Index("idx_timestamp", "timestamp"),)

    def __repr__(self):
        return f"<WeightHistory(time={self.timestamp}, tech={self.weight_technical:.2f}, reddit={self.weight_reddit:.2f}, news={self.weight_news:.2f})>"
