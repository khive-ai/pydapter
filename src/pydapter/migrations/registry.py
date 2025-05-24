"""
pydapter.migrations.registry - Registry for migration adapters.
"""

from typing import Any, Optional, TypeVar

from pydapter.exceptions import AdapterNotFoundError, ConfigurationError
from pydapter.migrations.exceptions import (
    MigrationCreationError,
    MigrationDowngradeError,
    MigrationError,
    MigrationInitError,
    MigrationUpgradeError,
)
from pydapter.migrations.protocols import AsyncMigrationProtocol, MigrationProtocol

T = TypeVar("T")


class MigrationRegistry:
    """Registry for migration adapters."""

    def __init__(self) -> None:
        self._reg: dict[str, type[MigrationProtocol]] = {}

    def register(self, adapter_cls: type[MigrationProtocol]) -> None:
        """
        Register a migration adapter.

        Args:
            adapter_cls: The adapter class to register

        Raises:
            ConfigurationError: If the adapter does not define a migration_key
        """
        key = getattr(adapter_cls, "migration_key", None)
        if not key:
            raise ConfigurationError(
                "Migration adapter must define 'migration_key'",
                adapter_cls=adapter_cls.__name__,
            )
        self._reg[key] = adapter_cls

    def get(self, migration_key: str) -> type[MigrationProtocol]:
        """
        Get a migration adapter by key.

        Args:
            migration_key: The key of the adapter to retrieve

        Returns:
            The adapter class

        Raises:
            AdapterNotFoundError: If no adapter is registered for the given key
        """
        try:
            return self._reg[migration_key]
        except KeyError as exc:
            raise AdapterNotFoundError(
                f"No migration adapter registered for '{migration_key}'",
                obj_key=migration_key,
            ) from exc

    # Convenience methods for migration operations

    def init_migrations(
        self, migration_key: str, directory: str, **kwargs: Any
    ) -> None:
        """
        Initialize migrations for the specified adapter.

        Args:
            migration_key: The key of the adapter to use
            directory: The directory to initialize migrations in
            **kwargs: Additional adapter-specific arguments

        Raises:
            MigrationInitError: If initialization fails
        """
        try:
            adapter_cls = self.get(migration_key)
            adapter_cls.init_migrations(directory, **kwargs)
        except Exception as exc:
            if isinstance(exc, MigrationError):
                raise
            raise MigrationInitError(
                f"Failed to initialize migrations for '{migration_key}'",
                directory=directory,
                adapter=migration_key,
                original_error=str(exc),
            ) from exc

    def create_migration(
        self, migration_key: str, message: str, autogenerate: bool = True, **kwargs: Any
    ) -> str:
        """
        Create a migration for the specified adapter.

        Args:
            migration_key: The key of the adapter to use
            message: The migration message
            autogenerate: Whether to auto-generate the migration
            **kwargs: Additional adapter-specific arguments

        Returns:
            The revision identifier of the created migration

        Raises:
            MigrationCreationError: If creation fails
        """
        try:
            adapter_cls = self.get(migration_key)
            return adapter_cls.create_migration(message, autogenerate, **kwargs)
        except Exception as exc:
            if isinstance(exc, MigrationError):
                raise
            raise MigrationCreationError(
                f"Failed to create migration for '{migration_key}'",
                message_text=message,
                autogenerate=autogenerate,
                adapter=migration_key,
                original_error=str(exc),
            ) from exc

    def upgrade(
        self, migration_key: str, revision: str = "head", **kwargs: Any
    ) -> None:
        """
        Upgrade migrations for the specified adapter.

        Args:
            migration_key: The key of the adapter to use
            revision: The target revision to upgrade to
            **kwargs: Additional adapter-specific arguments

        Raises:
            MigrationUpgradeError: If upgrade fails
        """
        try:
            adapter_cls = self.get(migration_key)
            adapter_cls.upgrade(revision, **kwargs)
        except Exception as exc:
            if isinstance(exc, MigrationError):
                raise
            raise MigrationUpgradeError(
                f"Failed to upgrade migrations for '{migration_key}'",
                revision=revision,
                adapter=migration_key,
                original_error=str(exc),
            ) from exc

    def downgrade(self, migration_key: str, revision: str, **kwargs: Any) -> None:
        """
        Downgrade migrations for the specified adapter.

        Args:
            migration_key: The key of the adapter to use
            revision: The target revision to downgrade to
            **kwargs: Additional adapter-specific arguments

        Raises:
            MigrationDowngradeError: If downgrade fails
        """
        try:
            adapter_cls = self.get(migration_key)
            adapter_cls.downgrade(revision, **kwargs)
        except Exception as exc:
            if isinstance(exc, MigrationError):
                raise
            raise MigrationDowngradeError(
                f"Failed to downgrade migrations for '{migration_key}'",
                revision=revision,
                adapter=migration_key,
                original_error=str(exc),
            ) from exc

    def get_current_revision(self, migration_key: str, **kwargs: Any) -> Optional[str]:
        """
        Get the current revision for the specified adapter.

        Args:
            migration_key: The key of the adapter to use
            **kwargs: Additional adapter-specific arguments

        Returns:
            The current revision identifier, or None if no migrations have been applied

        Raises:
            MigrationError: If getting the current revision fails
        """
        try:
            adapter_cls = self.get(migration_key)
            return adapter_cls.get_current_revision(**kwargs)
        except Exception as exc:
            if isinstance(exc, MigrationError):
                raise
            raise MigrationError(
                f"Failed to get current revision for '{migration_key}'",
                adapter=migration_key,
                original_error=exc,
            ) from exc

    def get_migration_history(self, migration_key: str, **kwargs: Any) -> list[dict]:
        """
        Get the migration history for the specified adapter.

        Args:
            migration_key: The key of the adapter to use
            **kwargs: Additional adapter-specific arguments

        Returns:
            A list of dictionaries containing migration information

        Raises:
            MigrationError: If getting the migration history fails
        """
        try:
            adapter_cls = self.get(migration_key)
            return adapter_cls.get_migration_history(**kwargs)
        except Exception as exc:
            if isinstance(exc, MigrationError):
                raise
            raise MigrationError(
                f"Failed to get migration history for '{migration_key}'",
                adapter=migration_key,
                original_error=exc,
            ) from exc


