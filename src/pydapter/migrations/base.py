"""
pydapter.migrations.base - Base classes for migration adapters.
"""

import os
from abc import ABC
from typing import Any, ClassVar, Optional

from pydapter.migrations.exceptions import MigrationError
from pydapter.migrations.protocols import AsyncMigrationProtocol, MigrationProtocol


class BaseMigrationAdapter(ABC):
    """Base class for migration adapters."""

    migration_key: ClassVar[str]

    def __init__(self, connection_string: str, models_module: Any = None):
        """
        Initialize the migration adapter.

        Args:
            connection_string: Database connection string
            models_module: Optional module containing model definitions
        """
        self.connection_string = connection_string
        self.models_module = models_module
        self._initialized = False
        self._migrations_dir = None

    def _ensure_directory(self, directory: str) -> None:
        """
        Ensure the directory exists.

        Args:
            directory: Directory path
        """
        if not os.path.exists(directory):
            os.makedirs(directory)

    def _check_initialized(self) -> None:
        """
        Check if migrations have been initialized.

        Raises:
            MigrationError: If migrations have not been initialized
        """
        if not self._initialized:
            raise MigrationError(
                "Migrations have not been initialized. Call init_migrations first.",
                adapter=self.__class__.migration_key,
            )


class SyncMigrationAdapter(BaseMigrationAdapter, MigrationProtocol):
    """Base class for synchronous migration adapters."""

    @classmethod
    def init_migrations(cls, directory: str, **kwargs: Any) -> None:
        """
        Initialize migration environment in the specified directory.

        Args:
            directory: Path to the directory where migrations will be stored
            **kwargs: Additional adapter-specific arguments

        Raises:
            MigrationInitError: If initialization fails
        """
        raise NotImplementedError("Subclasses must implement init_migrations")

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

        Raises:
            MigrationCreationError: If creation fails
        """
        raise NotImplementedError("Subclasses must implement create_migration")

    @classmethod
    def upgrade(cls, revision: str = "head", **kwargs: Any) -> None:
        """
        Upgrade to the specified revision.

        Args:
            revision: The target revision to upgrade to (default: "head")
            **kwargs: Additional adapter-specific arguments

        Raises:
            MigrationUpgradeError: If upgrade fails
        """
        raise NotImplementedError("Subclasses must implement upgrade")

    @classmethod
    def downgrade(cls, revision: str, **kwargs: Any) -> None:
        """
        Downgrade to the specified revision.

        Args:
            revision: The target revision to downgrade to
            **kwargs: Additional adapter-specific arguments

        Raises:
            MigrationDowngradeError: If downgrade fails
        """
        raise NotImplementedError("Subclasses must implement downgrade")

    @classmethod
    def get_current_revision(cls, **kwargs: Any) -> Optional[str]:
        """
        Get the current migration revision.

        Args:
            **kwargs: Additional adapter-specific arguments

        Returns:
            The current revision identifier, or None if no migrations have been applied

        Raises:
            MigrationError: If getting the current revision fails
        """
        raise NotImplementedError("Subclasses must implement get_current_revision")

    @classmethod
    def get_migration_history(cls, **kwargs: Any) -> list[dict[str, Any]]:
        """
        Get the migration history.

        Args:
            **kwargs: Additional adapter-specific arguments

        Returns:
            A list of dictionaries containing migration information

        Raises:
            MigrationError: If getting the migration history fails
        """
        raise NotImplementedError("Subclasses must implement get_migration_history")


class AsyncMigrationAdapter(BaseMigrationAdapter, AsyncMigrationProtocol):
    """Base class for asynchronous migration adapters."""

    @classmethod
    async def init_migrations(cls, directory: str, **kwargs: Any) -> None:
        """
        Initialize migration environment in the specified directory.

        Args:
            directory: Path to the directory where migrations will be stored
            **kwargs: Additional adapter-specific arguments

        Raises:
            MigrationInitError: If initialization fails
        """
        raise NotImplementedError("Subclasses must implement init_migrations")

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

        Raises:
            MigrationCreationError: If creation fails
        """
        raise NotImplementedError("Subclasses must implement create_migration")

    @classmethod
    async def upgrade(cls, revision: str = "head", **kwargs: Any) -> None:
        """
        Upgrade to the specified revision.

        Args:
            revision: The target revision to upgrade to (default: "head")
            **kwargs: Additional adapter-specific arguments

        Raises:
            MigrationUpgradeError: If upgrade fails
        """
        raise NotImplementedError("Subclasses must implement upgrade")

    @classmethod
    async def downgrade(cls, revision: str, **kwargs: Any) -> None:
        """
        Downgrade to the specified revision.

        Args:
            revision: The target revision to downgrade to
            **kwargs: Additional adapter-specific arguments

        Raises:
            MigrationDowngradeError: If downgrade fails
        """
        raise NotImplementedError("Subclasses must implement downgrade")

    @classmethod
    async def get_current_revision(cls, **kwargs: Any) -> Optional[str]:
        """
        Get the current migration revision.

        Args:
            **kwargs: Additional adapter-specific arguments

        Returns:
            The current revision identifier, or None if no migrations have been applied

        Raises:
            MigrationError: If getting the current revision fails
        """
        raise NotImplementedError("Subclasses must implement get_current_revision")

    @classmethod
    async def get_migration_history(cls, **kwargs: Any) -> list[dict[str, Any]]:
        """
        Get the migration history.

        Args:
            **kwargs: Additional adapter-specific arguments

        Returns:
            A list of dictionaries containing migration information

        Raises:
            MigrationError: If getting the migration history fails
        """
        raise NotImplementedError("Subclasses must implement get_migration_history")
