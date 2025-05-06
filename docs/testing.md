# Testing in pydapter

pydapter uses a comprehensive testing strategy to ensure reliability and
correctness of all adapters. This document explains the testing approach and how
to run tests.

## Testing Strategy

pydapter employs two main types of tests:

1. **Unit Tests** - Test adapter functionality in isolation using mocks
2. **Integration Tests** - Test adapters with real database systems using
   TestContainers

## Unit Tests

Unit tests are designed to test adapter functionality without requiring external
dependencies. These tests use mocks to simulate database connections and
responses, making them fast and reliable.

Example unit test for a database adapter:

```python
def test_postgres_adapter_to_obj(mocker):
    # Mock SQLAlchemy engine and connection
    mock_engine = mocker.patch("sqlalchemy.create_engine")
    mock_conn = mock_engine.return_value.begin.return_value.__enter__.return_value

    # Create test model
    test_model = TestModel(id=1, name="test", value=42.0)

    # Test adapter
    PostgresAdapter.to_obj(test_model, engine_url="postgresql://test", table="test_table")

    # Verify SQL execution was called with correct parameters
    mock_conn.execute.assert_called_once()
```

## Integration Tests

Integration tests verify that adapters work correctly with actual database
systems. These tests use [TestContainers](https://testcontainers.com/) to spin
up isolated database instances in Docker containers during test execution.

### Supported Databases

pydapter includes integration tests for:

- **PostgreSQL** - SQL database adapter tests
- **MongoDB** - Document database adapter tests
- **Neo4j** - Graph database adapter tests
- **Qdrant** - Vector database adapter tests

### TestContainers Setup

Integration tests use pytest fixtures to create and manage database containers:

```python
@pytest.fixture(scope="session")
def pg_url():
    """PostgreSQL container fixture for tests."""
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16-alpine") as pg:
        url = pg.get_connection_url()
        yield url
```

These fixtures handle container lifecycle, ensuring proper cleanup after tests
complete.

### Example Integration Test

```python
def test_postgres_single_record(pg_url, sync_model_factory, postgres_table):
    """Test PostgreSQL adapter with a single record."""
    # Create test instance
    test_model = sync_model_factory(id=42, name="test_postgres", value=12.34)

    # Register adapter
    test_model.__class__.register_adapter(PostgresAdapter)

    # Store in database
    test_model.adapt_to(obj_key="postgres", engine_url=pg_url, table="test_table")

    # Retrieve from database
    retrieved = test_model.__class__.adapt_from(
        {"engine_url": pg_url, "table": "test_table", "selectors": {"id": 42}},
        obj_key="postgres",
        many=False,
    )

    # Verify data integrity
    assert retrieved.id == test_model.id
    assert retrieved.name == test_model.name
    assert retrieved.value == test_model.value
```

## Running Tests

### Prerequisites

- Python 3.8+
- Docker (for integration tests)

### Installation

```bash
# Clone the repository
git clone https://github.com/ohdearquant/pydapter.git
cd pydapter

# Install development dependencies
pip install -e ".[dev]"
```

### Running All Tests

```bash
pytest
```

### Running Specific Tests

```bash
# Run only unit tests
pytest tests/test_*.py -k "not test_integration"

# Run only integration tests
pytest tests/test_integration_*.py

# Run tests for a specific adapter
pytest tests/test_*postgres*.py
```

### Docker Availability Check

Integration tests automatically check for Docker availability and are skipped if
Docker is not running:

```python
def is_docker_available():
    """Check if Docker is available."""
    import subprocess
    try:
        subprocess.run(["docker", "info"], check=True, capture_output=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

# Skip tests if Docker is not available
pytestmark = pytest.mark.skipif(
    not is_docker_available(), reason="Docker is not available"
)
```

## Writing New Tests

When contributing new adapters or features to pydapter, please include both unit
tests and integration tests:

1. **Unit tests** should test the adapter's functionality in isolation using
   mocks
2. **Integration tests** should verify the adapter works with a real database
   instance

### Integration Test Template

```python
def test_new_adapter_integration(container_url, model_factory, cleanup_fixture):
    """Test new adapter with a real database."""
    # Create test instance
    test_model = model_factory(id=1, name="test", value=42.0)

    # Register adapter
    test_model.__class__.register_adapter(NewAdapter)

    # Store in database
    test_model.adapt_to(obj_key="new_adapter", url=container_url, ...)

    # Retrieve from database
    retrieved = test_model.__class__.adapt_from(
        {"url": container_url, ...},
        obj_key="new_adapter",
        many=False,
    )

    # Verify data integrity
    assert retrieved.id == test_model.id
    assert retrieved.name == test_model.name
    assert retrieved.value == test_model.value
```

## Test Coverage

pydapter aims to maintain high test coverage. You can generate a coverage report
with:

```bash
pytest --cov=pydapter
```

For a detailed HTML report:

```bash
pytest --cov=pydapter --cov-report=html
```

This will create a `htmlcov` directory with the coverage report.
