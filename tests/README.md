# Bitcoin Trading Advisor - Test Suite

Comprehensive test suite for the Bitcoin Trading Advisor application, providing thorough coverage of core business logic, technical analysis, sentiment analysis, and integration workflows.

## Overview

This test suite includes:

- **Unit Tests**: Tests for individual components in isolation
- **Integration Tests**: End-to-end workflow tests with mocked external dependencies
- **Edge Case Tests**: Boundary conditions and error handling
- **Fixtures**: Reusable test data and mock objects

## Test Structure

```
tests/
├── conftest.py                      # Shared fixtures and test configuration
├── test_recommendation_engine.py    # Core recommendation logic tests
├── test_technical_analyzer.py       # RSI, MACD, MA indicator tests
├── test_sentiment_analyzer.py       # VADER sentiment analysis tests
├── test_integration.py              # End-to-end workflow tests
└── README.md                        # This file
```

## Running Tests

### Quick Start

```bash
# Run all tests with coverage
./run_tests.sh

# Run without coverage report
./run_tests.sh --no-coverage

# Run only unit tests
./run_tests.sh --unit

# Run only integration tests
./run_tests.sh --integration

# Run tests in parallel (faster)
./run_tests.sh --parallel

# Verbose output
./run_tests.sh --verbose
```

### Manual pytest Commands

```bash
# Activate virtual environment first
source venv/bin/activate

# Run all tests
pytest

# Run specific test file
pytest tests/test_recommendation_engine.py

# Run specific test class
pytest tests/test_recommendation_engine.py::TestContrarian Alerts

# Run specific test
pytest tests/test_recommendation_engine.py::TestContrarian Alerts::test_extreme_euphoria_alert

# Run with coverage
pytest --cov=src --cov-report=html

# Run fast tests only (exclude slow tests)
pytest -m "not slow"

# Run in parallel
pytest -n auto
```

## Test Coverage Goals

| Component | Target Coverage | Current Status |
|-----------|----------------|----------------|
| Recommendation Engine | 85%+ | ✓ Comprehensive |
| Technical Analyzer | 80%+ | ✓ Comprehensive |
| Sentiment Analyzer | 80%+ | ✓ Comprehensive |
| Integration Flow | 70%+ | ✓ Comprehensive |
| Overall | 70%+ | Target achieved |

## Test Categories

### 1. Recommendation Engine Tests (`test_recommendation_engine.py`)

**What's Tested:**
- Weight initialization and validation
- Recommendation scoring (-1 to +1 scale)
- Contrarian alert system (extreme euphoria/fear detection)
- Weighted signal combination
- Target price calculation
- Divergence detection (price vs sentiment)
- Response structure validation

**Key Test Classes:**
- `TestRecommendationEngineInitialization` - Validates weight configuration
- `TestContrarian Alerts` - Tests extreme sentiment thresholds (>0.85, <0.15)
- `TestWeightedRecommendation` - Verifies signal combination logic
- `TestTargetCalculation` - Validates price target generation
- `TestEdgeCases` - Handles edge conditions (zero confidence, extreme prices)

**Example:**
```python
def test_extreme_euphoria_alert(self):
    """Test contrarian alert triggers at >0.85 sentiment"""
    # Creates Reddit sentiment with 0.90 compound score
    # Expects CONTRARIAN_ALERT recommendation
    assert result['alert_type'] == 'Extreme Euphoria'
```

### 2. Technical Analyzer Tests (`test_technical_analyzer.py`)

**What's Tested:**
- RSI calculation and signal classification (overbought/oversold)
- MACD calculation and crossover detection
- Simple Moving Averages (SMA)
- Exponential Moving Averages (EMA)
- Golden Cross / Death Cross detection
- Trend analysis (uptrend/downtrend/neutral)
- Overall recommendation logic

**Key Test Classes:**
- `TestRSICalculation` - Validates RSI values (0-100 range)
- `TestMACDCalculation` - Tests MACD = (12 EMA - 26 EMA)
- `TestMovingAverages` - Verifies SMA and EMA calculations
- `TestCrossoverDetection` - Tests 50/200 SMA crossovers
- `TestFullAnalysis` - Validates complete technical analysis output

**Example:**
```python
def test_golden_cross_detection(self):
    """Test Golden Cross (50 SMA crosses above 200 SMA)"""
    # Creates price pattern causing golden cross
    # Expects sma_50_vs_200 == 'above'
```

### 3. Sentiment Analyzer Tests (`test_sentiment_analyzer.py`)

**What's Tested:**
- VADER sentiment scoring (-1 to +1 compound)
- Article classification (positive/negative/neutral)
- Multi-article aggregation
- Confidence calculation
- Sentiment to recommendation mapping
- Crypto-specific language handling

**Key Test Classes:**
- `TestTextAnalysis` - Tests raw text sentiment scoring
- `TestArticleAnalysis` - Validates article processing
- `TestMultipleArticlesAnalysis` - Tests aggregation logic
- `TestVaderSpecificBehavior` - Tests VADER intensifiers (!!, CAPS, negation)

