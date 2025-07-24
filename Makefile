.PHONY: help install install-dev install-all dev test coverage lint format typecheck clean \
        build-python build-ts build-frontend build-docs \
        dev-api dev-frontend dev-docs \
        test-python test-ts test-integration \
        all

# Default target
help:
	@echo "CinchDB Monorepo Commands:"
	@echo ""
	@echo "Installation:"
	@echo "  make install          - Install Python dependencies only"
	@echo "  make install-dev      - Install CinchDB CLI in editable mode"
	@echo "  make install-all      - Install everything (dependencies + CLI + TypeScript + Frontend + Docs)"
	@echo ""
	@echo "Development:"
	@echo "  make dev              - Run development mode (API + Frontend)"
	@echo "  make dev-api          - Run API server in development mode"
	@echo "  make dev-frontend     - Run frontend in development mode"
	@echo "  make dev-docs         - Run documentation site in development mode"
	@echo ""
	@echo "Testing:"
	@echo "  make test             - Run all tests"
	@echo "  make test-python      - Run Python tests only"
	@echo "  make test-ts          - Run TypeScript SDK tests"
	@echo "  make test-integration - Run integration tests"
	@echo "  make coverage         - Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint             - Run linters on all code"
	@echo "  make format           - Format all code"
	@echo "  make typecheck        - Run type checking"
	@echo ""
	@echo "Building:"
	@echo "  make build-python     - Build Python package"
	@echo "  make build-ts         - Build TypeScript SDK"
	@echo "  make build-frontend   - Build frontend application"
	@echo "  make build-docs       - Build documentation site"
	@echo "  make build-all        - Build everything"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean            - Clean all build artifacts and caches"

# Installation targets
install:
	uv sync

install-dev:
	uv pip install -e .

install-all: install install-dev
	cd sdk/typescript && npm install
	cd frontend && npm install
	cd docs && npm install

# Development targets
dev: dev-api dev-frontend
	@echo "Starting CinchDB development environment..."

dev-api:
	uv run cinch-server

dev-frontend:
	cd frontend && npm run dev

dev-docs:
	cd docs && npm run dev

# Python-specific targets
test-python:
	uv run pytest tests/

coverage:
	uv run pytest --cov=cinchdb --cov-report=html --cov-report=term tests/

lint-python:
	uv run ruff check src/ tests/

format-python:
	uv run ruff format src/ tests/

typecheck-python:
	uv run mypy src/

build-python:
	uv build

# TypeScript SDK targets
test-ts:
	cd sdk/typescript && npm test

lint-ts:
	cd sdk/typescript && npm run lint

build-ts:
	cd sdk/typescript && npm run build

# Frontend targets
lint-frontend:
	cd frontend && npm run lint

build-frontend:
	cd frontend && npm run build

# Documentation targets
build-docs:
	cd docs && npm run build

# Integration tests
test-integration:
	uv run pytest tests/integration/ -v

# Combined targets
test: test-python test-ts

lint: lint-python lint-ts lint-frontend

format: format-python

typecheck: typecheck-python

build-all: build-python build-ts build-frontend build-docs

# Clean target
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name ".next" -exec rm -rf {} +
	find . -type d -name "dist" -exec rm -rf {} +
	find . -type d -name "build" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete
	rm -rf htmlcov/
	rm -rf sdk/typescript/dist/
	rm -rf frontend/.next/
	rm -rf frontend/out/
	rm -rf docs/.next/
	rm -rf docs/out/

# Main targets
all: lint typecheck test