"""
pydapter.migrations.protocols - Protocol definitions for migration adapters.
"""

from __future__ import annotations

from typing import Any, ClassVar, Protocol, TypeVar, runtime_checkable

T = TypeVar("T", covariant=True)


@runtime_checkable
class MigrationProtocol(Protocol[T]):
    """Protocol defining synchronous migration operations."""

    migration_key: ClassVar[str]

    @classmethod
    def init_migrations(cls, directory: str, **kwargs: Any) -> None:
        """
        Initialize migration environment in the specified directory.

        Args:
            directory: Path to the directory where migrations will be stored
            **kwargs: Additional adapter-specific arguments
        """
        ...

    @classmethod
    def create_migration(
        cls, message: str, autogenerate: bool = True, **kwargs: Any
    ) -> str:
        """
        Create a new migration.

        Args:
            message: Description of the migration
            autogenerate: Whether to auto-generate the migration based on model changes
            **kwargs: Additional adapter-specific arguments

        Returns:
            The revision identifier of the created migration
        """
        ...

    @classmethod
    def upgrade(cls, revision: str = "head", **kwargs: Any) -> None:
        """
        Upgrade to the specified revision.

        Args:
            revision: The target revision to upgrade to (default: "head")
            **kwargs: Additional adapter-specific arguments
        """
        ...

    @classmethod
    def downgrade(cls, revision: str, **kwargs: Any) -> None:
        """
        Downgrade to the specified revision.

        Args:
            revision: The target revision to downgrade to
            **kwargs: Additional adapter-specific arguments
        """
        ...

    @classmethod
    def get_current_revision(cls, **kwargs: Any) -> str | None:
        """
        Get the current migration revision.

        Args:
            **kwargs: Additional adapter-specific arguments

        Returns:
            The current revision identifier, or None if no migrations have been applied
        """
        ...

    @classmethod
    def get_migration_history(cls, **kwargs: Any) -> list[dict]:
        """
        Get the migration history.

        Args:
            **kwargs: Additional adapter-specific arguments

        Returns:
            A list of dictionaries containing migration information
        """
        ...


@runtime_checkable
class AsyncMigrationProtocol(Protocol[T]):
    """Protocol defining asynchronous migration operations."""

    migration_key: ClassVar[str]

    @classmethod
    async def init_migrations(cls, directory: str, **kwargs: Any) -> None:
        """
        Initialize migration environment in the specified directory.

        Args:
            directory: Path to the directory where migrations will be stored
            **kwargs: Additional adapter-specific arguments
        """
        ...

    @classmethod
    async def create_migration(
        cls, message: str, autogenerate: bool = True, **kwargs: Any
    ) -> str:
        """
        Create a new migration.

        Args:
            message: Description of the migration
            autogenerate: Whether to auto-generate the migration based on model changes
            **kwargs: Additional adapter-specific arguments

        Returns:
            The revision identifier of the created migration
        """
        ...

    @classmethod
    async def upgrade(cls, revision: str = "head", **kwargs: Any) -> None:
        """
        Upgrade to the specified revision.

        Args:
            revision: The target revision to upgrade to (default: "head")
            **kwargs: Additional adapter-specific arguments
        """
        ...

    @classmethod
    async def downgrade(cls, revision: str, **kwargs: Any) -> None:
        """
        Downgrade to the specified revision.

        Args:
            revision: The target revision to downgrade to
            **kwargs: Additional adapter-specific arguments
        """
        ...

    @classmethod
    async def get_current_revision(cls, **kwargs: Any) -> str | None:
        """
        Get the current migration revision.

        Args:
            **kwargs: Additional adapter-specific arguments

        Returns:
            The current revision identifier, or None if no migrations have been applied
        """
        ...

    @classmethod
    async def get_migration_history(cls, **kwargs: Any) -> list[dict]:
        """
        Get the migration history.

        Args:
            **kwargs: Additional adapter-specific arguments

        Returns:
            A list of dictionaries containing migration information
        """
        ...
