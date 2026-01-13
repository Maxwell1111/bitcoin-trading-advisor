# Quick Reference Card - Bitcoin Trading Advisor

## Running the Application

### Basic Usage
```bash
# Run with mock data (no API keys needed)
python main.py --mock

# Run with real data (requires API keys in .env)
python main.py

# Run with custom parameters
python main.py --days 90 --articles 100 --news-days 14
```

### Logging Options
```bash
# Verbose logging (shows file/line numbers)
python main.py --mock --verbose

# Save logs to file
python main.py --mock --log-file logs/advisor.log

# Debug level logging
python main.py --mock --log-level DEBUG

# Combined
python main.py --mock -v --log-file logs/debug.log --log-level DEBUG
```

## Code Quality Tools

### Ruff (Linting & Formatting)
```bash
# Check for issues
ruff check .

# Auto-fix issues
ruff check --fix .

# Format code
ruff format .

# Check specific file
ruff check src/engine/recommendation.py
```

### Running Tests
```bash
# All tests
pytest

# With coverage report
pytest --cov=src --cov-report=html

# Specific test file
pytest tests/test_recommendation_engine.py

# Specific test
pytest tests/test_recommendation_engine.py::TestRecommendationEngineInitialization

# Fast tests only
pytest -m "not slow"

# Parallel execution
pytest -n auto

# Using the test runner script
./run_tests.sh                 # All tests with coverage
./run_tests.sh --unit          # Unit tests only
./run_tests.sh --fast          # Skip slow tests
./run_tests.sh --parallel      # Run in parallel
```

### Type Checking
```bash
# Check all files
mypy src/

# Check specific file
mypy src/engine/recommendation.py
```

### Pre-commit Hooks
```bash
# Run all pre-commit checks manually
pre-commit run --all-files

# Update hook versions
pre-commit autoupdate

# Skip hooks for one commit (not recommended)
git commit --no-verify
```

## Git Workflow

```bash
# 1. Make changes to code
# 2. Check code quality
ruff check --fix .

# 3. Run tests
pytest

# 4. Stage and commit (hooks run automatically)
git add .
git commit -m "Your commit message"

# 5. Push to remote
git push
```

## Common Tasks

### Fix Import Order
```bash
ruff check --select I --fix .
```

### Fix All Auto-fixable Issues
```bash
ruff check --fix .
```

### Format All Code
```bash
ruff format .
```

### Run Security Scan
```bash
bandit -r src/
```

### View Test Coverage
```bash
pytest --cov=src --cov-report=html
open htmlcov/index.html  # macOS
```

### Clean Up Generated Files
```bash
# Remove test cache and coverage files
rm -rf .pytest_cache htmlcov .coverage

# Remove Python cache
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

## Debugging

### Enable Debug Logging
```bash
python main.py --mock --log-level DEBUG -v
```

### Run Single Test with Output
```bash
pytest -s tests/test_recommendation_engine.py::test_specific_test
```

### Use Python Debugger
```python
# Add to code where you want to debug
import pdb; pdb.set_trace()

# Or use breakpoint() (Python 3.7+)
breakpoint()
```

## Project Structure

```
bitcoin-trading-advisor/
├── main.py                 # Main entry point
├── src/
│   ├── analysis/          # Technical & sentiment analysis
│   ├── data/              # Data fetchers
│   ├── engine/            # Recommendation engine
│   ├── api/               # FastAPI web server
│   ├── database/          # SQLite models
│   ├── services/          # Background services
│   └── utils/             # Utilities & config
├── tests/                 # Test suite
├── static/                # Web dashboard
├── requirements.txt       # Dependencies
├── pyproject.toml        # Tool configurations
├── pytest.ini            # Pytest config
└── .pre-commit-config.yaml  # Pre-commit hooks
```

## Environment Setup

### Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows
```

### Install Dependencies
```bash
# Production dependencies
pip install -r requirements.txt

# Testing dependencies
pip install -r requirements.testing.txt

# Development dependencies
pip install -e ".[dev,test]"
```

### Set Up API Keys
```bash
cp .env.example .env
# Edit .env and add your API keys
```

## Troubleshooting

### Tests Failing
```bash
# Update dependencies
pip install -r requirements.testing.txt --upgrade

# Clear cache and rerun
pytest --cache-clear
```

### Pre-commit Issues
```bash
# Update hooks
pre-commit autoupdate

# Clean and reinstall
pre-commit clean
pre-commit install
```

### Import Errors
```bash
# Ensure you're in the project root
cd /Users/aardeshiri/bitcoin-trading-advisor

# Reinstall in editable mode
pip install -e .
```

## Performance Tips

- Use `--mock` flag for fast testing without API calls
- Run tests in parallel: `pytest -n auto`
- Use `ruff` instead of `flake8` + `isort` + `pylint` (much faster)
- Enable test cache: pytest automatically caches results

## Getting Help

```bash
# Main script help
python main.py --help

# Pytest help
pytest --help

# Ruff help
ruff --help

# Pre-commit help
pre-commit --help
```

---

**Pro Tip:** Set up your IDE to run `ruff check --fix` on file save for automatic code cleanup!
