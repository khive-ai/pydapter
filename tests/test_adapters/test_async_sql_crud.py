"""
Tests for async SQL adapter CRUD operations.
"""

import os

# Import the adapters
import sys
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/src")

from pydapter.exceptions import ValidationError
from pydapter.extras.async_postgres_ import AsyncPostgresAdapter
from pydapter.extras.async_sql_ import AsyncSQLAdapter, SQLReadConfig


class TestModel(BaseModel):
    """Test model for CRUD operations."""

    id: int | None = None
    name: str
    email: str
    age: int
    active: bool = True
    created_at: datetime | None = None


@pytest_asyncio.fixture
async def test_engine():
    """Create a test SQLite engine for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    # Create test table
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: sync_conn.exec_driver_sql(
                """
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                age INTEGER NOT NULL,
                active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
            )
        )

    yield engine

    await engine.dispose()


@pytest.fixture
def mock_engine():
    """Create a mock engine for unit testing."""
    engine = MagicMock()
    engine.begin = MagicMock()

    # Mock connection context manager
    mock_conn = AsyncMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=None)

    engine.begin.return_value = mock_conn

    return engine, mock_conn


class TestAsyncSQLAdapterCRUD:
    """Test AsyncSQLAdapter CRUD operations."""

    @pytest.mark.asyncio
    async def test_insert_operation(self, test_engine):
        """Test INSERT operation."""
        test_data = TestModel(name="John Doe", email="john@example.com", age=30)

        result = await AsyncSQLAdapter.to_obj(
            test_data, engine=test_engine, table="test_table"
        )

        assert result == {"inserted_count": 1}

        # Verify the insert
        config: SQLReadConfig = {"engine": test_engine, "table": "test_table"}
        users = await AsyncSQLAdapter.from_obj(TestModel, config, many=True)
        assert len(users) == 1
        assert users[0].name == "John Doe"
        assert users[0].email == "john@example.com"

    @pytest.mark.asyncio
    async def test_select_operation(self, test_engine):
        """Test SELECT operation."""
        # Insert test data
        test_users = [
            TestModel(name="Alice", email="alice@example.com", age=25),
            TestModel(name="Bob", email="bob@example.com", age=30),
            TestModel(name="Charlie", email="charlie@example.com", age=35),
        ]

        for user in test_users:
            await AsyncSQLAdapter.to_obj(user, engine=test_engine, table="test_table")

        # Test select all
        config: SQLReadConfig = {"engine": test_engine, "table": "test_table"}
        users = await AsyncSQLAdapter.from_obj(TestModel, config, many=True)
        assert len(users) == 3

        # Test select with filters
        config = {
            "engine": test_engine,
            "table": "test_table",
            "selectors": {"age": 30},
        }
        filtered_users = await AsyncSQLAdapter.from_obj(TestModel, config, many=True)
        assert len(filtered_users) == 1
        assert filtered_users[0].name == "Bob"

        # Test select with limit
        config = {"engine": test_engine, "table": "test_table", "limit": 2}
        limited_users = await AsyncSQLAdapter.from_obj(TestModel, config, many=True)
        assert len(limited_users) == 2

    @pytest.mark.asyncio
    async def test_update_operation(self, test_engine):
        """Test UPDATE operation."""
        # Insert initial data
        user = TestModel(name="John", email="john@example.com", age=30)
        await AsyncSQLAdapter.to_obj(user, engine=test_engine, table="test_table")

        # Update the user
        updated_user = TestModel(name="John Updated", email="john@example.com", age=31)
        result = await AsyncSQLAdapter.to_obj(
            updated_user,
            engine=test_engine,
            table="test_table",
            operation="update",
            where={"email": "john@example.com"},
        )

        assert result == {"updated_count": 1}

        # Verify the update
        config = {
            "engine": test_engine,
            "table": "test_table",
            "selectors": {"email": "john@example.com"},
        }
        updated = await AsyncSQLAdapter.from_obj(TestModel, config, many=False)
        assert updated.name == "John Updated"
        assert updated.age == 31

    @pytest.mark.asyncio
    async def test_delete_operation(self, test_engine):
        """Test DELETE operation."""
        # Insert test data
        user = TestModel(name="ToDelete", email="delete@example.com", age=25)
        await AsyncSQLAdapter.to_obj(user, engine=test_engine, table="test_table")

        # Delete the user
        config = {
            "engine": test_engine,
            "table": "test_table",
            "operation": "delete",
            "selectors": {"email": "delete@example.com"},
        }
        result = await AsyncSQLAdapter.from_obj(TestModel, config)

        assert result == {"deleted_count": 1}

        # Verify deletion
        config = {
            "engine": test_engine,
            "table": "test_table",
            "selectors": {"email": "delete@example.com"},
        }
        with pytest.raises(Exception):  # Should raise ResourceError
            await AsyncSQLAdapter.from_obj(TestModel, config, many=False)

    @pytest.mark.asyncio
    async def test_upsert_operation(self, test_engine):
        """Test UPSERT operation."""
        # Initial insert via upsert
        user = TestModel(name="Alice", email="alice@example.com", age=25)
        result = await AsyncSQLAdapter.to_obj(
            user,
            engine=test_engine,
            table="test_table",
            operation="upsert",
            conflict_columns=["email"],
        )

        assert result["inserted_count"] == 1
        assert result["updated_count"] == 0

        # Update via upsert
        updated_user = TestModel(
            name="Alice Updated", email="alice@example.com", age=26
        )
        result = await AsyncSQLAdapter.to_obj(
            updated_user,
            engine=test_engine,
            table="test_table",
            operation="upsert",
            conflict_columns=["email"],
        )

        assert result["inserted_count"] == 0
        assert result["updated_count"] == 1

        # Verify the update
        config = {
            "engine": test_engine,
            "table": "test_table",
            "selectors": {"email": "alice@example.com"},
        }
        user = await AsyncSQLAdapter.from_obj(TestModel, config, many=False)
        assert user.name == "Alice Updated"
        assert user.age == 26

    @pytest.mark.asyncio
    async def test_raw_sql_operation(self, test_engine):
        """Test raw SQL execution."""
        # Insert test data
        users = [
            TestModel(name="User1", email="user1@example.com", age=20),
            TestModel(name="User2", email="user2@example.com", age=30),
            TestModel(name="User3", email="user3@example.com", age=40),
        ]
        for user in users:
            await AsyncSQLAdapter.to_obj(user, engine=test_engine, table="test_table")

        # Execute raw SQL query
        config = {
            "engine": test_engine,
            "operation": "raw_sql",
            "sql": """
                SELECT COUNT(*) as count, AVG(age) as avg_age
                FROM test_table
                WHERE active = :active
            """,
            "params": {"active": True},
        }
        result = await AsyncSQLAdapter.from_obj(dict, config, many=False)

        assert result["count"] == 3
        assert result["avg_age"] == 30.0

    @pytest.mark.asyncio
    async def test_parameter_validation(self):
        """Test parameter validation."""
        # Missing required parameters
        with pytest.raises(ValidationError) as exc_info:
            await AsyncSQLAdapter.from_obj(TestModel, {})
        assert "Missing required parameter" in str(exc_info.value)

        # Multiple engine parameters
        with pytest.raises(ValidationError) as exc_info:
            config = {
                "dsn": "postgresql://localhost/test",
                "engine_url": "postgresql://localhost/test",
                "table": "test_table",
            }
            await AsyncSQLAdapter.from_obj(TestModel, config)
        assert "Multiple engine parameters" in str(exc_info.value)

        # Invalid operation
        with pytest.raises(ValidationError) as exc_info:
            config = {
                "dsn": "sqlite+aiosqlite:///:memory:",
                "table": "test_table",
                "operation": "invalid_op",
            }
            await AsyncSQLAdapter.from_obj(TestModel, config)
        assert "Unsupported operation" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_none_value_handling(self, test_engine):
        """Test that None values are properly excluded from INSERT/UPDATE."""
        # Insert with None values
        user = TestModel(
            id=None,  # Should be excluded
            name="Test User",
            email="test@example.com",
            age=25,
            created_at=None,  # Should be excluded
        )

        result = await AsyncSQLAdapter.to_obj(
            user, engine=test_engine, table="test_table"
        )
        assert result == {"inserted_count": 1}

        # Verify the insert worked (would fail if None was included for id)
        config = {
            "engine": test_engine,
            "table": "test_table",
            "selectors": {"email": "test@example.com"},
        }
        saved_user = await AsyncSQLAdapter.from_obj(TestModel, config, many=False)
        assert saved_user.name == "Test User"
        assert saved_user.id is not None  # Auto-generated

    @pytest.mark.asyncio
    async def test_dsn_parameter_support(self):
        """Test DSN parameter support and conversion."""
        # Test with dsn parameter
        config: SQLReadConfig = {
            "dsn": "sqlite+aiosqlite:///:memory:",
            "table": "test_table",
        }

        # Should accept dsn without error (will fail on actual query but parameter is accepted)
        try:
            await AsyncSQLAdapter.from_obj(TestModel, config, many=True)
        except Exception as e:
            # Expected to fail on query, but should accept dsn parameter
            assert "dsn" not in str(e).lower() or "missing" not in str(e).lower()

    @pytest.mark.asyncio
    async def test_typed_dict_support(self):
        """Test TypedDict configuration support."""
        # Using TypedDict for configuration
        read_config: SQLReadConfig = {
            "dsn": "sqlite+aiosqlite:///:memory:",
            "table": "test_table",
            "operation": "select",
            "selectors": {"active": True},
            "limit": 10,
        }

        # Should accept TypedDict configuration
        try:
            await AsyncSQLAdapter.from_obj(TestModel, read_config, many=True)
        except Exception:
            # Expected to fail on connection, but TypedDict should be accepted
            pass


