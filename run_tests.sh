#!/bin/bash
# Test runner script for Bitcoin Trading Advisor

set -e  # Exit on error

echo "=================================================="
echo "  Bitcoin Trading Advisor - Test Suite Runner"
echo "=================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Warning: Virtual environment not found. Creating one...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    echo -e "${GREEN}Virtual environment created.${NC}"
else
    source venv/bin/activate
fi

# Install/upgrade test dependencies
echo "Installing test dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.testing.txt
pip install -q -e .
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Parse command line arguments
COVERAGE=true
MARKERS=""
VERBOSE=""
PARALLEL=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-coverage)
            COVERAGE=false
            shift
            ;;
        --unit)
            MARKERS="-m unit"
            shift
            ;;
        --integration)
            MARKERS="-m integration"
            shift
            ;;
        --fast)
            MARKERS="-m 'not slow'"
            shift
            ;;
        --verbose)
            VERBOSE="-vv"
            shift
            ;;
        --parallel)
            PARALLEL="-n auto"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: ./run_tests.sh [--no-coverage] [--unit] [--integration] [--fast] [--verbose] [--parallel]"
            exit 1
            ;;
    esac
done

# Build pytest command
PYTEST_CMD="pytest"

if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=src --cov-report=html --cov-report=term-missing"
fi

if [ -n "$MARKERS" ]; then
    PYTEST_CMD="$PYTEST_CMD $MARKERS"
fi

if [ -n "$VERBOSE" ]; then
    PYTEST_CMD="$PYTEST_CMD $VERBOSE"
fi

if [ -n "$PARALLEL" ]; then
    PYTEST_CMD="$PYTEST_CMD $PARALLEL"
fi

# Run tests
echo "Running tests..."
echo "Command: $PYTEST_CMD"
echo ""

if $PYTEST_CMD; then
    echo ""
    echo -e "${GREEN}=================================================="
    echo -e "  ✓ All tests passed!"
    echo -e "==================================================${NC}"

    if [ "$COVERAGE" = true ]; then
        echo ""
        echo -e "${GREEN}Coverage report generated at: htmlcov/index.html${NC}"
        echo -e "Open it with: open htmlcov/index.html (macOS) or xdg-open htmlcov/index.html (Linux)"
    fi

    exit 0
else
    echo ""
    echo -e "${RED}=================================================="
    echo -e "  ✗ Tests failed"
    echo -e "==================================================${NC}"
    exit 1
fi
