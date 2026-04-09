# Development task runner for kubeagent

default: help

# Install in editable mode with dev dependencies
install:
    pip install -e ".[dev]"

# Format code
fmt:
    ruff format src/ tests/

# Lint code
lint:
    ruff check src/ tests/

# Fix auto-fixable lint issues
fix:
    ruff check --fix src/ tests/

# Run tests
test:
    pytest -v

# Run all checks
check: fmt lint test
    @echo "All checks passed!"

# Install pre-commit hooks
precommit-install:
    pre-commit install

# Clean build artifacts
clean:
    rm -rf build/ dist/ *.egg-info/
    rm -rf .pytest_cache/ .coverage htmlcov/
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete

# Show available recipes
help:
    @just --list