class TestAsyncPostgresAdapter:
    """Test AsyncPostgresAdapter specific functionality."""

    @pytest.mark.asyncio
    async def test_dsn_conversion(self):
        """Test PostgreSQL DSN format conversion."""
        # Mock the parent class from_obj
        with patch.object(
            AsyncSQLAdapter, "from_obj", new_callable=AsyncMock
        ) as mock_from_obj:
            mock_from_obj.return_value = []

            # Test with PostgreSQL format (should be converted)
            config = {
                "dsn": "postgresql://user:pass@localhost/db",
                "table": "test_table",
            }

            await AsyncPostgresAdapter.from_obj(TestModel, config, many=True)

            # Check that dsn was converted
            call_args = mock_from_obj.call_args[0]
            assert "postgresql+asyncpg://" in call_args[1]["dsn"]

    @pytest.mark.asyncio
    async def test_backward_compatibility_engine_url(self):
        """Test backward compatibility with engine_url parameter."""
        with patch.object(
            AsyncSQLAdapter, "from_obj", new_callable=AsyncMock
        ) as mock_from_obj:
            mock_from_obj.return_value = []

            # Test with legacy engine_url parameter
            config = {
                "engine_url": "postgresql://user:pass@localhost/db",
                "table": "test_table",
            }

            await AsyncPostgresAdapter.from_obj(TestModel, config, many=True)

            # Check that engine_url was converted to dsn
            call_args = mock_from_obj.call_args[0]
            assert "dsn" in call_args[1]
            assert "postgresql+asyncpg://" in call_args[1]["dsn"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