class AsyncMigrationRegistry:
    """Registry for asynchronous migration adapters."""

    def __init__(self) -> None:
        self._reg: dict[str, type[AsyncMigrationProtocol]] = {}

    def register(self, adapter_cls: type[AsyncMigrationProtocol]) -> None:
        """
        Register an async migration adapter.

        Args:
            adapter_cls: The adapter class to register

        Raises:
            ConfigurationError: If the adapter does not define a migration_key
        """
        key = getattr(adapter_cls, "migration_key", None)
        if not key:
            raise ConfigurationError(
                "Async migration adapter must define 'migration_key'",
                adapter_cls=adapter_cls.__name__,
            )
        self._reg[key] = adapter_cls

    def get(self, migration_key: str) -> type[AsyncMigrationProtocol]:
        """
        Get an async migration adapter by key.

        Args:
            migration_key: The key of the adapter to retrieve

        Returns:
            The adapter class

        Raises:
            AdapterNotFoundError: If no adapter is registered for the given key
        """
        try:
            return self._reg[migration_key]
        except KeyError as exc:
            raise AdapterNotFoundError(
                f"No async migration adapter registered for '{migration_key}'",
                obj_key=migration_key,
            ) from exc

    # Convenience methods for async migration operations

    async def init_migrations(
        self, migration_key: str, directory: str, **kwargs: Any
    ) -> None:
        """
        Initialize migrations for the specified adapter.

        Args:
            migration_key: The key of the adapter to use
            directory: The directory to initialize migrations in
            **kwargs: Additional adapter-specific arguments

        Raises:
            MigrationInitError: If initialization fails
        """
        try:
            adapter_cls = self.get(migration_key)
            await adapter_cls.init_migrations(directory, **kwargs)
        except Exception as exc:
            if isinstance(exc, MigrationError):
                raise
            raise MigrationInitError(
                f"Failed to initialize async migrations for '{migration_key}'",
                directory=directory,
                adapter=migration_key,
                original_error=str(exc),
            ) from exc

    async def create_migration(
        self, migration_key: str, message: str, autogenerate: bool = True, **kwargs: Any
    ) -> str:
        """
        Create a migration for the specified adapter.

        Args:
            migration_key: The key of the adapter to use
            message: The migration message
            autogenerate: Whether to auto-generate the migration
            **kwargs: Additional adapter-specific arguments

        Returns:
            The revision identifier of the created migration

        Raises:
            MigrationCreationError: If creation fails
        """
        try:
            adapter_cls = self.get(migration_key)
            return await adapter_cls.create_migration(message, autogenerate, **kwargs)
        except Exception as exc:
            if isinstance(exc, MigrationError):
                raise
            raise MigrationCreationError(
                f"Failed to create async migration for '{migration_key}'",
                message_text=message,
                autogenerate=autogenerate,
                adapter=migration_key,
                original_error=str(exc),
            ) from exc

    async def upgrade(
        self, migration_key: str, revision: str = "head", **kwargs: Any
    ) -> None:
        """
        Upgrade migrations for the specified adapter.

        Args:
            migration_key: The key of the adapter to use
            revision: The target revision to upgrade to
            **kwargs: Additional adapter-specific arguments

        Raises:
            MigrationUpgradeError: If upgrade fails
        """
        try:
            adapter_cls = self.get(migration_key)
            await adapter_cls.upgrade(revision, **kwargs)
        except Exception as exc:
            if isinstance(exc, MigrationError):
                raise
            raise MigrationUpgradeError(
                f"Failed to upgrade async migrations for '{migration_key}'",
                revision=revision,
                adapter=migration_key,
                original_error=str(exc),
            ) from exc

    async def downgrade(self, migration_key: str, revision: str, **kwargs: Any) -> None:
        """
        Downgrade migrations for the specified adapter.

        Args:
            migration_key: The key of the adapter to use
            revision: The target revision to downgrade to
            **kwargs: Additional adapter-specific arguments

        Raises:
            MigrationDowngradeError: If downgrade fails
        """
        try:
            adapter_cls = self.get(migration_key)
            await adapter_cls.downgrade(revision, **kwargs)
        except Exception as exc:
            if isinstance(exc, MigrationError):
                raise
            raise MigrationDowngradeError(
                f"Failed to downgrade async migrations for '{migration_key}'",
                revision=revision,
                adapter=migration_key,
                original_error=str(exc),
            ) from exc

    async def get_current_revision(
        self, migration_key: str, **kwargs: Any
    ) -> Optional[str]:
        """
        Get the current revision for the specified adapter.

        Args:
            migration_key: The key of the adapter to use
            **kwargs: Additional adapter-specific arguments

        Returns:
            The current revision identifier, or None if no migrations have been applied

        Raises:
            MigrationError: If getting the current revision fails
        """
        try:
            adapter_cls = self.get(migration_key)
            return await adapter_cls.get_current_revision(**kwargs)
        except Exception as exc:
            if isinstance(exc, MigrationError):
                raise
            raise MigrationError(
                f"Failed to get current async revision for '{migration_key}'",
                adapter=migration_key,
                original_error=exc,
            ) from exc

    async def get_migration_history(
        self, migration_key: str, **kwargs: Any
    ) -> list[dict]:
        """
        Get the migration history for the specified adapter.

        Args:
            migration_key: The key of the adapter to use
            **kwargs: Additional adapter-specific arguments

        Returns:
            A list of dictionaries containing migration information

        Raises:
            MigrationError: If getting the migration history fails
        """
        try:
            adapter_cls = self.get(migration_key)
            return await adapter_cls.get_migration_history(**kwargs)
        except Exception as exc:
            if isinstance(exc, MigrationError):
                raise
            raise MigrationError(
                f"Failed to get async migration history for '{migration_key}'",
                adapter=migration_key,
                original_error=exc,
            ) from exc
