from typing import TYPE_CHECKING
from importlib.util import find_spec

if TYPE_CHECKING:
    # Type checking imports
    from .base import BaseMigrationAdapter, SyncMigrationAdapter, AsyncMigrationAdapter
    from .protocols import MigrationProtocol, AsyncMigrationProtocol
    from .exceptions import (
        MigrationError, MigrationInitError, MigrationCreationError,
        MigrationUpgradeError, MigrationDowngradeError, MigrationNotFoundError
    )
    from .registry import MigrationRegistry
else:
    try:
        # Runtime imports
        from .base import BaseMigrationAdapter, SyncMigrationAdapter, AsyncMigrationAdapter
        from .protocols import MigrationProtocol, AsyncMigrationProtocol
        from .exceptions import (
            MigrationError, MigrationInitError, MigrationCreationError,
            MigrationUpgradeError, MigrationDowngradeError, MigrationNotFoundError
        )
        from .registry import MigrationRegistry
    except ImportError:
        # Import error handling
        from ..utils.dependencies import check_migrations_dependencies
        
        def __getattr__(name):
            check_migrations_dependencies()
            raise ImportError(f"Cannot import {name} because dependencies are missing")

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
    "MigrationRegistry"
]

# Optional imports based on available dependencies
if find_spec("sqlalchemy") is not None and find_spec("alembic") is not None:
    try:
        from .sql.alembic_adapter import AlembicAdapter, AsyncAlembicAdapter
        __all__.extend(["AlembicAdapter", "AsyncAlembicAdapter"])
    except ImportError:
        pass
