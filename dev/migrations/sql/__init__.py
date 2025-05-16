import warnings

warnings.warn(
    "Importing from dev.migrations.sql is deprecated and will be removed in a future version. "
    "Please use pydapter.migrations.sql instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export from new location
try:
    from pydapter.migrations.sql import *
except ImportError:
    # If the new module isn't available, fall back to local implementation
    try:
        from .alembic_adapter import AlembicAdapter, AsyncAlembicAdapter

        __all__ = ["AlembicAdapter", "AsyncAlembicAdapter"]
    except ImportError:
        __all__ = []
