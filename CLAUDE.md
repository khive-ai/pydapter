# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Pydapter is a Python library that provides a unified interface for data adapters, enabling seamless data flow between Pydantic models and various storage systems (databases, files, vector stores, etc.). The core philosophy is "storage as a deployment decision, not an architecture decision."

## Architecture

### Core Components

- **`src/pydapter/core.py`**: Defines the `Adapter` protocol - the fundamental interface all adapters implement
  - `from_obj()`: Convert from external format to Pydantic models
  - `to_obj()`: Convert from Pydantic models to external format

- **`src/pydapter/async_core.py`**: Async version of the adapter protocol for high-performance async operations

- **Adapter Categories**:
  - **File Adapters** (`adapters/`): JSON, CSV, TOML, Excel
  - **Database Adapters** (`extras/`): PostgreSQL, MongoDB, Neo4j, SQLite
  - **Vector Store Adapters** (`extras/`): Qdrant, Weaviate
  - **Specialized Adapters** (`extras/`): Memvid, Pulsar, SQL with SQLAlchemy

- **Model Adapters** (`model_adapters/`): Higher-level adapters that work with SQLAlchemy models and provide ORM-like functionality

- **Migrations** (`migrations/`): Database migration support using Alembic

### Key Design Patterns

1. **Protocol-Based Design**: All adapters implement the same protocol, ensuring consistency
2. **Sync/Async Duality**: Most adapters have both sync and async versions (e.g., `PostgresAdapter` and `AsyncPostgresAdapter`)
3. **Framework Agnostic**: Works with any model framework (Pydantic, dataclasses, custom classes)
4. **Stateless Adapters**: Adapters are class-based utilities without instance state

## Development Commands

### Setup

```bash
# Install development dependencies using uv (recommended)
uv pip install -e ".[dev,all]"

# Sync dependencies
uv sync

# Install pre-commit hooks
pre-commit install
```

### Testing

```bash
# Run all tests with coverage
uv run pytest -xvs --cov=pydapter --cov-report=term-missing

# Run unit tests only (exclude integration tests)
uv run pytest -xvs -k "not integration"

# Run integration tests only
uv run pytest -xvs -k "integration"

# Run a specific test file
uv run pytest tests/test_adapters/test_core_adapters.py -xvs

# Run a single test
uv run pytest tests/test_adapters/test_core_adapters.py::test_text_roundtrip -xvs

# Run tests in parallel (requires pytest-xdist)
uv run pytest -n 4

# Run the full CI suite locally
python scripts/ci.py

# Skip integration tests (useful when Docker isn't available)
python scripts/ci.py --skip-integration

# Run only specific CI components
python scripts/ci.py --only lint
python scripts/ci.py --only unit
```

### Code Quality

```bash
# Run linting
uv run ruff check src tests

# Fix linting issues automatically
uv run ruff check src tests --fix

# Format code
uv run ruff format src tests

# Check formatting without modifying
uv run ruff format src tests --check

# Run type checking (if configured)
uv run mypy src
```

### Documentation

```bash
# Build documentation locally
uv run mkdocs serve

# Deploy documentation (typically done by CI)
uv run mkdocs gh-deploy
```

## Testing Strategy

### Test Organization

- **`tests/test_adapters/`**: Core adapter functionality tests
  - Unit tests for each adapter type
  - Extended tests for complex adapters
  - Property-based testing with Hypothesis

- **`tests/test_adapters/test_integration_*.py`**: Integration tests requiring external services
  - Use testcontainers for database testing
  - Require Docker to be running

- **`tests/test_model_adapters/`**: Tests for SQLAlchemy model adapters

- **`tests/test_error_handling/`**: Error handling and edge cases

- **`tests/test_migrations/`**: Database migration tests

### Test Fixtures

Tests use pytest fixtures defined in `tests/conftest.py`. Common fixtures include sample Pydantic models and database connections.

## Adding New Adapters

When creating a new adapter:

1. Implement the `Adapter` protocol from `core.py`
2. Place file adapters in `src/pydapter/adapters/`
3. Place database/external service adapters in `src/pydapter/extras/`
4. Create both sync and async versions if applicable
5. Add comprehensive tests in `tests/test_adapters/`
6. Update optional dependencies in `pyproject.toml` if needed
7. Add example notebook in `notebooks/` demonstrating usage

## CI/CD Pipeline

The project uses GitHub Actions for CI/CD:

- **`ci.yml`**: Runs on every push/PR - linting, formatting, tests, coverage
- **`release.yml`**: Handles PyPI releases on version tags
- **`docs-deploy.yml`**: Deploys documentation to GitHub Pages
- **`codeql.yml`**: Security analysis

Local CI script (`scripts/ci.py`) replicates the CI environment locally.

## Common Tasks

### Working with Optional Dependencies

```bash
# Install specific extras
uv pip install -e ".[postgres,mongo,qdrant]"

# Install all extras for comprehensive testing
uv pip install -e ".[all]"
```

### Running Database-Specific Tests

Many integration tests require Docker. Start required services:

```bash
# PostgreSQL
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres

# MongoDB
docker run -d -p 27017:27017 mongo

# Neo4j
docker run -d -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j

# Qdrant
docker run -d -p 6333:6333 qdrant/qdrant
```

Or use the docker-compose files in the notebooks directories.

## Project Conventions

- Use `uv` for all package management (not pip directly)
- Follow conventional commits for commit messages
- All new code must have tests with >90% coverage
- Async functions/classes prefix with `Async` (e.g., `AsyncPostgresAdapter`)
- Type hints are required for all public APIs
- Examples should be provided as Jupyter notebooks in `notebooks/`