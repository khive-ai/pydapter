"""
pydapter.migrations.sql.alembic_adapter - Alembic migration adapter implementation.
"""

import os
import shutil
import tempfile
from typing import Any, ClassVar, Dict, List, Optional, Tuple, Union

import sqlalchemy as sa
from alembic import command, config
from alembic.runtime import environment
from alembic.script import ScriptDirectory
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

from pydapter.migrations.base import SyncMigrationAdapter, AsyncMigrationAdapter
from pydapter.migrations.exceptions import (
    MigrationError,
    MigrationInitError,
    MigrationCreationError,
    MigrationUpgradeError,
    MigrationDowngradeError,
    MigrationNotFoundError,
)


class AlembicMigrationAdapter(SyncMigrationAdapter):
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
                    directory=directory
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
                original_error=str(exc)
            ) from exc
    
    @classmethod
    def create_migration(cls, message: str, autogenerate: bool = True, **kwargs) -> str:
        """
        Create a new migration.
        
        Args:
            message: Description of the migration
            autogenerate: Whether to auto-generate the migration based on model changes
            **kwargs: Additional adapter-specific arguments
                directory: Path to the migration directory
                connection_string: Database connection string
                models_module: Optional module containing SQLAlchemy models
                
        Returns:
            The revision identifier of the created migration
        """
        try:
            # Get the migration directory
            directory = kwargs.get("directory")
            if not directory:
                raise MigrationCreationError(
                    "Migration directory is required for creating migrations",
                    message_text=message
                )
            
            # Create a new instance with the provided connection string
            connection_string = kwargs.get("connection_string")
            if not connection_string:
                raise MigrationCreationError(
                    "Connection string is required for creating migrations",
                    message_text=message,
                    directory=directory
                )
            
            adapter = cls(connection_string, kwargs.get("models_module"))
            
            # Load the Alembic configuration
            adapter.alembic_cfg = config.Config(os.path.join(directory, "alembic.ini"))
            adapter.alembic_cfg.set_main_option("script_location", directory)
            adapter.alembic_cfg.set_main_option("sqlalchemy.url", connection_string)
            
            # Create the migration
            revision = command.revision(
                adapter.alembic_cfg,
                message=message,
                autogenerate=autogenerate
            )
            
            return revision.revision
            
        except Exception as exc:
            if isinstance(exc, MigrationError):
                raise
            raise MigrationCreationError(
                f"Failed to create migration: {str(exc)}",
                message_text=message,
                autogenerate=autogenerate,
                original_error=str(exc)
            ) from exc
    
    @classmethod
    def upgrade(cls, revision: str = "head", **kwargs) -> None:
        """
        Upgrade to the specified revision.
        
        Args:
            revision: The target revision to upgrade to (default: "head")
            **kwargs: Additional adapter-specific arguments
                directory: Path to the migration directory
                connection_string: Database connection string
                sql: Whether to generate SQL instead of executing it
                tag: Optional tag to apply to the migration
        """
        try:
            # Get the migration directory
            directory = kwargs.get("directory")
            if not directory:
                raise MigrationUpgradeError(
                    "Migration directory is required for upgrading migrations",
                    revision=revision
                )
            
            # Create a new instance with the provided connection string
            connection_string = kwargs.get("connection_string")
            if not connection_string:
                raise MigrationUpgradeError(
                    "Connection string is required for upgrading migrations",
                    revision=revision,
                    directory=directory
                )
            
            adapter = cls(connection_string)
            
            # Load the Alembic configuration
            adapter.alembic_cfg = config.Config(os.path.join(directory, "alembic.ini"))
            adapter.alembic_cfg.set_main_option("script_location", directory)
            adapter.alembic_cfg.set_main_option("sqlalchemy.url", connection_string)
            
            # Upgrade to the specified revision
            sql = kwargs.get("sql", False)
            tag = kwargs.get("tag")
            command.upgrade(adapter.alembic_cfg, revision, sql=sql, tag=tag)
            
        except Exception as exc:
            if isinstance(exc, MigrationError):
                raise
            raise MigrationUpgradeError(
                f"Failed to upgrade to revision '{revision}': {str(exc)}",
                revision=revision,
                original_error=str(exc)
            ) from exc
    
    @classmethod
    def downgrade(cls, revision: str, **kwargs) -> None:
        """
        Downgrade to the specified revision.
        
        Args:
            revision: The target revision to downgrade to
            **kwargs: Additional adapter-specific arguments
                directory: Path to the migration directory
                connection_string: Database connection string
                sql: Whether to generate SQL instead of executing it
                tag: Optional tag to apply to the migration
        """
        try:
            # Get the migration directory
            directory = kwargs.get("directory")
            if not directory:
                raise MigrationDowngradeError(
                    "Migration directory is required for downgrading migrations",
                    revision=revision
                )
            
            # Create a new instance with the provided connection string
            connection_string = kwargs.get("connection_string")
            if not connection_string:
                raise MigrationDowngradeError(
                    "Connection string is required for downgrading migrations",
                    revision=revision,
                    directory=directory
                )
            
            adapter = cls(connection_string)
            
            # Load the Alembic configuration
            adapter.alembic_cfg = config.Config(os.path.join(directory, "alembic.ini"))
            adapter.alembic_cfg.set_main_option("script_location", directory)
            adapter.alembic_cfg.set_main_option("sqlalchemy.url", connection_string)
            
            # Downgrade to the specified revision
            sql = kwargs.get("sql", False)
            tag = kwargs.get("tag")
            command.downgrade(adapter.alembic_cfg, revision, sql=sql, tag=tag)
            
        except Exception as exc:
            if isinstance(exc, MigrationError):
                raise
            raise MigrationDowngradeError(
                f"Failed to downgrade to revision '{revision}': {str(exc)}",
                revision=revision,
                original_error=str(exc)
            ) from exc
    
    @classmethod
    def get_current_revision(cls, **kwargs) -> Optional[str]:
        """
        Get the current migration revision.
        
        Args:
            **kwargs: Additional adapter-specific arguments
                directory: Path to the migration directory
                connection_string: Database connection string
                
        Returns:
            The current revision identifier, or None if no migrations have been applied
        """
        try:
            # Get the migration directory
            directory = kwargs.get("directory")
            if not directory:
                raise MigrationError(
                    "Migration directory is required for getting current revision"
                )
            
            # Create a new instance with the provided connection string
            connection_string = kwargs.get("connection_string")
            if not connection_string:
                raise MigrationError(
                    "Connection string is required for getting current revision",
                    directory=directory
                )
            
            adapter = cls(connection_string)
            
            # Load the Alembic configuration
            adapter.alembic_cfg = config.Config(os.path.join(directory, "alembic.ini"))
            adapter.alembic_cfg.set_main_option("script_location", directory)
            adapter.alembic_cfg.set_main_option("sqlalchemy.url", connection_string)
            
            # Get the current revision
            script = ScriptDirectory.from_config(adapter.alembic_cfg)
            with adapter.engine.connect() as conn:
                context = environment.EnvironmentContext(
                    adapter.alembic_cfg,
                    script
                )
                context.configure(connection=conn)
                # Get the current revision from the database
                return script.get_current_head()
            
        except Exception as exc:
            if isinstance(exc, MigrationError):
                raise
            raise MigrationError(
                f"Failed to get current revision: {str(exc)}",
                original_error=str(exc)
            ) from exc
    
    @classmethod
    def get_migration_history(cls, **kwargs) -> List[Dict[str, Any]]:
        """
        Get the migration history.
        
        Args:
            **kwargs: Additional adapter-specific arguments
                directory: Path to the migration directory
                
        Returns:
            A list of dictionaries containing migration information
        """
        try:
            # Get the migration directory
            directory = kwargs.get("directory")
            if not directory:
                raise MigrationError(
                    "Migration directory is required for getting migration history"
                )
            
            # Load the Alembic configuration
            alembic_cfg = config.Config(os.path.join(directory, "alembic.ini"))
            alembic_cfg.set_main_option("script_location", directory)
            
            # Get the migration history
            script = ScriptDirectory.from_config(alembic_cfg)
            history = []
            for sc in script.walk_revisions():
                # Extract available attributes from the revision
                revision_data = {
                    "revision": sc.revision,
                    "down_revision": sc.down_revision,
                }
                
                # Add optional attributes if they exist
                if hasattr(sc, "message"):
                    revision_data["message"] = sc.message
                elif hasattr(sc, "doc"):
                    revision_data["message"] = sc.doc
                else:
                    revision_data["message"] = "No message available"
                    
                if hasattr(sc, "created_date") and sc.created_date:
                    revision_data["created_date"] = sc.created_date.isoformat()
                else:
                    revision_data["created_date"] = None
                    
                history.append(revision_data)
                
            return history
            
        except Exception as exc:
            if isinstance(exc, MigrationError):
                raise
            raise MigrationError(
                f"Failed to get migration history: {str(exc)}",
                original_error=str(exc)
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
        with open(env_path, "r") as f:
            env_content = f.read()
        
        # Update the target_metadata
        if "target_metadata = None" in env_content:
            # Import the models module
            import_statement = f"from {self.models_module.__name__} import Base\n"
            env_content = env_content.replace(
                "from alembic import context",
                "from alembic import context\n" + import_statement
            )
            
            # Update the target_metadata
            env_content = env_content.replace(
                "target_metadata = None",
                "target_metadata = Base.metadata"
            )
            
            # Write the updated env.py file
            with open(env_path, "w") as f:
                f.write(env_content)


class AsyncAlembicMigrationAdapter(AsyncMigrationAdapter):
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
    
    @classmethod
    async def init_migrations(cls, directory: str, **kwargs) -> None:
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
                    directory=directory
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
                await adapter._update_env_py_async(env_path)
            
            adapter._migrations_dir = directory
            adapter._initialized = True
            
        except Exception as exc:
            if isinstance(exc, MigrationError):
                raise
            raise MigrationInitError(
                f"Failed to initialize Alembic migrations: {str(exc)}",
                directory=directory,
                original_error=str(exc)
            ) from exc
    
    @classmethod
    async def create_migration(cls, message: str, autogenerate: bool = True, **kwargs) -> str:
        """
        Create a new migration.
        
        Args:
            message: Description of the migration
            autogenerate: Whether to auto-generate the migration based on model changes
            **kwargs: Additional adapter-specific arguments
                directory: Path to the migration directory
                connection_string: Database connection string
                models_module: Optional module containing SQLAlchemy models
                
        Returns:
            The revision identifier of the created migration
        """
        try:
            # Get the migration directory
            directory = kwargs.get("directory")
            if not directory:
                raise MigrationCreationError(
                    "Migration directory is required for creating migrations",
                    message_text=message
                )
            
            # Create a new instance with the provided connection string
            connection_string = kwargs.get("connection_string")
            if not connection_string:
                raise MigrationCreationError(
                    "Connection string is required for creating migrations",
                    message_text=message,
                    directory=directory
                )
            
            adapter = cls(connection_string, kwargs.get("models_module"))
            
            # Load the Alembic configuration
            adapter.alembic_cfg = config.Config(os.path.join(directory, "alembic.ini"))
            adapter.alembic_cfg.set_main_option("script_location", directory)
            adapter.alembic_cfg.set_main_option("sqlalchemy.url", connection_string)
            
            # Create the migration
            if autogenerate:
                async with adapter.engine.begin() as conn:
                    revision = await conn.run_sync(
                        lambda sync_conn: cls._create_migration_sync(
                            adapter.alembic_cfg, sync_conn, message, autogenerate
                        )
                    )
                    return revision
            else:
                # For non-autogenerated migrations, we don't need a connection
                revision = cls._create_migration_sync(
                    adapter.alembic_cfg, None, message, autogenerate
                )
                return revision
            
        except Exception as exc:
            if isinstance(exc, MigrationError):
                raise
            raise MigrationCreationError(
                f"Failed to create migration: {str(exc)}",
                message_text=message,
                autogenerate=autogenerate,
                original_error=str(exc)
            ) from exc
    
    @classmethod
    async def upgrade(cls, revision: str = "head", **kwargs) -> None:
        """
        Upgrade to the specified revision.
        
        Args:
            revision: The target revision to upgrade to (default: "head")
            **kwargs: Additional adapter-specific arguments
                directory: Path to the migration directory
                connection_string: Database connection string
                sql: Whether to generate SQL instead of executing it
                tag: Optional tag to apply to the migration
        """
        try:
            # Get the migration directory
            directory = kwargs.get("directory")
            if not directory:
                raise MigrationUpgradeError(
                    "Migration directory is required for upgrading migrations",
                    revision=revision
                )
            
            # Create a new instance with the provided connection string
            connection_string = kwargs.get("connection_string")
            if not connection_string:
                raise MigrationUpgradeError(
                    "Connection string is required for upgrading migrations",
                    revision=revision,
                    directory=directory
                )
            
            adapter = cls(connection_string)
            
            # Load the Alembic configuration
            adapter.alembic_cfg = config.Config(os.path.join(directory, "alembic.ini"))
            adapter.alembic_cfg.set_main_option("script_location", directory)
            adapter.alembic_cfg.set_main_option("sqlalchemy.url", connection_string)
            
            # Upgrade to the specified revision
            sql = kwargs.get("sql", False)
            tag = kwargs.get("tag")
            
            async with adapter.engine.begin() as conn:
                await conn.run_sync(
                    lambda sync_conn: cls._upgrade_sync(
                        adapter.alembic_cfg, sync_conn, revision, sql, tag
                    )
                )
            
        except Exception as exc:
            if isinstance(exc, MigrationError):
                raise
            raise MigrationUpgradeError(
                f"Failed to upgrade to revision '{revision}': {str(exc)}",
                revision=revision,
                original_error=str(exc)
            ) from exc
    
    @classmethod
    async def downgrade(cls, revision: str, **kwargs) -> None:
        """
        Downgrade to the specified revision.
        
        Args:
            revision: The target revision to downgrade to
            **kwargs: Additional adapter-specific arguments
                directory: Path to the migration directory
                connection_string: Database connection string
                sql: Whether to generate SQL instead of executing it
                tag: Optional tag to apply to the migration
        """
        try:
            # Get the migration directory
            directory = kwargs.get("directory")
            if not directory:
                raise MigrationDowngradeError(
                    "Migration directory is required for downgrading migrations",
                    revision=revision
                )
            
            # Create a new instance with the provided connection string
            connection_string = kwargs.get("connection_string")
            if not connection_string:
                raise MigrationDowngradeError(
                    "Connection string is required for downgrading migrations",
                    revision=revision,
                    directory=directory
                )
            
            adapter = cls(connection_string)
            
            # Load the Alembic configuration
            adapter.alembic_cfg = config.Config(os.path.join(directory, "alembic.ini"))
            adapter.alembic_cfg.set_main_option("script_location", directory)
            adapter.alembic_cfg.set_main_option("sqlalchemy.url", connection_string)
            
            # Downgrade to the specified revision
            sql = kwargs.get("sql", False)
            tag = kwargs.get("tag")
            
            async with adapter.engine.begin() as conn:
                await conn.run_sync(
                    lambda sync_conn: cls._downgrade_sync(
                        adapter.alembic_cfg, sync_conn, revision, sql, tag
                    )
                )
            
        except Exception as exc:
            if isinstance(exc, MigrationError):
                raise
            raise MigrationDowngradeError(
                f"Failed to downgrade to revision '{revision}': {str(exc)}",
                revision=revision,
                original_error=str(exc)
            ) from exc
    
    @classmethod
    async def get_current_revision(cls, **kwargs) -> Optional[str]:
        """
        Get the current migration revision.
        
        Args:
            **kwargs: Additional adapter-specific arguments
                directory: Path to the migration directory
                connection_string: Database connection string
                
        Returns:
            The current revision identifier, or None if no migrations have been applied
        """
        try:
            # Get the migration directory
            directory = kwargs.get("directory")
            if not directory:
                raise MigrationError(
                    "Migration directory is required for getting current revision"
                )
            
            # Create a new instance with the provided connection string
            connection_string = kwargs.get("connection_string")
            if not connection_string:
                raise MigrationError(
                    "Connection string is required for getting current revision",
                    directory=directory
                )
            
            adapter = cls(connection_string)
            
            # Load the Alembic configuration
            adapter.alembic_cfg = config.Config(os.path.join(directory, "alembic.ini"))
            adapter.alembic_cfg.set_main_option("script_location", directory)
            adapter.alembic_cfg.set_main_option("sqlalchemy.url", connection_string)
            
            # Get the current revision
            async with adapter.engine.begin() as conn:
                return await conn.run_sync(
                    lambda sync_conn: cls._get_current_revision_sync(
                        adapter.alembic_cfg, sync_conn
                    )
                )
            
        except Exception as exc:
            if isinstance(exc, MigrationError):
                raise
            raise MigrationError(
                f"Failed to get current revision: {str(exc)}",
                original_error=str(exc)
            ) from exc
    
    @classmethod
    async def get_migration_history(cls, **kwargs) -> List[Dict[str, Any]]:
        """
        Get the migration history.
        
        Args:
            **kwargs: Additional adapter-specific arguments
                directory: Path to the migration directory
                
        Returns:
            A list of dictionaries containing migration information
        """
        try:
            # Get the migration directory
            directory = kwargs.get("directory")
            if not directory:
                raise MigrationError(
                    "Migration directory is required for getting migration history"
                )
            
            # Load the Alembic configuration
            alembic_cfg = config.Config(os.path.join(directory, "alembic.ini"))
            alembic_cfg.set_main_option("script_location", directory)
            
            # Get the migration history
            script = ScriptDirectory.from_config(alembic_cfg)
            history = []
            for sc in script.walk_revisions():
                # Extract available attributes from the revision
                revision_data = {
                    "revision": sc.revision,
                    "down_revision": sc.down_revision,
                }
                
                # Add optional attributes if they exist
                if hasattr(sc, "message"):
                    revision_data["message"] = sc.message
                elif hasattr(sc, "doc"):
                    revision_data["message"] = sc.doc
                else:
                    revision_data["message"] = "No message available"
                    
                if hasattr(sc, "created_date") and sc.created_date:
                    revision_data["created_date"] = sc.created_date.isoformat()
                else:
                    revision_data["created_date"] = None
                    
                history.append(revision_data)
                
            return history
            
        except Exception as exc:
            if isinstance(exc, MigrationError):
                raise
            raise MigrationError(
                f"Failed to get migration history: {str(exc)}",
                original_error=str(exc)
            ) from exc
    
    async def _update_env_py_async(self, env_path: str) -> None:
        """
        Update the env.py file to use the models_module for autogeneration.
        
        Args:
            env_path: Path to the env.py file
        """
        if not os.path.exists(env_path):
            return
        
        # Read the env.py file
        with open(env_path, "r") as f:
            env_content = f.read()
        
        # Update the target_metadata
        if "target_metadata = None" in env_content:
            # Import the models module
            import_statement = f"from {self.models_module.__name__} import Base\n"
            env_content = env_content.replace(
                "from alembic import context",
                "from alembic import context\n" + import_statement
            )
            
            # Update the target_metadata
            env_content = env_content.replace(
                "target_metadata = None",
                "target_metadata = Base.metadata"
            )
            
            # Write the updated env.py file
            with open(env_path, "w") as f:
                f.write(env_content)
    
    @staticmethod
    def _create_migration_sync(
        alembic_cfg: config.Config,
        sync_conn: Optional[Connection],
        message: str,
        autogenerate: bool
    ) -> str:
        """
        Synchronous implementation for create_migration.
        
        Args:
            alembic_cfg: Alembic configuration
            sync_conn: SQLAlchemy connection
            message: Migration message
            autogenerate: Whether to auto-generate the migration
            
        Returns:
            The revision identifier of the created migration
        """
        if autogenerate and sync_conn is not None:
            # Configure the context with the connection
            script = ScriptDirectory.from_config(alembic_cfg)
            context = environment.EnvironmentContext(
                alembic_cfg,
                script
            )
            context.configure(connection=sync_conn, target_metadata=None)
            
            # Create the migration
            with context.begin_transaction():
                revision = command.revision(
                    alembic_cfg,
                    message=message,
                    autogenerate=autogenerate
                )
                return revision.revision
        else:
            # Create the migration without autogeneration
            revision = command.revision(
                alembic_cfg,
                message=message,
                autogenerate=False
            )
            return revision.revision
    
    @staticmethod
    def _upgrade_sync(
        alembic_cfg: config.Config,
        sync_conn: Connection,
        revision: str,
        sql: bool,
        tag: Optional[str]
    ) -> None:
        """
        Synchronous implementation for upgrade.
        
        Args:
            alembic_cfg: Alembic configuration
            sync_conn: SQLAlchemy connection
            revision: Target revision
            sql: Whether to generate SQL
            tag: Optional tag
        """
        # Configure the context with the connection
        script = ScriptDirectory.from_config(alembic_cfg)
        context = environment.EnvironmentContext(
            alembic_cfg,
            script
        )
        context.configure(connection=sync_conn, target_metadata=None)
        
        # Upgrade to the specified revision
        with context.begin_transaction():
            # Skip running the env.py file directly, as it might cause issues
            # with the context.config attribute
            command.upgrade(alembic_cfg, revision, sql=sql, tag=tag)
    
    @staticmethod
    def _downgrade_sync(
        alembic_cfg: config.Config,
        sync_conn: Connection,
        revision: str,
        sql: bool,
        tag: Optional[str]
    ) -> None:
        """
        Synchronous implementation for downgrade.
        
        Args:
            alembic_cfg: Alembic configuration
            sync_conn: SQLAlchemy connection
            revision: Target revision
            sql: Whether to generate SQL
            tag: Optional tag
        """
        # Configure the context with the connection
        script = ScriptDirectory.from_config(alembic_cfg)
        context = environment.EnvironmentContext(
            alembic_cfg,
            script
        )
        context.configure(connection=sync_conn, target_metadata=None)
        
        # Downgrade to the specified revision
        with context.begin_transaction():
            # Skip running the env.py file directly, as it might cause issues
            # with the context.config attribute
            command.downgrade(alembic_cfg, revision, sql=sql, tag=tag)
    
    @staticmethod
    def _get_current_revision_sync(
        alembic_cfg: config.Config,
        sync_conn: Connection
    ) -> Optional[str]:
        """
        Synchronous implementation for get_current_revision.
        
        Args:
            alembic_cfg: Alembic configuration
            sync_conn: SQLAlchemy connection
            
        Returns:
            The current revision identifier, or None if no migrations have been applied
        """
        # Configure the context with the connection
        script = ScriptDirectory.from_config(alembic_cfg)
        context = environment.EnvironmentContext(
            alembic_cfg,
            script
        )
        context.configure(connection=sync_conn, target_metadata=None)
        
        # Get the current revision from the database
        return script.get_current_head()