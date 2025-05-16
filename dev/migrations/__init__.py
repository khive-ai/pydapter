"""
pydapter.migrations - Database migration support for pydapter.

This package provides standardized database migration capabilities for pydapter,
enabling consistent schema migration approaches across different database types.
It supports both SQL databases (using Alembic) and NoSQL databases (using custom
migration strategies) while maintaining pydapter's clean API design and supporting
both synchronous and asynchronous operations.
"""

from pydapter.migrations.protocols import MigrationProtocol, AsyncMigrationProtocol
from pydapter.migrations.registry import MigrationRegistry, AsyncMigrationRegistry
from pydapter.migrations.base import BaseMigrationAdapter, SyncMigrationAdapter, AsyncMigrationAdapter
from pydapter.migrations.exceptions import (
    MigrationError,
    MigrationInitError,
    MigrationCreationError,
    MigrationUpgradeError,
    MigrationDowngradeError,
    MigrationNotFoundError,
)
from pydapter.migrations.sql import AlembicMigrationAdapter, AsyncAlembicMigrationAdapter

# Create global registries
migration_registry = MigrationRegistry()
async_migration_registry = AsyncMigrationRegistry()


# Convenience functions for synchronous operations
def register_migration_adapter(adapter_cls):
    """Register a migration adapter with the global registry."""
    migration_registry.register(adapter_cls)


def init_migrations(migration_key: str, directory: str, **kwargs):
    """Initialize migrations for the specified adapter."""
    return migration_registry.init_migrations(migration_key, directory, **kwargs)


def create_migration(migration_key: str, message: str, autogenerate: bool = True, **kwargs):
    """Create a migration for the specified adapter."""
    return migration_registry.create_migration(
        migration_key, message, autogenerate, **kwargs
    )


def upgrade(migration_key: str, revision: str = "head", **kwargs):
    """Upgrade migrations for the specified adapter."""
    return migration_registry.upgrade(migration_key, revision, **kwargs)


def downgrade(migration_key: str, revision: str, **kwargs):
    """Downgrade migrations for the specified adapter."""
    return migration_registry.downgrade(migration_key, revision, **kwargs)


def get_current_revision(migration_key: str, **kwargs):
    """Get the current revision for the specified adapter."""
    return migration_registry.get_current_revision(migration_key, **kwargs)


def get_migration_history(migration_key: str, **kwargs):
    """Get the migration history for the specified adapter."""
    return migration_registry.get_migration_history(migration_key, **kwargs)


# Convenience functions for asynchronous operations
def register_async_migration_adapter(adapter_cls):
    """Register an async migration adapter with the global registry."""
    async_migration_registry.register(adapter_cls)


async def init_migrations_async(migration_key: str, directory: str, **kwargs):
    """Initialize migrations for the specified async adapter."""
    return await async_migration_registry.init_migrations(migration_key, directory, **kwargs)


async def create_migration_async(migration_key: str, message: str, autogenerate: bool = True, **kwargs):
    """Create a migration for the specified async adapter."""
    return await async_migration_registry.create_migration(
        migration_key, message, autogenerate, **kwargs
    )


async def upgrade_async(migration_key: str, revision: str = "head", **kwargs):
    """Upgrade migrations for the specified async adapter."""
    return await async_migration_registry.upgrade(migration_key, revision, **kwargs)


async def downgrade_async(migration_key: str, revision: str, **kwargs):
    """Downgrade migrations for the specified async adapter."""
    return await async_migration_registry.downgrade(migration_key, revision, **kwargs)


async def get_current_revision_async(migration_key: str, **kwargs):
    """Get the current revision for the specified async adapter."""
    return await async_migration_registry.get_current_revision(migration_key, **kwargs)


async def get_migration_history_async(migration_key: str, **kwargs):
    """Get the migration history for the specified async adapter."""
    return await async_migration_registry.get_migration_history(migration_key, **kwargs)


# Aliases for async functions with async_ prefix
async_init_migrations = init_migrations_async
async_create_migration = create_migration_async
async_upgrade = upgrade_async
async_downgrade = downgrade_async
async_get_current_revision = get_current_revision_async
async_get_migration_history = get_migration_history_async


__all__ = [
    # Protocols
    "MigrationProtocol",
    "AsyncMigrationProtocol",
    
    # Registries
    "MigrationRegistry",
    "AsyncMigrationRegistry",
    "migration_registry",
    "async_migration_registry",
    
    # Base Classes
    "BaseMigrationAdapter",
    "SyncMigrationAdapter",
    "AsyncMigrationAdapter",
    
    # Exceptions
    "MigrationError",
    "MigrationInitError",
    "MigrationCreationError",
    "MigrationUpgradeError",
    "MigrationDowngradeError",
    "MigrationNotFoundError",
    
    # SQL Adapters
    "AlembicMigrationAdapter",
    "AsyncAlembicMigrationAdapter",
    
    # Sync convenience functions
    "register_migration_adapter",
    "init_migrations",
    "create_migration",
    "upgrade",
    "downgrade",
    "get_current_revision",
    "get_migration_history",
    
    # Async convenience functions
    "register_async_migration_adapter",
    "init_migrations_async",
    "create_migration_async",
    "upgrade_async",
    "downgrade_async",
    "get_current_revision_async",
    "get_migration_history_async",
    
    # Aliases for async functions
    "async_init_migrations",
    "async_create_migration",
    "async_upgrade",
    "async_downgrade",
    "async_get_current_revision",
    "async_get_migration_history",
]