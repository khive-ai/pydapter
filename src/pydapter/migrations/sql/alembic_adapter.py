"""
pydapter.migrations.sql.alembic_adapter - Alembic migration adapter implementation.
"""

import os
import shutil
from typing import Any, ClassVar

import sqlalchemy as sa
from alembic import command, config
from sqlalchemy.ext.asyncio import create_async_engine

from pydapter.migrations.base import AsyncMigrationAdapter, SyncMigrationAdapter
from pydapter.migrations.exceptions import MigrationError, MigrationInitError


class AlembicAdapter(SyncMigrationAdapter):
    """Alembic implementation of the MigrationAdapter interface."""

    migration_key: ClassVar[str] = "alembic"

    def __init__(self, connection_string: str, models_module: Any = None):
        """
        Initialize the Alembic migration adapter.

        Args:
            connection_string: Database connection string
            models_module: Optional module containing SQLAlchemy models
        """
        super().__init__(connection_string, models_module)
        self.engine = sa.create_engine(connection_string)
        self.alembic_cfg = None

    @classmethod
    def init_migrations(cls, directory: str, **kwargs) -> None:
        """
        Initialize migration environment in the specified directory.

        Args:
            directory: Path to the directory where migrations will be stored
            **kwargs: Additional adapter-specific arguments
                connection_string: Database connection string
                models_module: Optional module containing SQLAlchemy models
                template: Optional template to use for migration environment
        """
        try:
            # Create a new instance with the provided connection string
            connection_string = kwargs.get("connection_string")
            if not connection_string:
                raise MigrationInitError(
                    "Connection string is required for Alembic initialization",
                    directory=directory,
                )

            adapter = cls(connection_string, kwargs.get("models_module"))

            # Check if the directory exists and is not empty
            force_clean = kwargs.get("force_clean", False)
            if os.path.exists(directory) and os.listdir(directory):
                if force_clean:
                    # If force_clean is specified, remove the directory and recreate it
                    shutil.rmtree(directory)
                    os.makedirs(directory)
            else:
                # Create the directory if it doesn't exist
                adapter._ensure_directory(directory)

            # Initialize Alembic directory structure
            template = kwargs.get("template", "generic")

            # Create a temporary config file
            ini_path = os.path.join(directory, "alembic.ini")
            with open(ini_path, "w") as f:
                f.write(f"""
[alembic]
script_location = {directory}
sqlalchemy.url = {connection_string}

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
""")

            # Initialize Alembic in the specified directory
            adapter.alembic_cfg = config.Config(ini_path)
            adapter.alembic_cfg.set_main_option("script_location", directory)
            adapter.alembic_cfg.set_main_option("sqlalchemy.url", connection_string)

            # Initialize Alembic directory structure
            try:
                command.init(adapter.alembic_cfg, directory, template=template)
            except Exception as e:
                if "already exists and is not empty" in str(e) and force_clean:
                    # If the directory exists and is not empty, and force_clean is True,
                    # try to clean it up again and retry
                    shutil.rmtree(directory)
                    os.makedirs(directory)
                    command.init(adapter.alembic_cfg, directory, template=template)
                else:
                    raise

            # Update env.py to use the models_module for autogeneration if provided
            if adapter.models_module:
                env_path = os.path.join(directory, "env.py")
                adapter._update_env_py(env_path)

            adapter._migrations_dir = directory
            adapter._initialized = True

        except Exception as exc:
            if isinstance(exc, MigrationError):
                raise
            raise MigrationInitError(
                f"Failed to initialize Alembic migrations: {str(exc)}",
                directory=directory,
                original_error=str(exc),
            ) from exc

    def _update_env_py(self, env_path: str) -> None:
        """
        Update the env.py file to use the models_module for autogeneration.

        Args:
            env_path: Path to the env.py file
        """
        if not os.path.exists(env_path):
            return

        # Read the env.py file
        with open(env_path) as f:
            env_content = f.read()

        # Update the target_metadata
        if "target_metadata = None" in env_content:
            # Import the models module
            import_statement = f"from {self.models_module.__name__} import Base\n"
            env_content = env_content.replace(
                "from alembic import context",
                "from alembic import context\n" + import_statement,
            )

            # Update the target_metadata
            env_content = env_content.replace(
                "target_metadata = None", "target_metadata = Base.metadata"
            )

            # Write the updated env.py file
            with open(env_path, "w") as f:
                f.write(env_content)


class AsyncAlembicAdapter(AsyncMigrationAdapter):
    """Async implementation of the Alembic migration adapter."""

    migration_key: ClassVar[str] = "async_alembic"

    def __init__(self, connection_string: str, models_module: Any = None):
        """
        Initialize the async Alembic migration adapter.

        Args:
            connection_string: Database connection string
            models_module: Optional module containing SQLAlchemy models
        """
        super().__init__(connection_string, models_module)
        self.engine = create_async_engine(connection_string)
        self.alembic_cfg = None

    async def _update_env_py_async(self, env_path: str) -> None:
        """
        Update the env.py file to use the models_module for autogeneration.

        Args:
            env_path: Path to the env.py file
        """
        if not os.path.exists(env_path):
            return

        # Read the env.py file
        with open(env_path) as f:
            env_content = f.read()

        # Update the target_metadata
        if "target_metadata = None" in env_content:
            # Import the models module
            import_statement = f"from {self.models_module.__name__} import Base\n"
            env_content = env_content.replace(
                "from alembic import context",
                "from alembic import context\n" + import_statement,
            )

            # Update the target_metadata
            env_content = env_content.replace(
                "target_metadata = None", "target_metadata = Base.metadata"
            )

            # Write the updated env.py file
            with open(env_path, "w") as f:
                f.write(env_content)
