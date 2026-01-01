# Bitcoin Portfolio Advisor - Technical Specification
## Adaptive Weighting System & Production Enhancements

**Version:** 1.0
**Date:** 2025-12-31
**Status:** Design Phase

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Overview](#system-overview)
3. [Architecture](#architecture)
4. [Core Features](#core-features)
5. [Data Models](#data-models)
6. [API Specification](#api-specification)
7. [Background Services](#background-services)
8. [Testing Strategy](#testing-strategy)
9. [Deployment & Operations](#deployment--operations)
10. [Future Considerations](#future-considerations)

---

## Executive Summary

### Goals

Transform the Bitcoin Portfolio Advisor from a stateless API into an adaptive system that learns from its historical performance and automatically optimizes recommendation accuracy over time.

### Key Value Propositions

1. **Adaptive Intelligence**: Automatically adjusts technical vs sentiment weighting based on historical accuracy
2. **Resilient Operation**: Gracefully degrades when external dependencies fail, automatically recovers
3. **Production-Ready**: Comprehensive observability, caching, and error handling
4. **Self-Improving**: Validates predictions, measures accuracy, and optimizes behavior

### Design Philosophy

- **Pragmatic over Perfect**: SQLite over complex distributed systems; background threads over microservices
- **Availability over Consistency**: Degrade gracefully rather than fail hard
- **Transparency**: Expose operating mode and system state to users
- **De-risk Core Value**: MVP focuses on proving adaptive weighting improves accuracy

---

## System Overview

### Current State (Baseline)

- FastAPI REST API serving trading recommendations
- Combines technical analysis (RSI, MACD) with sentiment analysis (news)
- Static weights: 60% technical, 40% sentiment
- Stateless: no memory of past recommendations
- Basic caching and error handling

### Target State (V1 MVP)

- **Adaptive Weighting**: Dynamically adjusts technical/sentiment weights based on backtested performance
- **Historical Tracking**: Persists all recommendations with full metadata
- **Accuracy Measurement**: Multi-horizon validation (4h, 24h, 7d) with event-based triggers
- **Operating Modes**: `normal`, `degraded` (single-signal fallback), `degraded_preferred` (auto-failover)
- **Enhanced Caching**: 5-minute TTL with volatility-triggered invalidation
- **Comprehensive Observability**: Metrics for weights, accuracy, cache performance, dependency health

---

## Architecture

### High-Level Components

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Application                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   API Routes │  │ Recommendation│  │   Caching    │    │
│  │              │  │    Engine     │  │   Layer      │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Background Services (asyncio tasks)          │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │ • Price Monitor    • Validation Jobs                 │  │
│  │ • Weight Optimizer • Cache Invalidator               │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
         ┌──────▼──────┐          ┌──────▼──────┐
         │   SQLite    │          │   Redis     │
         │  (History)  │          │  (Cache)    │
         └─────────────┘          └─────────────┘
                │
    ┌───────────┴───────────┐
    │                       │
┌───▼────┐           ┌──────▼──────┐
│CoinGecko│          │  NewsAPI    │
│  (Price)│          │ (Sentiment) │
└─────────┘          └─────────────┘
```

### Design Decisions

#### Single-Process Architecture
**Decision**: All components run in FastAPI process with asyncio background tasks
**Rationale**: Simplicity for MVP; avoids orchestration complexity
**Tradeoff**: Tasks die on restart; not horizontally scalable (single-instance only)
**Future**: Migrate to Celery/separate services if scaling needed

#### SQLite for Persistence
**Decision**: Local SQLite database with tiered data retention
**Rationale**: No separate DB server; sufficient for single-instance; fast local queries
**Tradeoff**: Write concurrency limits; doesn't support multi-instance deployments
**Mitigation**: Use SQLAlchemy ORM for eventual PostgreSQL migration path

#### In-Memory Cache (Redis Optional)
**Decision**: Python dict for MVP; Redis if available
**Ratability**: Minimal dependencies; instant local access
**Tradeoff**: Cache lost on restart; not shared across instances
**Future**: Redis for production multi-instance deployments

---

## Core Features

### 1. Adaptive Weighting System

#### Overview
Automatically adjusts the weight given to technical vs sentiment signals based on historical backtesting performance.

#### Algorithm

**Accuracy Measurement: Risk-Adjusted Returns (Sharpe Ratio)**

For each signal source (technical, sentiment), simulate trades using:
- **Position Sizing**: Kelly Criterion with linear confidence mapping
  - `edge = confidence` (0.72 → 72% win probability)
  - `kelly_fraction = (edge * win_payout - loss_prob * loss_payout) / win_payout`
  - Position size = `kelly_fraction * portfolio_value`

- **Constraints**:
  - Maximum position: 25% of portfolio
  - Minimum confidence threshold: 0.60 (below this, treat as "hold", no trade)
  - Dynamic cap: Reduce max position if recent accuracy drops below 55%

- **Risk-Free Rate**: 4.5% annual (US Treasury rate), prorated for holding period

**Sharpe Ratio Calculation**:
```python
portfolio_returns = []  # Returns from each simulated trade
mean_return = average(portfolio_returns)
std_return = stdev(portfolio_returns)
sharpe = (mean_return - risk_free_rate) / std_return
```

**Weight Adjustment**:
```python
# Calculate Sharpe ratios for technical-only vs sentiment-only
sharpe_technical = calculate_sharpe(technical_signals)
sharpe_sentiment = calculate_sharpe(sentiment_signals)

# Normalize to weights (higher Sharpe → higher weight)
total_sharpe = sharpe_technical + sharpe_sentiment
weight_technical = sharpe_technical / total_sharpe
weight_sentiment = sharpe_sentiment / total_sharpe

# Apply smoothing to prevent wild swings
new_weight = 0.7 * current_weight + 0.3 * calculated_weight
```

#### Cold Start Problem
**Strategy**: Bayesian priors
**Initial Weights**: 60% technical, 40% sentiment (current proven baseline)
**Transition**:
- First 30 days: Strong prior (70% weight on initial belief)
- Days 30-90: Linear transition to pure data-driven
- After 90 days: Fully data-driven with rolling 90-day window

```python
if days_of_data < 30:
    prior_weight = 0.7
    final_weight = prior_weight * INITIAL_WEIGHTS + (1 - prior_weight) * calculated_weight
elif days_of_data < 90:
    prior_weight = 0.7 * (90 - days_of_data) / 60  # Linear decay
    final_weight = prior_weight * INITIAL_WEIGHTS + (1 - prior_weight) * calculated_weight
else:
    final_weight = calculated_weight
```

#### Rolling Window
**Window Size**: 30 days of recommendations
**Recalculation Frequency**: Daily at 00:00 UTC
**Behavior**: Only recommendations from last 30 days affect current weights
**Rationale**: Market regime changes; recent performance more predictive

---

### 2. Multi-Horizon Validation System

#### Validation Schedules

Recommendations are validated at multiple time horizons to capture different trading styles:

| Horizon | Check Time | Success Criteria | Use Case |
|---------|-----------|------------------|----------|
| **Quick** | 4 hours | Directional movement >0.5% | Day trading validation |
| **Standard** | 24 hours | Directional movement >1% OR target_1 hit | Primary accuracy metric |
| **Extended** | 7 days | target_1 reached before stop_loss | Position trading validation |
| **Event-Based** | Continuous | Price crosses target or stop_loss | Real trading simulation |

**Composite Scoring**:
```python
# Weight different horizons for overall accuracy
accuracy_score = (
    0.2 * quick_accuracy +      # 20% weight
    0.5 * standard_accuracy +   # 50% weight (primary)
    0.2 * extended_accuracy +   # 20% weight
    0.1 * event_based_accuracy  # 10% weight
)
```

#### Market-Hours Awareness
Bitcoin trades 24/7, but validation accounts for:
- **Weekend Volatility**: Lower volume, potentially less reliable signals
- **Timezone Considerations**: Major market opens (US, Asia, Europe)
- **Implementation**: Flag weekends in validation data; option to weight weekday accuracy higher (80% vs 20%)

#### Event-Based Validation
**Trigger**: Background job checks prices every 5 minutes
**Logic**:
```python
for recommendation in pending_validations:
    current_price = get_current_price()
    if current_price >= recommendation.target_1:
        mark_success(recommendation, "target_reached")
    elif current_price <= recommendation.stop_loss:
        mark_failure(recommendation, "stop_loss_hit")
    elif days_since(recommendation) > 30:
        mark_expired(recommendation)  # Never resolved
```

---

### 3. Operating Modes & Degraded States

#### Mode Definitions

| Mode | Description | Signals Used | Weight Source |
|------|-------------|--------------|---------------|
| **normal** | Both dependencies healthy | Technical + Sentiment | Adaptive (historical) |
| **degraded** | One dependency failed | Technical OR Sentiment | Static fallback |
| **degraded_preferred** | Degraded mode outperforms | Technical OR Sentiment | Adaptive (degraded-only) |

#### Mode Transitions

```
┌─────────┐     Dependency Fail      ┌──────────┐
│ normal  │─────────────────────────>│ degraded │
└─────────┘                           └──────────┘
     ^                                     │
     │                                     │
     │         Dependency Recovers         │
     └─────────────────────────────────────┘
                                           │
                                           │ Auto-Failover
                                           │ (degraded Sharpe > normal Sharpe
                                           │  for 14+ days)
                                           │
                                           v
                                  ┌─────────────────┐
                                  │degraded_preferred│
                                  └─────────────────┘
                                           │
                                           │ Manual Override
                                           │ (config change)
                                           v
                                     ┌─────────┐
                                     │ normal  │
                                     └─────────┘
```

#### Auto-Failover Logic

**Trigger Conditions**:
1. System has been in `degraded` mode for at least 7 days
2. Degraded-mode Sharpe ratio > normal-mode Sharpe ratio
3. Statistical significance: p-value < 0.05 (t-test comparing performance)
4. Minimum 50 recommendations in each mode for comparison

**Action**:
1. Switch to `degraded_preferred` mode
2. Send webhook notification (if configured)
3. Log event with full metrics
4. Update product positioning: "Technical-focused with sentiment enhancement"

**Acceptance Philosophy**: If technical-only genuinely outperforms, we accept it rather than force combined analysis. This is a feature discovery, not a bug.

#### Degraded Mode Confidence Scoring

**Strategy**: Include historical degraded-mode accuracy
**Implementation**:
```python
if operating_mode == "degraded":
    # Track separate accuracy for degraded vs normal
    degraded_accuracy = get_historical_degraded_accuracy()

    # Use degraded accuracy to calibrate confidence
    confidence = base_confidence * (degraded_accuracy / normal_accuracy)

    # Ensure confidence reflects reality of single-signal operation
    confidence = min(confidence, 0.75)  # Cap at 75% in degraded mode
```

---

### 4. Enhanced Caching Strategy

#### Cache Configuration

**TTL**: 5 minutes (300 seconds)
**Cache Key**: `recommendation:{days}:{news_days}:{max_articles}:{use_mock}`
**Storage**: In-memory dict (MVP) or Redis (production)

#### Volatility-Triggered Invalidation

**Monitoring**: Background thread polls CoinGecko every 30 seconds
**Volatility Threshold**: 3% price change in 5-minute window

```python
async def price_monitor():
    """Background task monitoring for volatility"""
    price_history = deque(maxlen=10)  # Last 10 checks (5 min window)

    while True:
        try:
            current_price = await get_btc_price()
            price_history.append({
                'price': current_price,
                'timestamp': datetime.now()
            })

            if len(price_history) >= 2:
                oldest = price_history[0]['price']
                newest = price_history[-1]['price']
                pct_change = abs((newest - oldest) / oldest)

                if pct_change >= 0.03:  # 3% threshold
                    logger.warning(f"Volatility detected: {pct_change:.1%}")
                    invalidate_all_caches()
                    send_webhook_if_configured("volatility_event", {
                        'change': pct_change,
                        'price': newest
                    })

        except Exception as e:
            # Exponential backoff on failures
            logger.error(f"Price fetch failed: {e}")
            await exponential_backoff()

            # Fallback to last known price
            if price_history:
                logger.info("Using last known price for volatility check")

        await asyncio.sleep(30)
```

**Error Handling**:
- **Exponential Backoff**: Start 30s, double on each failure, max 600s (10 min)
- **Fallback**: Use last known good price if fetch fails
- **Recovery**: Automatically resume normal polling when fetch succeeds

#### Cache Race Condition

**Acknowledged Risk**: Volatility spike 1 second after cache refresh = stale data for up to 5 min
**Mitigation**: Acceptable tradeoff for aggressive 5-min TTL
**User Expectation**: Not marketed as real-time; suitable for position trading, not scalping

---

### 5. Observability & Monitoring

#### Metrics Endpoints

**GET /api/metrics** (or `/api/recommendation?include=stats`)

Response includes:
```json
{
  "system_health": {
    "operating_mode": "normal",
    "mode_since": "2025-12-30T10:00:00Z",
    "database_status": "healthy",
    "cache_status": "healthy"
  },
  "adaptive_weights": {
    "current": {
      "technical": 0.65,
      "sentiment": 0.35,
      "last_updated": "2025-12-31T00:00:00Z"
    },
    "accuracy_stats": {
      "24h": {
        "technical": 0.68,
        "sentiment": 0.54,
        "combined": 0.72
      },
      "7d": {
        "technical": 0.65,
        "sentiment": 0.58,
        "combined": 0.70
      },
      "30d": {
        "technical": 0.62,
        "sentiment": 0.61,
        "combined": 0.69
      }
    },
    "sharpe_ratios": {
      "technical": 1.42,
      "sentiment": 0.98,
      "combined": 1.68
    }
  },
  "cache_performance": {
    "hit_rate": 0.83,
    "invalidations_24h": 12,
    "avg_generation_time_ms": 8234
  },
  "dependencies": {
    "coingecko": {
      "status": "healthy",
      "last_success": "2025-12-31T15:30:00Z",
      "avg_response_ms": 234,
      "error_rate_24h": 0.02
    },
    "newsapi": {
      "status": "healthy",
      "last_success": "2025-12-31T15:29:00Z",
      "avg_response_ms": 1823,
      "error_rate_24h": 0.01
    }
  }
}
```

#### Health Check Enhancement

**GET /health** - Extended response:
```json
{
  "status": "healthy",
  "components": {
    "api": "ok",
    "database": "ok",
    "background_tasks": {
      "price_monitor": "running",
      "validation_job": "running",
      "weight_optimizer": "running"
    },
    "external_dependencies": {
      "coingecko": "ok",
      "newsapi": "ok"
    }
  },
  "uptime_seconds": 86400,
  "recommendations_served_24h": 1423
}
```

#### Webhook Notifications

**Configuration**: `config.yaml`
```yaml
webhooks:
  enabled: true
  url: "https://your-monitoring-service.com/hooks/advisor"
  events:
    - mode_change
    - volatility_event
    - dependency_failure
    - accuracy_threshold_breach
```

**Event Payload**:
```json
{
  "event_type": "mode_change",
  "timestamp": "2025-12-31T15:45:00Z",
  "details": {
    "old_mode": "normal",
    "new_mode": "degraded_preferred",
    "reason": "technical_only_outperformed",
    "metrics": {
      "degraded_sharpe": 1.89,
      "normal_sharpe": 1.68,
      "significance": 0.023
    }
  }
}
```

---

## Data Models

### Database Schema

#### Table: `recommendations`

Primary storage for all issued recommendations.

```sql
CREATE TABLE recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    recommendation TEXT NOT NULL,  -- 'buy', 'sell', 'hold'
    confidence REAL NOT NULL,
    current_price REAL NOT NULL,

    -- Weights used
    weight_technical REAL NOT NULL,
    weight_sentiment REAL NOT NULL,

    -- Signal scores
    technical_score REAL NOT NULL,
    sentiment_score REAL NOT NULL,
    technical_recommendation TEXT,
    sentiment_recommendation TEXT,

    -- Targets
    entry_price REAL,
    target_1 REAL,
    target_2 REAL,
    stop_loss REAL,

    -- Metadata
    operating_mode TEXT NOT NULL,  -- 'normal', 'degraded', 'degraded_preferred'
    signal_sources TEXT,  -- JSON array: ['technical', 'sentiment']
    request_params TEXT,  -- JSON: {days, news_days, max_articles}

    -- Full details
    full_signals JSON,  -- Complete technical + sentiment breakdown
    reasoning TEXT,

    -- Indexes
    INDEX idx_timestamp (timestamp),
    INDEX idx_mode (operating_mode),
    INDEX idx_recommendation (recommendation)
);
```

#### Table: `price_snapshots`

Price tracking for validation.

```sql
CREATE TABLE price_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recommendation_id INTEGER NOT NULL,
    snapshot_type TEXT NOT NULL,  -- 'initial', '4h', '24h', '7d', 'event'
    timestamp DATETIME NOT NULL,
    price REAL NOT NULL,
    time_offset_hours REAL,  -- Hours since recommendation

    FOREIGN KEY (recommendation_id) REFERENCES recommendations(id),
    INDEX idx_rec_id (recommendation_id),
    INDEX idx_timestamp (timestamp)
);
```

#### Table: `validation_results`

Pre-calculated accuracy outcomes.

```sql
CREATE TABLE validation_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recommendation_id INTEGER NOT NULL,
    validation_type TEXT NOT NULL,  -- 'quick_4h', 'standard_24h', 'extended_7d', 'event_based'
    validated_at DATETIME NOT NULL,

    -- Outcome
    outcome TEXT NOT NULL,  -- 'success', 'failure', 'expired', 'pending'
    outcome_reason TEXT,  -- 'target_reached', 'stop_loss_hit', 'directional', 'timeout'

    -- Performance metrics
    price_change_pct REAL,
    target_reached BOOLEAN,
    time_to_outcome_hours REAL,

    -- Simulated trading
    position_size_pct REAL,  -- What % of portfolio was simulated
    pnl_pct REAL,  -- Profit/loss %
    kelly_fraction REAL,  -- Kelly criterion fraction used

    FOREIGN KEY (recommendation_id) REFERENCES recommendations(id),
    INDEX idx_rec_id (recommendation_id),
    INDEX idx_type (validation_type),
    INDEX idx_outcome (outcome)
);
```

#### Table: `accuracy_aggregates`

Daily rollup statistics for fast queries.

```sql
CREATE TABLE accuracy_aggregates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL UNIQUE,

    -- Volume
    total_recommendations INTEGER NOT NULL,
    buy_count INTEGER,
    sell_count INTEGER,
    hold_count INTEGER,

    -- Accuracy by horizon
    quick_4h_accuracy REAL,
    standard_24h_accuracy REAL,
    extended_7d_accuracy REAL,
    event_based_accuracy REAL,

    -- By signal source
    technical_only_accuracy REAL,
    sentiment_only_accuracy REAL,
    combined_accuracy REAL,

    -- Risk metrics
    sharpe_ratio_technical REAL,
    sharpe_ratio_sentiment REAL,
    sharpe_ratio_combined REAL,

    -- Operating mode
    mode TEXT,  -- Dominant mode for the day
    degraded_time_pct REAL,  -- % of day in degraded mode

    INDEX idx_date (date)
);
```

#### Table: `weight_history`

Track weight changes over time.

```sql
CREATE TABLE weight_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    weight_technical REAL NOT NULL,
    weight_sentiment REAL NOT NULL,

    -- What triggered the change
    trigger_reason TEXT,  -- 'daily_recalc', 'mode_change', 'manual_override'

    -- Supporting data
    days_of_data INTEGER,
    prior_weight_factor REAL,  -- For Bayesian cold start
    sharpe_technical REAL,
    sharpe_sentiment REAL,

    INDEX idx_timestamp (timestamp)
);
```

### Data Retention Strategy

**Tiered Retention**:

| Data Age | Retention Level | Storage |
|----------|----------------|---------|
| 0-30 days | **Full Detail** | All individual recommendations, price snapshots, validation results |
| 31-90 days | **Aggregated** | Daily aggregates only; individual records archived/deleted |
| 90+ days | **Summary** | Monthly rollup stats; daily aggregates archived |

**Implementation**: Daily background job at 02:00 UTC
```python
async def archive_old_data():
    """Tier data based on age"""
    # Aggregate 30-90 day data
    aggregate_to_daily_stats(
        date_range=(today - 90, today - 30)
    )

    # Delete individual records older than 30 days
    # (after confirming aggregates exist)
    delete_stale_recommendations(older_than_days=30)

    # Archive 90+ day aggregates to file
    export_to_json(
        "data/archives/monthly_stats_{year}_{month}.json",
        date_range=(today - 365, today - 90)
    )
```

---

## API Specification

### Enhanced Response Format

#### Base Response (Default)

**POST /api/recommendation**

Remains backward compatible; existing fields unchanged.

#### Extended Response with Stats

**POST /api/recommendation?include=stats**

Additional fields:
```json
{
  "recommendation": "buy",
  "confidence": 0.72,
  "current_price": 65432.50,

  "signals": { /* ... existing ... */ },
  "targets": { /* ... existing ... */ },
  "reasoning": "...",
  "timestamp": "2025-12-31T15:30:00Z",

  // NEW FIELDS when ?include=stats
  "meta": {
    "operating_mode": "normal",
    "weights_used": {
      "technical": 0.65,
      "sentiment": 0.35,
      "source": "adaptive",  // or 'static_fallback'
      "last_updated": "2025-12-31T00:00:00Z"
    },
    "data_quality": {
      "technical_available": true,
      "sentiment_available": true,
      "degraded_reason": null  // or "newsapi_timeout"
    },
    "cache_info": {
      "cached": true,
      "generated_at": "2025-12-31T15:27:00Z",
      "ttl_seconds": 178
    }
  },

  "performance_stats": {
    "recent_accuracy": {
      "24h": 0.72,
      "7d": 0.70,
      "30d": 0.69
    },
    "current_sharpe_ratio": 1.68,
    "recommendations_today": 15
  }
}
```

#### Verbosity Levels

Support multiple levels via query param:

| Parameter | Response Size | Use Case |
|-----------|--------------|----------|
| *(none)* | Minimal | Standard clients |
| `?include=stats` | Medium | Dashboards showing accuracy |
| `?include=stats,history` | Large | Analytics, debugging |
| `?include=full` | Maximum | Admin tools, data export |

---

## Background Services

### Service 1: Price Monitor

**Purpose**: Detect volatility and invalidate cache
**Frequency**: Every 30 seconds
**Implementation**:
```python
# src/services/price_monitor.py
class PriceMonitor:
    def __init__(self, volatility_threshold=0.03):
        self.threshold = volatility_threshold
        self.history = deque(maxlen=10)  # 5-min window
        self.retry_delay = 30
        self.max_retry_delay = 600

    async def run(self):
        while True:
            try:
                price = await fetch_btc_price()
                self.history.append({
                    'price': price,
                    'time': datetime.now()
                })

                if self._is_volatile():
                    await self._handle_volatility()

                # Reset backoff on success
                self.retry_delay = 30

            except Exception as e:
                await self._handle_error(e)

            await asyncio.sleep(self.retry_delay)

    def _is_volatile(self) -> bool:
        if len(self.history) < 2:
            return False

        old_price = self.history[0]['price']
        new_price = self.history[-1]['price']
        change = abs((new_price - old_price) / old_price)

        return change >= self.threshold

    async def _handle_volatility(self):
        logger.warning("Volatility spike detected, invalidating cache")
        cache.clear()

        if config.webhooks.enabled:
            await send_webhook('volatility_event', {
                'change_pct': self._get_change_pct(),
                'price': self.history[-1]['price']
            })

    async def _handle_error(self, error):
        logger.error(f"Price fetch failed: {error}")

        # Exponential backoff
        self.retry_delay = min(
            self.retry_delay * 2,
            self.max_retry_delay
        )

        # Use last known price if available
        if self.history:
            logger.info("Continuing with last known price")
```

### Service 2: Validation Job

**Purpose**: Validate pending recommendations at scheduled horizons
**Frequency**: Every 5 minutes
**Implementation**:
```python
# src/services/validator.py
class RecommendationValidator:
    async def run(self):
        while True:
            await asyncio.sleep(300)  # 5 minutes

            try:
                await self._validate_all_pending()
            except Exception as e:
                logger.error(f"Validation error: {e}")

    async def _validate_all_pending(self):
        current_price = await fetch_btc_price()
        now = datetime.now()

        # Get all recommendations awaiting validation
        pending = db.query(Recommendation).filter(
            Recommendation.validation_status != 'complete'
        ).all()

        for rec in pending:
            age_hours = (now - rec.timestamp).total_seconds() / 3600

            # Check each validation horizon
            await self._check_horizon(rec, '4h', age_hours, current_price)
            await self._check_horizon(rec, '24h', age_hours, current_price)
            await self._check_horizon(rec, '7d', age_hours, current_price)
            await self._check_event_based(rec, current_price)

    async def _check_event_based(self, rec, current_price):
        """Check if target or stop-loss hit"""
        if current_price >= rec.target_1:
            self._record_validation(
                rec, 'event_based', 'success',
                reason='target_reached',
                pnl=self._calculate_pnl(rec, current_price)
            )
        elif current_price <= rec.stop_loss:
            self._record_validation(
                rec, 'event_based', 'failure',
                reason='stop_loss_hit',
                pnl=self._calculate_pnl(rec, current_price)
            )

    def _calculate_pnl(self, rec, exit_price):
        """Simulate trade P&L using Kelly sizing"""
        edge = rec.confidence
        kelly_fraction = self._kelly_criterion(edge)

        # Apply constraints
        position_size = min(kelly_fraction, 0.25)  # Max 25%
        position_size = self._apply_dynamic_cap(position_size)

        price_change = (exit_price - rec.entry_price) / rec.entry_price

        # Directional PnL
        if rec.recommendation == 'buy':
            pnl = position_size * price_change
        elif rec.recommendation == 'sell':
            pnl = position_size * -price_change
        else:  # hold
            pnl = 0

        return pnl
```

### Service 3: Weight Optimizer

**Purpose**: Recalculate adaptive weights based on rolling 30-day window
**Frequency**: Daily at 00:00 UTC
**Implementation**:
```python
# src/services/weight_optimizer.py
class WeightOptimizer:
    async def run(self):
        while True:
            # Sleep until next midnight UTC
            await self._sleep_until_midnight()

            try:
                await self._recalculate_weights()
            except Exception as e:
                logger.error(f"Weight optimization failed: {e}")

    async def _recalculate_weights(self):
        # Get 30-day window of validated recommendations
        window_start = datetime.now() - timedelta(days=30)
        validated = db.query(ValidationResult).join(
            Recommendation
        ).filter(
            Recommendation.timestamp >= window_start,
            ValidationResult.validation_type == 'standard_24h',
            ValidationResult.outcome != 'pending'
        ).all()

        if len(validated) < 10:
            logger.info("Insufficient data for weight optimization")
            return

        # Calculate Sharpe ratios for each signal source
        sharpe_technical = self._calculate_sharpe(
            [v for v in validated if 'technical' in v.recommendation.signal_sources]
        )
        sharpe_sentiment = self._calculate_sharpe(
            [v for v in validated if 'sentiment' in v.recommendation.signal_sources]
        )

        # Normalize to weights
        total_sharpe = sharpe_technical + sharpe_sentiment
        new_weight_tech = sharpe_technical / total_sharpe
        new_weight_sent = sharpe_sentiment / total_sharpe

        # Apply Bayesian prior for cold start
        days_of_data = (datetime.now() - validated[0].recommendation.timestamp).days
        new_weight_tech, new_weight_sent = self._apply_bayesian_prior(
            new_weight_tech, new_weight_sent, days_of_data
        )

        # Smooth transition (70% old, 30% new)
        current = db.query(WeightHistory).order_by(
            WeightHistory.timestamp.desc()
        ).first()

        if current:
            final_weight_tech = 0.7 * current.weight_technical + 0.3 * new_weight_tech
            final_weight_sent = 0.7 * current.weight_sentiment + 0.3 * new_weight_sent
        else:
            final_weight_tech = new_weight_tech
            final_weight_sent = new_weight_sent

        # Save new weights
        db.add(WeightHistory(
            timestamp=datetime.now(),
            weight_technical=final_weight_tech,
            weight_sentiment=final_weight_sent,
            trigger_reason='daily_recalc',
            days_of_data=days_of_data,
            sharpe_technical=sharpe_technical,
            sharpe_sentiment=sharpe_sentiment
        ))
        db.commit()

        logger.info(f"Weights updated: tech={final_weight_tech:.2f}, sent={final_weight_sent:.2f}")

        # Check for mode changes
        await self._check_mode_change(sharpe_technical, sharpe_sentiment)

    def _calculate_sharpe(self, validations):
        """Calculate Sharpe ratio from validation results"""
        pnls = [v.pnl_pct for v in validations if v.pnl_pct is not None]

        if len(pnls) < 5:
            return 0.0

        mean_return = np.mean(pnls)
        std_return = np.std(pnls)

        if std_return == 0:
            return 0.0

        # Annualized risk-free rate: 4.5% / 365 days * holding period (1 day)
        risk_free_rate = (0.045 / 365)

        sharpe = (mean_return - risk_free_rate) / std_return
        return sharpe

    def _apply_bayesian_prior(self, weight_tech, weight_sent, days_of_data):
        """Apply Bayesian prior for cold start smoothing"""
        PRIOR_TECH = 0.6
        PRIOR_SENT = 0.4

        if days_of_data < 30:
            prior_weight = 0.7
        elif days_of_data < 90:
            prior_weight = 0.7 * (90 - days_of_data) / 60
        else:
            prior_weight = 0.0

        final_tech = prior_weight * PRIOR_TECH + (1 - prior_weight) * weight_tech
        final_sent = prior_weight * PRIOR_SENT + (1 - prior_weight) * weight_sent

        return final_tech, final_sent

    async def _check_mode_change(self, sharpe_tech, sharpe_sent):
        """Check if degraded mode should become preferred"""
        current_mode = get_current_operating_mode()

        if current_mode == 'degraded':
            # Check if degraded has been active for 7+ days
            mode_duration = get_mode_duration_days()
            if mode_duration < 7:
                return

            # Get normal mode Sharpe for comparison
            sharpe_combined = calculate_combined_sharpe()
            sharpe_degraded = max(sharpe_tech, sharpe_sent)  # Best single signal

            if sharpe_degraded > sharpe_combined:
                # Statistical significance test
                p_value = statistical_comparison(sharpe_degraded, sharpe_combined)

                if p_value < 0.05:  # Statistically significant
                    await self._transition_to_degraded_preferred()

    async def _transition_to_degraded_preferred(self):
        """Transition to degraded_preferred mode"""
        set_operating_mode('degraded_preferred')

        logger.warning("Operating mode changed to degraded_preferred")

        if config.webhooks.enabled:
            await send_webhook('mode_change', {
                'old_mode': 'degraded',
                'new_mode': 'degraded_preferred',
                'reason': 'single_signal_outperformed'
            })
```

### Service Lifecycle Management

**Startup**:
```python
# src/api/app.py
@app.on_event("startup")
async def startup_event():
    # Initialize database
    init_database()

    # Start background services
    asyncio.create_task(price_monitor.run())
    asyncio.create_task(validator.run())
    asyncio.create_task(weight_optimizer.run())

    logger.info("Background services started")

@app.on_event("shutdown")
async def shutdown_event():
    # Graceful shutdown
    logger.info("Shutting down background services")
    # Services will stop on next iteration
```

---

## Testing Strategy

### Unit Tests

**Scope**: Individual functions with mocked dependencies
**Tools**: pytest, pytest-asyncio, pytest-mock
**Coverage Target**: >80%

**Key Test Cases**:
```python
# tests/test_weights.py
def test_sharpe_calculation():
    """Test Sharpe ratio calculation with known returns"""
    pnls = [0.02, 0.01, -0.005, 0.03, 0.015]
    sharpe = calculate_sharpe(pnls, risk_free_rate=0.045/365)
    assert 0.5 < sharpe < 2.0  # Reasonable range

def test_bayesian_prior_cold_start():
    """Test Bayesian prior application during cold start"""
    weight_tech, weight_sent = apply_bayesian_prior(
        calculated_tech=0.8,
        calculated_sent=0.2,
        days_of_data=15
    )
    # Should be between calculated and prior (0.6/0.4)
    assert 0.6 < weight_tech < 0.8
    assert 0.2 < weight_sent < 0.4

def test_kelly_criterion_constraints():
    """Test Kelly criterion with position limits"""
    position = calculate_kelly_position(
        confidence=0.95,  # Very high confidence
        max_position=0.25
    )
    assert position <= 0.25  # Should respect cap

def test_volatility_detection():
    """Test volatility threshold triggering"""
    monitor = PriceMonitor(threshold=0.03)
    monitor.history = [
        {'price': 60000, 'time': datetime.now()},
        {'price': 61900, 'time': datetime.now()}  # 3.17% increase
    ]
    assert monitor._is_volatile() == True
```

### Integration Tests

**Scope**: Multi-component workflows with seeded database
**Tools**: pytest with SQLite test database

**Key Test Cases**:
```python
# tests/integration/test_adaptive_flow.py
@pytest.fixture
def seeded_db():
    """Create test DB with historical recommendations"""
    db = create_test_database()

    # Seed 30 days of recommendations
    for i in range(30):
        rec = create_test_recommendation(
            timestamp=datetime.now() - timedelta(days=30-i),
            recommendation='buy',
            confidence=0.7,
            technical_weight=0.6,
            sentiment_weight=0.4
        )
        db.add(rec)

        # Add validation results (simulate outcomes)
        val = ValidationResult(
            recommendation_id=rec.id,
            validation_type='standard_24h',
            outcome='success' if i % 2 == 0 else 'failure',
            pnl_pct=0.02 if i % 2 == 0 else -0.01
        )
        db.add(val)

    db.commit()
    return db

async def test_weight_recalculation(seeded_db):
    """Test end-to-end weight optimization"""
    optimizer = WeightOptimizer(db=seeded_db)

    initial_weights = get_current_weights(seeded_db)
    await optimizer._recalculate_weights()
    new_weights = get_current_weights(seeded_db)

    # Weights should have changed
    assert initial_weights != new_weights

    # Weights should sum to 1.0
    assert abs(sum(new_weights.values()) - 1.0) < 0.01

async def test_degraded_mode_transition(seeded_db):
    """Test automatic transition to degraded_preferred"""
    # Simulate degraded mode for 7 days
    set_operating_mode('degraded', seeded_db)

    # Seed better performance in degraded mode
    seed_better_degraded_performance(seeded_db)

    optimizer = WeightOptimizer(db=seeded_db)
    await optimizer._check_mode_change(sharpe_tech=1.8, sharpe_sent=0.9)

    # Should transition to degraded_preferred
    assert get_current_operating_mode(seeded_db) == 'degraded_preferred'

async def test_cache_invalidation_on_volatility(mock_coingecko):
    """Test cache clearing when volatility detected"""
    # Populate cache
    cache['recommendation:default'] = {'data': 'cached'}

    # Simulate price spike
    mock_coingecko.set_price_sequence([
        60000, 60100, 60200, 61900  # 3.17% jump
    ])

    monitor = PriceMonitor()
    await monitor.run_once()

    # Cache should be cleared
    assert 'recommendation:default' not in cache
```

### Property-Based Tests

**Tool**: hypothesis
**Purpose**: Find edge cases with generated inputs

```python
# tests/property/test_invariants.py
from hypothesis import given, strategies as st

@given(
    confidence=st.floats(min_value=0.0, max_value=1.0),
    technical_score=st.floats(min_value=-1.0, max_value=1.0),
    sentiment_score=st.floats(min_value=-1.0, max_value=1.0)
)
def test_recommendation_invariants(confidence, technical_score, sentiment_score):
    """Test that recommendations always satisfy invariants"""
    rec = generate_recommendation(
        technical_score=technical_score,
        sentiment_score=sentiment_score
    )

    # Confidence must be in valid range
    assert 0.0 <= rec.confidence <= 1.0

    # Weights must sum to 1.0
    assert abs(rec.weight_technical + rec.weight_sentiment - 1.0) < 0.001

    # Recommendation must be valid
    assert rec.recommendation in ['buy', 'sell', 'hold']

@given(
    pnls=st.lists(st.floats(min_value=-0.1, max_value=0.1), min_size=5, max_size=100)
)
def test_sharpe_ratio_properties(pnls):
    """Test Sharpe ratio calculation properties"""
    sharpe = calculate_sharpe(pnls)

    # Sharpe should be finite
    assert not math.isinf(sharpe)
    assert not math.isnan(sharpe)

    # Higher mean with same std should yield higher Sharpe
    higher_pnls = [p + 0.01 for p in pnls]
    higher_sharpe = calculate_sharpe(higher_pnls)
    assert higher_sharpe > sharpe
```

### Test Execution

**CI/CD Pipeline**:
```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov hypothesis

      - name: Run tests
        run: |
          pytest tests/ --cov=src --cov-report=xml --cov-report=term

      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

---

## Deployment & Operations

### Deployment Strategy

**Approach**: Big bang deployment
**Rationale**: MVP launch; single-instance architecture simplifies deployment
**Risks**: No gradual rollout; all users experience changes simultaneously
**Mitigation**: Thorough testing; feature flags for quick disabling if issues arise

### Deployment Steps

1. **Pre-deployment Validation**
   ```bash
   # Run full test suite
   pytest tests/ -v

   # Verify database migrations
   alembic upgrade head

   # Test with production-like config
   ./dev --config config.production.yaml
   ```

2. **Deployment**
   ```bash
   # Pull latest code
   git pull origin main

   # Install dependencies
   pip install -r requirements.txt

   # Initialize database (creates tables if not exist)
   python scripts/init_db.py

   # Restart service
   systemctl restart bitcoin-advisor
   ```

3. **Post-deployment Verification**
   ```bash
   # Health check
   curl http://localhost:8000/health

   # Test recommendation endpoint
   curl -X POST http://localhost:8000/api/recommendation \
     -H "Content-Type: application/json" \
     -d '{"days": 100, "news_days": 7, "max_articles": 50}'

   # Check background services running
   tail -f logs/advisor.log | grep "Background services started"
   ```

### Configuration Management

**config.yaml** - Enhanced with new settings:
```yaml
# Existing configuration...
api:
  host: "0.0.0.0"
  port: 8000
  reload: false

weights:
  # Initial weights (used as Bayesian prior)
  initial_technical: 0.6
  initial_sentiment: 0.4

  # Adaptive behavior
  adaptive_enabled: true
  cold_start_days: 30  # Days before fully data-driven
  rolling_window_days: 30  # Window for weight calculation
  smoothing_factor: 0.3  # Weight given to new calculation (vs current)

cache:
  enabled: true
  ttl_seconds: 300  # 5 minutes
  volatility_threshold: 0.03  # 3% price change triggers invalidation

validation:
  horizons:
    quick: 4  # hours
    standard: 24  # hours
    extended: 168  # hours (7 days)
  event_based: true

  position_sizing:
    method: "kelly_criterion"
    max_position_pct: 25
    min_confidence: 0.60
    dynamic_cap_enabled: true
    half_kelly: false  # Set true for Kelly/2 (more conservative)

backtesting:
  risk_free_rate: 0.045  # 4.5% annual (US Treasury)
  min_trades_for_sharpe: 10

operating_modes:
  auto_failover_enabled: true
  degraded_min_days: 7  # Days in degraded before considering failover
  significance_threshold: 0.05  # p-value for statistical tests

data_retention:
  full_detail_days: 30
  aggregated_days: 90
  archive_to_file: true
  archive_path: "data/archives/"

webhooks:
  enabled: false  # Set true to enable
  url: ""  # Your webhook endpoint
  events:
    - mode_change
    - volatility_event
    - dependency_failure
  timeout_seconds: 5

monitoring:
  health_check_enabled: true
  metrics_endpoint_enabled: true
  log_level: "INFO"  # DEBUG, INFO, WARNING, ERROR
  log_file: "logs/advisor.log"

background_services:
  price_monitor:
    enabled: true
    interval_seconds: 30
    retry_backoff_max_seconds: 600

  validator:
    enabled: true
    interval_seconds: 300  # 5 minutes

  weight_optimizer:
    enabled: true
    run_time_utc: "00:00"  # Daily at midnight UTC

  archiver:
    enabled: true
    run_time_utc: "02:00"  # Daily at 2 AM UTC
```

### Database Management

**Initialization**:
```python
# scripts/init_db.py
import sqlite3
from pathlib import Path

def init_database():
    db_path = Path("data/advisor.db")
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Read and execute schema
    with open("src/database/schema.sql") as f:
        cursor.executescript(f.read())

    # Initialize with default weights
    cursor.execute("""
        INSERT INTO weight_history (timestamp, weight_technical, weight_sentiment, trigger_reason)
        VALUES (datetime('now'), 0.6, 0.4, 'initial_setup')
    """)

    conn.commit()
    conn.close()

    print("Database initialized successfully")

if __name__ == "__main__":
    init_database()
```

**Backup Strategy**:
```bash
# Daily backup script (cron: 0 3 * * *)
#!/bin/bash

BACKUP_DIR="data/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup
sqlite3 data/advisor.db ".backup ${BACKUP_DIR}/advisor_${TIMESTAMP}.db"

# Compress
gzip ${BACKUP_DIR}/advisor_${TIMESTAMP}.db

# Keep only last 30 days
find ${BACKUP_DIR} -name "*.gz" -mtime +30 -delete

echo "Backup completed: advisor_${TIMESTAMP}.db.gz"
```

### Monitoring & Alerting

**Key Metrics to Monitor**:

1. **System Health**
   - API uptime
   - Response times (p50, p95, p99)
   - Error rates

2. **Adaptive System**
   - Current weights (technical vs sentiment)
   - Operating mode (normal/degraded/degraded_preferred)
   - Days since last weight update

3. **Accuracy Metrics**
   - 24h accuracy rate
   - 7d accuracy rate
   - Sharpe ratios (technical, sentiment, combined)

4. **Data Quality**
   - CoinGecko availability & latency
   - NewsAPI availability & latency
   - Cache hit rate
   - Recommendations served per day

5. **Database**
   - Database size
   - Query performance
   - Lock wait times

**Sample Prometheus Metrics**:
```python
# src/monitoring/metrics.py
from prometheus_client import Counter, Gauge, Histogram

# API metrics
recommendations_total = Counter(
    'recommendations_total',
    'Total recommendations served',
    ['recommendation_type', 'operating_mode']
)

recommendation_duration = Histogram(
    'recommendation_duration_seconds',
    'Time to generate recommendation',
    buckets=[1, 2, 5, 10, 20, 30]
)

# Adaptive system metrics
current_weights = Gauge(
    'current_weights',
    'Current signal weights',
    ['signal_type']
)

accuracy_rate = Gauge(
    'accuracy_rate',
    'Recommendation accuracy',
    ['horizon', 'mode']
)

sharpe_ratio = Gauge(
    'sharpe_ratio',
    'Current Sharpe ratio',
    ['signal_type']
)

# Dependency metrics
dependency_status = Gauge(
    'dependency_status',
    'Dependency health (1=healthy, 0=unhealthy)',
    ['dependency']
)

dependency_latency = Histogram(
    'dependency_latency_seconds',
    'Dependency response time',
    ['dependency'],
    buckets=[0.1, 0.5, 1, 2, 5]
)
```

**Grafana Dashboard** (JSON export):
- Panel 1: Current operating mode (stat)
- Panel 2: Adaptive weights over time (time series)
- Panel 3: Accuracy rates (time series with 24h/7d/30d)
- Panel 4: Sharpe ratios (gauge)
- Panel 5: Recommendations per hour (bar chart)
- Panel 6: Cache hit rate (stat)
- Panel 7: Dependency health (stat grid)
- Panel 8: API latency (heatmap)

### Error Handling

**Database Failures**:
```python
# src/database/resilient_db.py
class ResilientDatabase:
    def __init__(self, db_path):
        self.db_path = db_path
        self.fallback_weights = {'technical': 0.6, 'sentiment': 0.4}
        self.cached_weights = None

    def get_current_weights(self):
        try:
            conn = sqlite3.connect(self.db_path, timeout=5.0)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT weight_technical, weight_sentiment
                FROM weight_history
                ORDER BY timestamp DESC
                LIMIT 1
            """)
            row = cursor.fetchone()
            conn.close()

            if row:
                weights = {
                    'technical': row[0],
                    'sentiment': row[1]
                }
                # Cache for fallback
                self.cached_weights = weights
                return weights
            else:
                return self.fallback_weights

        except sqlite3.OperationalError as e:
            logger.error(f"Database locked or corrupted: {e}")

            # Degrade to stateless mode
            if self.cached_weights:
                logger.info("Using cached weights from memory")
                return self.cached_weights
            else:
                logger.warning("Using static fallback weights")
                return self.fallback_weights

        except Exception as e:
            logger.error(f"Unexpected database error: {e}")
            return self.fallback_weights
```

**Dependency Failures**:
```python
# src/services/resilient_fetcher.py
async def fetch_with_degradation(primary_func, fallback_value=None):
    """Wrapper for external API calls with graceful degradation"""
    try:
        result = await asyncio.wait_for(
            primary_func(),
            timeout=10.0
        )
        return result, 'success'

    except asyncio.TimeoutError:
        logger.warning(f"{primary_func.__name__} timed out")
        return fallback_value, 'timeout'

    except Exception as e:
        logger.error(f"{primary_func.__name__} failed: {e}")
        return fallback_value, 'error'

# Usage
sentiment_data, status = await fetch_with_degradation(
    fetch_news_sentiment,
    fallback_value=None
)

if status != 'success':
    # Operate in degraded mode (technical-only)
    set_operating_mode('degraded', reason=f'newsapi_{status}')
```

---

## Future Considerations

### Phase 2 Enhancements (Post-MVP)

1. **Multi-Instance Support**
   - Migrate to PostgreSQL or Redis-backed SQLite
   - Shared cache across instances
   - Load balancing support

2. **Volatility-Aware Features**
   - Automatic position size reduction during high volatility
   - Different weight profiles for different volatility regimes
   - Real-time WebSocket price feeds

3. **Advanced Backtesting**
   - Walk-forward optimization
   - Monte Carlo simulation for confidence intervals
   - Drawdown analysis and max risk metrics

4. **User Accounts**
   - Per-user weight preferences
   - Webhook registration via API
   - Historical recommendation access

5. **Additional Signal Sources**
   - On-chain metrics (active addresses, exchange flows)
   - Funding rates and perpetual data
   - Social sentiment (Twitter, Reddit)

6. **Machine Learning**
   - Train ML model to predict optimal weights
   - Feature engineering from technical indicators
   - Ensemble methods combining traditional + ML signals

### Known Limitations

1. **Single-Instance Architecture**
   - Cannot horizontally scale
   - Downtime during restarts
   - SQLite write concurrency limits

2. **Backtesting Simplifications**
   - Assumes instant execution (no slippage)
   - Fixed risk-free rate (varies in reality)
   - No transaction costs modeled

3. **Cold Start Period**
   - First 30 days uses mostly static weights
   - Limited data = high variance in Sharpe calculations
   - May not adapt quickly to regime changes

4. **Event-Based Validation**
   - Some recommendations never hit target or stop-loss
   - Marked as "expired" after 30 days
   - Skews accuracy if many expired

5. **Cache Race Conditions**
   - Volatility spike right after cache refresh = stale data
   - Accepted tradeoff for 5-min TTL

### Scaling Path

When single-instance limitations become critical:

**Phase 1: Vertical Scaling**
- Larger instance (more CPU/RAM)
- Optimize database queries (indexes, query plan)
- Redis cache for improved concurrency

**Phase 2: Horizontal Scaling (Stateless API)**
- PostgreSQL for shared state
- Redis for distributed cache
- Load balancer (nginx, HAProxy)
- Separate background job workers (Celery)

**Phase 3: Microservices (If Needed)**
- Recommendation Service (API)
- Backtesting Service (weight calculation)
- Data Collection Service (price, news)
- Validation Service (accuracy tracking)
- Message queue for coordination (RabbitMQ, Kafka)

---

## Appendix

### Glossary

- **Adaptive Weighting**: Automatically adjusting technical vs sentiment weights based on historical performance
- **Sharpe Ratio**: Risk-adjusted return metric; (mean return - risk-free rate) / standard deviation
- **Kelly Criterion**: Mathematical formula for optimal position sizing based on edge and odds
- **Operating Mode**: System state (normal, degraded, degraded_preferred) affecting signal usage
- **Bayesian Prior**: Initial belief about weights before data collection, updated as data arrives
- **Rolling Window**: Fixed time period (e.g., 30 days) that moves forward; only recent data used

### References

- **Kelly Criterion**: https://en.wikipedia.org/wiki/Kelly_criterion
- **Sharpe Ratio**: https://en.wikipedia.org/wiki/Sharpe_ratio
- **Backtesting**: https://www.quantstart.com/articles/Backtesting-Systematic-Trading-Strategies-in-Python-Considerations-and-Open-Source-Frameworks/
- **Bayesian Priors**: https://en.wikipedia.org/wiki/Prior_probability

### Change Log

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-31 | Initial specification after comprehensive design interview |

---

**End of Technical Specification**
