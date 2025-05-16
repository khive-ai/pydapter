from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Type checking imports
    from .alembic_adapter import AlembicAdapter, AsyncAlembicAdapter
else:
    try:
        # Runtime imports
        from .alembic_adapter import AlembicAdapter, AsyncAlembicAdapter

        __all__ = ["AlembicAdapter", "AsyncAlembicAdapter"]
    except ImportError:
        # Import error handling
        from ...utils.dependencies import check_migrations_sql_dependencies

        def __getattr__(name):
            check_migrations_sql_dependencies()
            raise ImportError(f"Cannot import {name} because dependencies are missing")

        __all__ = []
