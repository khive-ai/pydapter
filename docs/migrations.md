# Migrations Module

The Migrations module provides a framework for managing database schema changes
in a controlled, versioned manner. It follows pydapter's adapter pattern
philosophy, offering both synchronous and asynchronous interfaces for different
database backends.

## Installation

The Migrations module is available as an optional dependency with different
components:

```bash
# Core migrations functionality (minimal dependencies)
pip install pydapter[migrations-core]

# SQL migrations with Alembic support
pip install pydapter[migrations-sql]

# All migrations components
pip install pydapter[migrations]

# Migrations with protocols support
pip install pydapter[migrations-all]
```

## Key Concepts

### Migration Adapters

Migration adapters implement the migration protocols and provide concrete
functionality for specific database backends. The base module includes:

- `BaseMigrationAdapter`: Abstract base class for all migration adapters
- `SyncMigrationAdapter`: Base class for synchronous migration adapters
- `AsyncMigrationAdapter`: Base class for asynchronous migration adapters

### Migration Protocols

The module defines protocols that specify the interface for migration
operations:

- `MigrationProtocol`: Protocol for synchronous migration operations
- `AsyncMigrationProtocol`: Protocol for asynchronous migration operations

### SQL Migrations with Alembic

The SQL migrations implementation uses
[Alembic](https://alembic.sqlalchemy.org/), a database migration tool for
SQLAlchemy. It provides:

- `AlembicAdapter`: Synchronous Alembic-based migration adapter
- `AsyncAlembicAdapter`: Asynchronous Alembic-based migration adapter

## Basic Usage

### Initializing Migrations

Before you can create and apply migrations, you need to initialize the migration
environment:

```python
from pydapter.migrations import AlembicAdapter
import mymodels  # Module containing your SQLAlchemy models

# Initialize migrations
AlembicAdapter.init_migrations(
    directory="migrations",
    connection_string="postgresql://user:pass@localhost/mydb",
    models_module=mymodels
)
```

This creates the necessary directory structure and configuration files for
Alembic.

### Creating Migrations

You can create migrations manually or automatically based on model changes:

```python
# Create a migration with auto-generation based on model changes
revision = AlembicAdapter.create_migration(
    message="Add users table",
    autogenerate=True,
    directory="migrations",
    connection_string="postgresql://user:pass@localhost/mydb"
)
print(f"Created migration: {revision}")
```

The `autogenerate` parameter tells Alembic to compare your models with the
current database schema and generate the necessary changes.

### Applying Migrations

To apply migrations and update your database schema:

```python
# Upgrade to the latest version
AlembicAdapter.upgrade(
    revision="head",  # "head" means the latest version
    directory="migrations",
    connection_string="postgresql://user:pass@localhost/mydb"
)
```

### Reverting Migrations

If you need to revert to a previous version:

```python
# Downgrade to a specific revision
AlembicAdapter.downgrade(
    revision="ae1027a6acf",  # Specific revision identifier
    directory="migrations",
    connection_string="postgresql://user:pass@localhost/mydb"
)
```

### Checking Migration Status

You can check the current migration status:

```python
# Get the current revision
current = AlembicAdapter.get_current_revision(
    directory="migrations",
    connection_string="postgresql://user:pass@localhost/mydb"
)
print(f"Current revision: {current}")

# Get the full migration history
history = AlembicAdapter.get_migration_history(
    directory="migrations",
    connection_string="postgresql://user:pass@localhost/mydb"
)
for migration in history:
    print(f"{migration['revision']}: {migration['description']}")
```

## Asynchronous Migrations

For applications using asynchronous database connections, you can use the async
migration adapter:

```python
from pydapter.migrations import AsyncAlembicAdapter
import mymodels

# Initialize migrations
await AsyncAlembicAdapter.init_migrations(
    directory="migrations",
    connection_string="postgresql+asyncpg://user:pass@localhost/mydb",
    models_module=mymodels
)

# Create a migration
revision = await AsyncAlembicAdapter.create_migration(
    message="Add users table",
    autogenerate=True,
    directory="migrations",
    connection_string="postgresql+asyncpg://user:pass@localhost/mydb"
)

# Apply migrations
await AsyncAlembicAdapter.upgrade(
    revision="head",
    directory="migrations",
    connection_string="postgresql+asyncpg://user:pass@localhost/mydb"
)
```

## Error Handling

The migrations module provides a comprehensive error hierarchy:

- `MigrationError`: Base exception for all migration errors
- `MigrationInitError`: Raised when initialization fails
- `MigrationCreationError`: Raised when migration creation fails
- `MigrationUpgradeError`: Raised when upgrade fails
- `MigrationDowngradeError`: Raised when downgrade fails
- `MigrationNotFoundError`: Raised when a specified revision is not found

Example of handling migration errors:

```python
from pydapter.migrations import AlembicAdapter, MigrationError, MigrationUpgradeError

try:
    AlembicAdapter.upgrade(
        revision="head",
        directory="migrations",
        connection_string="postgresql://user:pass@localhost/mydb"
    )
except MigrationUpgradeError as e:
    print(f"Failed to upgrade: {e}")
    # Handle specific upgrade error
except MigrationError as e:
    print(f"Migration error: {e}")
    # Handle general migration error
```

## Advanced Usage

### Custom Migration Scripts

While auto-generated migrations work for many cases, you might need to write
custom migration scripts for complex changes:

1. Create a migration without auto-generation:

```python
revision = AlembicAdapter.create_migration(
    message="Custom data migration",
    autogenerate=False,
    directory="migrations",
    connection_string="postgresql://user:pass@localhost/mydb"
)
```

1. Edit the generated script in the `migrations/versions/` directory:

```python
"""Custom data migration

Revision ID: ae1027a6acf
Revises: 1a2b3c4d5e6f
Create Date: 2025-05-16 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'ae1027a6acf'
down_revision = '1a2b3c4d5e6f'
branch_labels = None
depends_on = None

def upgrade():
    # Custom upgrade operations
    op.execute("""
        UPDATE users
        SET status = 'active'
        WHERE status = 'pending' AND created_at < NOW() - INTERVAL '7 days'
    """)

def downgrade():
    # Custom downgrade operations
    # Note: Data migrations are often not reversible
    pass
```

### Working with Multiple Databases

If your application uses multiple databases, you can create separate migration
directories for each:

```python
# Initialize migrations for the main database
AlembicAdapter.init_migrations(
    directory="migrations/main",
    connection_string="postgresql://user:pass@localhost/main_db",
    models_module=main_models
)

# Initialize migrations for the analytics database
AlembicAdapter.init_migrations(
    directory="migrations/analytics",
    connection_string="postgresql://user:pass@localhost/analytics_db",
    models_module=analytics_models
)
```

Then apply migrations to each database separately:

```python
# Upgrade main database
AlembicAdapter.upgrade(
    revision="head",
    directory="migrations/main",
    connection_string="postgresql://user:pass@localhost/main_db"
)

# Upgrade analytics database
AlembicAdapter.upgrade(
    revision="head",
    directory="migrations/analytics",
    connection_string="postgresql://user:pass@localhost/analytics_db"
)
```

### Integration with SQLAlchemy Models

The migrations module works best with SQLAlchemy models that follow the
declarative base pattern:

```python
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)

# Later, when initializing migrations:
AlembicAdapter.init_migrations(
    directory="migrations",
    connection_string="postgresql://user:pass@localhost/mydb",
    models_module=sys.modules[__name__]  # Current module containing models
)
```

## Best Practices

### Migration Workflow

Follow these best practices for a smooth migration workflow:

1. **Always back up your database before applying migrations**
2. **Test migrations in a development environment first**
3. **Keep migrations small and focused on specific changes**
4. **Include descriptive messages for each migration**
5. **Ensure both upgrade and downgrade functions are implemented**
6. **Use transactions for data safety**

### Organizing Migrations

For larger projects, consider these organizational tips:

1. **Use a consistent naming convention for migration files**
2. **Group related migrations in branches when appropriate**
3. **Document complex migrations with comments**
4. **Include the related issue or ticket number in migration messages**

### Deployment Considerations

When deploying migrations to production:

1. **Include migrations in your CI/CD pipeline**
2. **Apply migrations during maintenance windows when possible**
3. **Have a rollback plan for each migration**
4. **Monitor database performance during and after migrations**
5. **Consider using a separate deployment step for migrations**

## Extending the Migrations Framework

You can extend the migrations framework by creating custom adapters for other
database systems:

```python
from pydapter.migrations.base import SyncMigrationAdapter
from typing import ClassVar, Optional, List, Dict, Any

class CustomDatabaseAdapter(SyncMigrationAdapter):
    """Custom migration adapter for a specific database system."""

    migration_key: ClassVar[str] = "custom_db"

    @classmethod
    def init_migrations(cls, directory: str, **kwargs) -> None:
        # Implementation for initializing migrations
        pass

    @classmethod
    def create_migration(cls, message: str, autogenerate: bool = True, **kwargs) -> str:
        # Implementation for creating migrations
        pass

    @classmethod
    def upgrade(cls, revision: str = "head", **kwargs) -> None:
        # Implementation for upgrading
        pass

    @classmethod
    def downgrade(cls, revision: str, **kwargs) -> None:
        # Implementation for downgrading
        pass

    @classmethod
    def get_current_revision(cls, **kwargs) -> Optional[str]:
        # Implementation for getting current revision
        pass

    @classmethod
    def get_migration_history(cls, **kwargs) -> List[Dict[str, Any]]:
        # Implementation for getting migration history
        pass
```

## Troubleshooting

### Common Issues

1. **Missing dependencies**:

   ```text
   ImportError: The 'migrations-sql' feature requires the 'sqlalchemy' package.
   ```

   Solution: Install the required dependencies with
   `pip install pydapter[migrations-sql]`

2. **Alembic command not found**:

   ```text
   ModuleNotFoundError: No module named 'alembic'
   ```

   Solution: Install Alembic with `pip install alembic`

3. **Autogeneration not detecting changes**: Solution: Ensure your models are
   imported and accessible in the environment where migrations are created

4. **Conflicts between migrations**: Solution: Ensure you're working with the
   latest revision before creating new migrations

### Getting Help

If you encounter issues with migrations, check:

1. The Alembic documentation: https://alembic.sqlalchemy.org/
2. SQLAlchemy documentation: https://docs.sqlalchemy.org/
3. pydapter GitHub issues: https://github.com/yourusername/pydapter/issues