**Example:**
```python
def test_analyze_all_positive_articles(self):
    """Test analysis of all positive articles"""
    # Expects overall_sentiment == 'positive'
    # Expects recommendation == 'buy'
    # Expects average_compound > 0.05
```

### 4. Integration Tests (`test_integration.py`)

**What's Tested:**
- Complete recommendation flow (data → analysis → recommendation)
- Different weighting scenarios (technical-heavy, sentiment-heavy)
- Data quality handling (minimal data, missing fields)
- Response consistency and reproducibility
- Formatted output generation

**Key Test Classes:**
- `TestRecommendationFlow` - End-to-end bullish/bearish/mixed scenarios
- `TestWeightedScenarios` - Tests different weight configurations
- `TestDataQualityHandling` - Validates graceful degradation
- `TestResponseConsistency` - Ensures reproducible results

**Example:**
```python
def test_full_recommendation_flow_bullish(self):
    """Test complete flow with bullish signals"""
    # Technical analysis on bullish data
    # Sentiment analysis on positive articles
    # Generate recommendation
    # Expects 'buy' or 'strong_buy'
```

## Fixtures (`conftest.py`)

### Price Data Fixtures

- `sample_price_data` - 100 days of realistic BTC price data
- `long_price_data` - 300 days for testing long-term MAs
- `bullish_price_data` - Clear uptrend pattern
- `bearish_price_data` - Clear downtrend pattern

### Article Fixtures

- `sample_news_articles` - Mixed sentiment articles
- `positive_articles` - Strongly bullish articles
- `negative_articles` - Strongly bearish articles
- `neutral_articles` - Neutral market updates
- `sample_reddit_posts` - Reddit-specific posts

### Analysis Fixtures

- `mock_technical_analysis` - Pre-computed technical results
- `mock_sentiment_analysis` - Pre-computed sentiment results
- `current_price` - Standard test price (50,000)

## Writing New Tests

### Test Naming Convention

```python
class TestFeatureName:
    """Test description of feature"""

    def test_specific_behavior(self):
        """Test that specific behavior works correctly"""
        # Arrange
        input_data = create_test_data()

        # Act
        result = function_under_test(input_data)

        # Assert
        assert result['expected_field'] == expected_value
```

### Using Fixtures

```python
def test_with_fixtures(self, bullish_price_data, positive_articles, current_price):
    """Fixtures are automatically injected by pytest"""
    analyzer = TechnicalAnalyzer()
    results = analyzer.analyze(bullish_price_data)

    assert results['overall']['recommendation'] == 'buy'
```

### Testing Edge Cases

Always test:
- Empty inputs
- Minimal data (single data point)
- Extreme values (very high/low prices)
- Invalid data (negative values, NaN)
- Missing fields
- Zero confidence scenarios

## Coverage Report

After running tests with coverage:

```bash
# View HTML coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux

# View terminal summary
pytest --cov=src --cov-report=term-missing
```

The HTML report shows:
- Line-by-line coverage highlighting
- Branch coverage
- Missing lines
- Coverage percentage per file

## Continuous Integration

These tests are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run Tests
  run: |
    pip install -r requirements.testing.txt
    pytest --cov=src --cov-report=xml

- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    files: ./coverage.xml
```

## Common Issues & Solutions

### Issue: Import Errors

```bash
# Solution: Install package in editable mode
pip install -e .
```

### Issue: Fixture Not Found

```bash
# Solution: Ensure conftest.py is in tests/ directory
# Fixtures are automatically discovered from conftest.py
```

### Issue: Tests Pass Locally but Fail in CI

```bash
# Solution: Check Python version and dependencies match
python --version
pip list
```

### Issue: Coverage Below Threshold

```bash
# Solution: Run with coverage report to see missing lines
pytest --cov=src --cov-report=term-missing

# Add tests for uncovered lines
```

## Best Practices

1. **Test One Thing**: Each test should verify a single behavior
2. **Use Descriptive Names**: Test names should describe what is being tested
3. **Arrange-Act-Assert**: Structure tests clearly (AAA pattern)
4. **Mock External Dependencies**: Don't make real API calls in tests
5. **Test Edge Cases**: Include boundary conditions and error handling
6. **Keep Tests Fast**: Use fixtures to avoid repeated setup
7. **Maintain Independence**: Tests should not depend on execution order

## Performance

Typical test execution times:

- Full suite: ~10-15 seconds
- Unit tests only: ~5 seconds
- Integration tests: ~5-8 seconds
- With parallel execution (`-n auto`): ~3-5 seconds

## Contributing

When adding new features:

1. Write tests first (TDD approach)
2. Ensure tests pass locally
3. Maintain coverage above 70%
4. Add fixtures for reusable test data
5. Document complex test scenarios
6. Update this README if adding new test categories

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [VADER sentiment analysis](https://github.com/cjhutto/vaderSentiment)
- [pandas testing utilities](https://pandas.pydata.org/docs/reference/testing.html)
