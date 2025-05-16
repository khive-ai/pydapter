"""
Tests for migration registry.
"""

from typing import ClassVar, Optional

import pytest

from pydapter.exceptions import AdapterNotFoundError, ConfigurationError
from pydapter.migrations.registry import MigrationRegistry


class TestMigrationAdapter:
    migration_key: ClassVar[str] = "test"

    @classmethod
    def init_migrations(cls, directory: str, **kwargs) -> None:
        return None

    @classmethod
    def create_migration(cls, message: str, autogenerate: bool = True, **kwargs) -> str:
        return "revision123"

    @classmethod
    def upgrade(cls, revision: str = "head", **kwargs) -> None:
        return None

    @classmethod
    def downgrade(cls, revision: str, **kwargs) -> None:
        return None

    @classmethod
    def get_current_revision(cls, **kwargs) -> Optional[str]:
        return "revision123"

    @classmethod
    def get_migration_history(cls, **kwargs) -> list[dict]:
        return [{"revision": "revision123", "message": "test migration"}]


class InvalidMigrationAdapter:
    # Missing migration_key

    @classmethod
    def init_migrations(cls, directory: str, **kwargs) -> None:
        return None


def test_migration_registry_registration():
    """Test that migration adapters can be registered and retrieved."""
    registry = MigrationRegistry()

    # Register a valid adapter
    registry.register(TestMigrationAdapter)

    # Retrieve the adapter
    adapter_cls = registry.get("test")
    assert adapter_cls == TestMigrationAdapter

    # Check that the adapter has the expected methods
    assert hasattr(adapter_cls, "init_migrations")
    assert hasattr(adapter_cls, "create_migration")
    assert hasattr(adapter_cls, "upgrade")
    assert hasattr(adapter_cls, "downgrade")
    assert hasattr(adapter_cls, "get_current_revision")
    assert hasattr(adapter_cls, "get_migration_history")


def test_migration_registry_invalid_adapter():
    """Test that registering an invalid adapter raises an error."""
    registry = MigrationRegistry()

    # Try to register an invalid adapter (missing migration_key)
    with pytest.raises(ConfigurationError) as exc_info:
        registry.register(InvalidMigrationAdapter)

    assert "must define 'migration_key'" in str(exc_info.value)


def test_migration_registry_adapter_not_found():
    """Test that retrieving a non-existent adapter raises an error."""
    registry = MigrationRegistry()

    # Try to retrieve a non-existent adapter
    with pytest.raises(AdapterNotFoundError) as exc_info:
        registry.get("non_existent")

    assert "No migration adapter registered for 'non_existent'" in str(exc_info.value)


def test_migration_registry_convenience_methods():
    """Test the convenience methods for migration operations."""
    registry = MigrationRegistry()
    registry.register(TestMigrationAdapter)

    # Test init_migrations
    registry.init_migrations("test", directory="/tmp/migrations")

    # Test create_migration
    revision = registry.create_migration("test", message="Test migration")
    assert revision == "revision123"

    # Test upgrade
    registry.upgrade("test")

    # Test downgrade
    registry.downgrade("test", revision="revision123")

    # Test get_current_revision
    current_revision = registry.get_current_revision("test")
    assert current_revision == "revision123"

    # Test get_migration_history
    history = registry.get_migration_history("test")
    assert len(history) == 1
    assert history[0]["revision"] == "revision123"
