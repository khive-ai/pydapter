"""
Tests for Async SQL adapter raw SQL functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import BaseModel

from pydapter.extras.async_sql_ import AsyncSQLAdapter


class TestModel(BaseModel):
    """Test model for raw SQL tests."""

    id: int
    name: str
    value: float


@pytest.mark.asyncio
async def test_raw_sql_without_table_parameter():
    """Test that raw SQL operations work without table parameter."""

    # Mock the engine and connection
    mock_result = MagicMock()
    mock_result.returns_rows = True
    mock_result.fetchall.return_value = [
        MagicMock(_mapping={"id": 1, "name": "test1", "value": 10.5}),
        MagicMock(_mapping={"id": 2, "name": "test2", "value": 20.5}),
    ]

    mock_conn = AsyncMock()
    mock_conn.execute.return_value = mock_result

    mock_engine = MagicMock()
    mock_begin_ctx = AsyncMock()
    mock_begin_ctx.__aenter__.return_value = mock_conn
    mock_begin_ctx.__aexit__.return_value = None
    mock_engine.begin.return_value = mock_begin_ctx

    # Test config WITHOUT table parameter
    config = {
        "engine": mock_engine,
        "operation": "raw_sql",
        "sql": "SELECT * FROM users WHERE active = :active ORDER BY created_at DESC LIMIT :limit",
        "params": {"active": True, "limit": 10},
    }

    # This should work without requiring a table parameter
    results = await AsyncSQLAdapter.from_obj(TestModel, config, many=True)

    # Verify results
    assert len(results) == 2
    assert results[0].id == 1
    assert results[0].name == "test1"
    assert results[1].id == 2
    assert results[1].name == "test2"

    # Verify the SQL was executed with params
    mock_conn.execute.assert_called_once()
    call_args = mock_conn.execute.call_args
    assert "active" in call_args[0][1]
    assert "limit" in call_args[0][1]


@pytest.mark.asyncio
async def test_raw_sql_with_dict_model():
    """Test raw SQL with dict instead of Pydantic model for flexible results."""

    # Mock the engine and connection
    mock_result = MagicMock()
    mock_result.returns_rows = True
    mock_result.fetchall.return_value = [
        MagicMock(
            _mapping={
                "id": 1,
                "name": "test1",
                "extra_field": "extra_value",
                "count": 100,
            }
        ),
    ]

    mock_conn = AsyncMock()
    mock_conn.execute.return_value = mock_result

    mock_engine = MagicMock()
    mock_begin_ctx = AsyncMock()
    mock_begin_ctx.__aenter__.return_value = mock_conn
    mock_begin_ctx.__aexit__.return_value = None
    mock_engine.begin.return_value = mock_begin_ctx

    # Test config for aggregation query without table parameter
    config = {
        "engine": mock_engine,
        "operation": "raw_sql",
        "sql": """
            SELECT 
                department,
                COUNT(*) as count,
                AVG(salary) as avg_salary
            FROM employees
            GROUP BY department
        """,
        "params": {},
    }

    # Use dict to get raw results without model validation
    results = await AsyncSQLAdapter.from_obj(dict, config, many=True)

    # Verify we get raw dict results
    assert len(results) == 1
    assert results[0]["id"] == 1
    assert results[0]["name"] == "test1"
    assert results[0]["extra_field"] == "extra_value"
    assert results[0]["count"] == 100


@pytest.mark.asyncio
async def test_raw_sql_ddl_operation():
    """Test raw SQL for DDL operations (CREATE, ALTER, etc.)."""

    # Mock the engine and connection for DDL
    mock_result = MagicMock()
    mock_result.returns_rows = False
    mock_result.rowcount = 0

    mock_conn = AsyncMock()
    mock_conn.execute.return_value = mock_result

    mock_engine = MagicMock()
    mock_begin_ctx = AsyncMock()
    mock_begin_ctx.__aenter__.return_value = mock_conn
    mock_begin_ctx.__aexit__.return_value = None
    mock_engine.begin.return_value = mock_begin_ctx

    # DDL operation config without table parameter
    config = {
        "engine": mock_engine,
        "operation": "raw_sql",
        "sql": "CREATE INDEX idx_users_email ON users(email)",
        "fetch_results": False,  # Don't try to fetch results for DDL
    }

    # Execute DDL operation
    result = await AsyncSQLAdapter.from_obj(dict, config)

    # Verify DDL result
    assert isinstance(result, dict)
    assert "affected_rows" in result
    assert result["affected_rows"] == 0


@pytest.mark.asyncio
async def test_raw_sql_with_order_by():
    """Test raw SQL with ORDER BY clause (common use case from feedback)."""

    # Mock the engine and connection
    mock_result = MagicMock()
    mock_result.returns_rows = True
    # Simulate ordered results
    mock_result.fetchall.return_value = [
        MagicMock(_mapping={"id": 3, "name": "newest", "created_at": "2024-01-03"}),
        MagicMock(_mapping={"id": 2, "name": "middle", "created_at": "2024-01-02"}),
        MagicMock(_mapping={"id": 1, "name": "oldest", "created_at": "2024-01-01"}),
    ]

    mock_conn = AsyncMock()
    mock_conn.execute.return_value = mock_result

    mock_engine = MagicMock()
    mock_begin_ctx = AsyncMock()
    mock_begin_ctx.__aenter__.return_value = mock_conn
    mock_begin_ctx.__aexit__.return_value = None
    mock_engine.begin.return_value = mock_begin_ctx

    # Config for ORDER BY query without table parameter
    config = {
        "engine": mock_engine,
        "operation": "raw_sql",
        "sql": "SELECT * FROM events ORDER BY created_at DESC LIMIT :limit",
        "params": {"limit": 3},
    }

    # Get ordered results as dicts
    results = await AsyncSQLAdapter.from_obj(dict, config, many=True)

    # Verify order is preserved
    assert len(results) == 3
    assert results[0]["id"] == 3
    assert results[0]["name"] == "newest"
    assert results[1]["id"] == 2
    assert results[1]["name"] == "middle"
    assert results[2]["id"] == 1
    assert results[2]["name"] == "oldest"


@pytest.mark.asyncio
async def test_raw_sql_no_results():
    """Test raw SQL that returns no results."""

    # Mock the engine and connection with empty results
    mock_result = MagicMock()
    mock_result.returns_rows = True
    mock_result.fetchall.return_value = []

    mock_conn = AsyncMock()
    mock_conn.execute.return_value = mock_result

    mock_engine = MagicMock()
    mock_begin_ctx = AsyncMock()
    mock_begin_ctx.__aenter__.return_value = mock_conn
    mock_begin_ctx.__aexit__.return_value = None
    mock_engine.begin.return_value = mock_begin_ctx

    config = {
        "engine": mock_engine,
        "operation": "raw_sql",
        "sql": "SELECT * FROM users WHERE id = :id",
        "params": {"id": 999999},
    }

    # Test with many=True - should return empty list
    results = await AsyncSQLAdapter.from_obj(dict, config, many=True)
    assert results == []

    # Test with many=False - should return None
    result = await AsyncSQLAdapter.from_obj(dict, config, many=False)
    assert result is None


@pytest.mark.asyncio
async def test_raw_sql_with_dsn():
    """Test raw SQL with DSN instead of engine."""

    with patch("pydapter.extras.async_sql_.create_async_engine") as mock_create_engine:
        # Mock the engine creation
        mock_result = MagicMock()
        mock_result.returns_rows = True
        mock_result.fetchall.return_value = [
            MagicMock(_mapping={"id": 1, "name": "test", "value": 10.5}),
        ]

        mock_conn = AsyncMock()
        mock_conn.execute.return_value = mock_result

        mock_engine = MagicMock()
        mock_begin_ctx = AsyncMock()
        mock_begin_ctx.__aenter__.return_value = mock_conn
        mock_begin_ctx.__aexit__.return_value = None
        mock_engine.begin.return_value = mock_begin_ctx
        mock_engine.dispose = AsyncMock()

        mock_create_engine.return_value = mock_engine

        # Config with DSN, no table parameter
        config = {
            "dsn": "postgresql+asyncpg://user:pass@localhost/db",
            "operation": "raw_sql",
            "sql": "SELECT * FROM users WHERE id = :id",
            "params": {"id": 1},
        }

        result = await AsyncSQLAdapter.from_obj(TestModel, config, many=False)

        # Verify result
        assert result.id == 1
        assert result.name == "test"
        assert result.value == 10.5

        # Verify engine was created with DSN
        mock_create_engine.assert_called_once_with(
            "postgresql+asyncpg://user:pass@localhost/db", future=True
        )

        # Note: Engine disposal is managed by SQLAlchemy's connection pool
        # and is NOT called explicitly in from_obj
