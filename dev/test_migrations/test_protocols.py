"""
Tests for migration protocol interfaces.
"""

from typing import ClassVar, Optional

from pydapter.migrations.protocols import AsyncMigrationProtocol, MigrationProtocol


def test_migration_protocol_interface():
    """Test that the MigrationProtocol interface is correctly defined."""

    # Define a class that implements the MigrationProtocol
    class TestMigrationAdapter:
        migration_key: ClassVar[str] = "test"

        @classmethod
        def init_migrations(cls, directory: str, **kwargs) -> None:
            return None

        @classmethod
        def create_migration(
            cls, message: str, autogenerate: bool = True, **kwargs
        ) -> str:
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

    # Check that the class implements the protocol
    assert isinstance(TestMigrationAdapter, type)

    # Create an instance to test with isinstance instead of issubclass
    # This is because protocols with non-method members don't support issubclass()
    adapter = TestMigrationAdapter()
    assert isinstance(adapter, MigrationProtocol)


def test_async_migration_protocol_interface():
    """Test that the AsyncMigrationProtocol interface is correctly defined."""

    # Define a class that implements the AsyncMigrationProtocol
    class TestAsyncMigrationAdapter:
        migration_key: ClassVar[str] = "test_async"

        @classmethod
        async def init_migrations(cls, directory: str, **kwargs) -> None:
            return None

        @classmethod
        async def create_migration(
            cls, message: str, autogenerate: bool = True, **kwargs
        ) -> str:
            return "revision123"

        @classmethod
        async def upgrade(cls, revision: str = "head", **kwargs) -> None:
            return None

        @classmethod
        async def downgrade(cls, revision: str, **kwargs) -> None:
            return None

        @classmethod
        async def get_current_revision(cls, **kwargs) -> Optional[str]:
            return "revision123"

        @classmethod
        async def get_migration_history(cls, **kwargs) -> list[dict]:
            return [{"revision": "revision123", "message": "test migration"}]

    # Check that the class implements the protocol
    assert isinstance(TestAsyncMigrationAdapter, type)

    # Create an instance to test with isinstance instead of issubclass
    # This is because protocols with non-method members don't support issubclass()
    adapter = TestAsyncMigrationAdapter()
    assert isinstance(adapter, AsyncMigrationProtocol)
