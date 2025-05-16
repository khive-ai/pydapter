import warnings

warnings.warn(
    "Importing from dev.migrations is deprecated and will be removed in a future version. "
    "Please use pydapter.migrations instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export from new location
try:
    from pydapter.migrations import *
except ImportError:
    # If the new module isn't available, fall back to local implementation
    from .base import AsyncMigrationAdapter, BaseMigrationAdapter, SyncMigrationAdapter
    from .exceptions import (
        MigrationCreationError,
        MigrationDowngradeError,
        MigrationError,
        MigrationInitError,
        MigrationNotFoundError,
        MigrationUpgradeError,
    )
    from .protocols import AsyncMigrationProtocol, MigrationProtocol
    from .registry import MigrationRegistry

    __all__ = [
        "BaseMigrationAdapter",
        "SyncMigrationAdapter",
        "AsyncMigrationAdapter",
        "MigrationProtocol",
        "AsyncMigrationProtocol",
        "MigrationError",
        "MigrationInitError",
        "MigrationCreationError",
        "MigrationUpgradeError",
        "MigrationDowngradeError",
        "MigrationNotFoundError",
        "MigrationRegistry",
    ]

    try:
        from .sql.alembic_adapter import AlembicAdapter, AsyncAlembicAdapter

        __all__.extend(["AlembicAdapter", "AsyncAlembicAdapter"])
    except ImportError:
        pass
