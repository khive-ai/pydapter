"""
Tests for the migrations package public API.
"""

from typing import ClassVar, Optional

import pytest

from pydapter.migrations import (
    async_migration_registry,
    create_migration,
    downgrade,
    get_current_revision,
    get_migration_history,
    init_migrations,
    migration_registry,
    register_async_migration_adapter,
    register_migration_adapter,
    upgrade,
)


class TestMigrationAdapter:
    """Test migration adapter for synchronous operations."""

    migration_key: ClassVar[str] = "test"

    # Track calls to methods for testing
    init_calls = []
    create_calls = []
    upgrade_calls = []
    downgrade_calls = []
    current_revision_calls = []
    history_calls = []

    @classmethod
    def reset(cls):
        """Reset call tracking."""
        cls.init_calls = []
        cls.create_calls = []
        cls.upgrade_calls = []
        cls.downgrade_calls = []
        cls.current_revision_calls = []
        cls.history_calls = []

    @classmethod
    def init_migrations(cls, directory: str, **kwargs) -> None:
        cls.init_calls.append((directory, kwargs))
        return None

    @classmethod
    def create_migration(cls, message: str, autogenerate: bool = True, **kwargs) -> str:
        cls.create_calls.append((message, autogenerate, kwargs))
        return "revision123"

    @classmethod
    def upgrade(cls, revision: str = "head", **kwargs) -> None:
        cls.upgrade_calls.append((revision, kwargs))
        return None

    @classmethod
    def downgrade(cls, revision: str, **kwargs) -> None:
        cls.downgrade_calls.append((revision, kwargs))
        return None

    @classmethod
    def get_current_revision(cls, **kwargs) -> Optional[str]:
        cls.current_revision_calls.append(kwargs)
        return "revision123"

    @classmethod
    def get_migration_history(cls, **kwargs) -> list[dict]:
        cls.history_calls.append(kwargs)
        return [{"revision": "revision123", "message": "test migration"}]


class TestAsyncMigrationAdapter:
    """Test migration adapter for asynchronous operations."""

    migration_key: ClassVar[str] = "test_async"

    # Track calls to methods for testing
    init_calls = []
    create_calls = []
    upgrade_calls = []
    downgrade_calls = []
    current_revision_calls = []
    history_calls = []

    @classmethod
    def reset(cls):
        """Reset call tracking."""
        cls.init_calls = []
        cls.create_calls = []
        cls.upgrade_calls = []
        cls.downgrade_calls = []
        cls.current_revision_calls = []
        cls.history_calls = []

    @classmethod
    async def init_migrations(cls, directory: str, **kwargs) -> None:
        cls.init_calls.append((directory, kwargs))
        return None

    @classmethod
    async def create_migration(
        cls, message: str, autogenerate: bool = True, **kwargs
    ) -> str:
        cls.create_calls.append((message, autogenerate, kwargs))
        return "revision123"

    @classmethod
    async def upgrade(cls, revision: str = "head", **kwargs) -> None:
        cls.upgrade_calls.append((revision, kwargs))
        return None

    @classmethod
    async def downgrade(cls, revision: str, **kwargs) -> None:
        cls.downgrade_calls.append((revision, kwargs))
        return None

    @classmethod
    async def get_current_revision(cls, **kwargs) -> Optional[str]:
        cls.current_revision_calls.append(kwargs)
        return "revision123"

    @classmethod
    async def get_migration_history(cls, **kwargs) -> list[dict]:
        cls.history_calls.append(kwargs)
        return [{"revision": "revision123", "message": "test migration"}]


def test_register_migration_adapter():
    """Test registering a migration adapter."""
    # Reset the registry
    migration_registry._reg = {}

    # Register the adapter
    register_migration_adapter(TestMigrationAdapter)

    # Check that the adapter is registered
    assert "test" in migration_registry._reg
    assert migration_registry._reg["test"] == TestMigrationAdapter


def test_sync_convenience_functions():
    """Test the synchronous convenience functions."""
    # Reset the registry and adapter
    migration_registry._reg = {}
    TestMigrationAdapter.reset()

    # Register the adapter
    register_migration_adapter(TestMigrationAdapter)

    # Test init_migrations
    init_migrations("test", "/tmp/migrations", extra_arg="value")
    assert len(TestMigrationAdapter.init_calls) == 1
    assert TestMigrationAdapter.init_calls[0][0] == "/tmp/migrations"
    assert TestMigrationAdapter.init_calls[0][1]["extra_arg"] == "value"

    # Test create_migration
    revision = create_migration("test", "Test migration", extra_arg="value")
    assert revision == "revision123"
    assert len(TestMigrationAdapter.create_calls) == 1
    assert TestMigrationAdapter.create_calls[0][0] == "Test migration"
    assert TestMigrationAdapter.create_calls[0][1] is True  # autogenerate
    assert TestMigrationAdapter.create_calls[0][2]["extra_arg"] == "value"

    # Test upgrade
    upgrade("test", "head", extra_arg="value")
    assert len(TestMigrationAdapter.upgrade_calls) == 1
    assert TestMigrationAdapter.upgrade_calls[0][0] == "head"
    assert TestMigrationAdapter.upgrade_calls[0][1]["extra_arg"] == "value"

    # Test downgrade
    downgrade("test", "base", extra_arg="value")
    assert len(TestMigrationAdapter.downgrade_calls) == 1
    assert TestMigrationAdapter.downgrade_calls[0][0] == "base"
    assert TestMigrationAdapter.downgrade_calls[0][1]["extra_arg"] == "value"

    # Test get_current_revision
    current = get_current_revision("test", extra_arg="value")
    assert current == "revision123"
    assert len(TestMigrationAdapter.current_revision_calls) == 1
    assert TestMigrationAdapter.current_revision_calls[0]["extra_arg"] == "value"

    # Test get_migration_history
    history = get_migration_history("test", extra_arg="value")
    assert len(history) == 1
    assert history[0]["revision"] == "revision123"
    assert len(TestMigrationAdapter.history_calls) == 1
    assert TestMigrationAdapter.history_calls[0]["extra_arg"] == "value"


@pytest.mark.asyncio
async def test_register_async_migration_adapter():
    """Test registering an async migration adapter."""
    # Reset the registry
    async_migration_registry._reg = {}

    # Register the adapter
    register_async_migration_adapter(TestAsyncMigrationAdapter)

    # Check that the adapter is registered
    assert "test_async" in async_migration_registry._reg
    assert async_migration_registry._reg["test_async"] == TestAsyncMigrationAdapter


@pytest.mark.asyncio
async def test_async_convenience_functions():
    """Test the asynchronous convenience functions."""
    # Import async functions
    from pydapter.migrations import (
        create_migration_async,
        downgrade_async,
        get_current_revision_async,
        get_migration_history_async,
        init_migrations_async,
        upgrade_async,
    )

    # Reset the registry and adapter
    async_migration_registry._reg = {}
    TestAsyncMigrationAdapter.reset()

    # Register the adapter
    register_async_migration_adapter(TestAsyncMigrationAdapter)

    # Test init_migrations_async
    await init_migrations_async("test_async", "/tmp/migrations", extra_arg="value")
    assert len(TestAsyncMigrationAdapter.init_calls) == 1
    assert TestAsyncMigrationAdapter.init_calls[0][0] == "/tmp/migrations"
    assert TestAsyncMigrationAdapter.init_calls[0][1]["extra_arg"] == "value"

    # Test create_migration_async
    revision = await create_migration_async(
        "test_async", "Test migration", extra_arg="value"
    )
    assert revision == "revision123"
    assert len(TestAsyncMigrationAdapter.create_calls) == 1
    assert TestAsyncMigrationAdapter.create_calls[0][0] == "Test migration"
    assert TestAsyncMigrationAdapter.create_calls[0][1] is True  # autogenerate
    assert TestAsyncMigrationAdapter.create_calls[0][2]["extra_arg"] == "value"

    # Test upgrade_async
    await upgrade_async("test_async", "head", extra_arg="value")
    assert len(TestAsyncMigrationAdapter.upgrade_calls) == 1
    assert TestAsyncMigrationAdapter.upgrade_calls[0][0] == "head"
    assert TestAsyncMigrationAdapter.upgrade_calls[0][1]["extra_arg"] == "value"

    # Test downgrade_async
    await downgrade_async("test_async", "base", extra_arg="value")
    assert len(TestAsyncMigrationAdapter.downgrade_calls) == 1
    assert TestAsyncMigrationAdapter.downgrade_calls[0][0] == "base"
    assert TestAsyncMigrationAdapter.downgrade_calls[0][1]["extra_arg"] == "value"

    # Test get_current_revision_async
    current = await get_current_revision_async("test_async", extra_arg="value")
    assert current == "revision123"
    assert len(TestAsyncMigrationAdapter.current_revision_calls) == 1
    assert TestAsyncMigrationAdapter.current_revision_calls[0]["extra_arg"] == "value"

    # Test get_migration_history_async
    history = await get_migration_history_async("test_async", extra_arg="value")
    assert len(history) == 1
    assert history[0]["revision"] == "revision123"
    assert len(TestAsyncMigrationAdapter.history_calls) == 1
    assert TestAsyncMigrationAdapter.history_calls[0]["extra_arg"] == "value"
