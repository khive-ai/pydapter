# Tutorial: Managing Database Schema Evolution with Migrations

This tutorial demonstrates how to use pydapter's migrations module to manage
database schema changes in a SQLAlchemy-based application. We'll create a simple
user management system and evolve its schema over time using migrations.

## Prerequisites

Before starting, ensure you have installed pydapter with the migrations-sql
extension:

```bash
pip install pydapter[migrations-sql]
```

This will install the required dependencies, including SQLAlchemy and Alembic.

## Step 1: Set Up the Project Structure

First, let's create a basic project structure:

```text
user_management/
├── migrations/        # Will be created by the migration tool
├── models.py          # SQLAlchemy models
├── database.py        # Database connection setup
└── main.py            # Application entry point
```

## Step 2: Define the Initial Database Models

Let's create our initial database models in `models.py`:

```python
# models.py
from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=func.now())
```

Next, let's set up the database connection in `database.py`:

```python
# database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Use SQLite for simplicity in this tutorial
DATABASE_URL = "sqlite:///./user_management.db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

## Step 3: Initialize Migrations

Now, let's initialize the migrations environment. Create a simple script in
`main.py`:

```python
# main.py
import os
from pydapter.migrations import AlembicAdapter
import models

def init_migrations():
    """Initialize the migrations environment."""
    os.makedirs("migrations", exist_ok=True)

    AlembicAdapter.init_migrations(
        directory="migrations",
        connection_string="sqlite:///./user_management.db",
        models_module=models
    )
    print("Migrations initialized successfully!")

if __name__ == "__main__":
    init_migrations()
```

Run this script to initialize the migrations environment:

```bash
python main.py
```

This will create the necessary directory structure and configuration files for
Alembic in the `migrations` directory.

## Step 4: Create the Initial Migration

Now, let's create our first migration to set up the initial database schema:

```python
# main.py (add this function)
def create_initial_migration():
    """Create the initial migration."""
    revision = AlembicAdapter.create_migration(
        message="Create users table",
        autogenerate=True,
        directory="migrations",
        connection_string="sqlite:///./user_management.db"
    )
    print(f"Created initial migration: {revision}")

if __name__ == "__main__":
    # init_migrations()  # Comment this out after first run
    create_initial_migration()
```

Run the script again to create the initial migration:

```bash
python main.py
```

This will create a new migration file in the `migrations/versions/` directory
with a unique revision ID.

## Step 5: Apply the Migration

Now, let's apply the migration to create the database schema:

```python
# main.py (add this function)
def apply_migrations():
    """Apply all pending migrations."""
    AlembicAdapter.upgrade(
        revision="head",
        directory="migrations",
        connection_string="sqlite:///./user_management.db"
    )
    print("Migrations applied successfully!")

if __name__ == "__main__":
    # init_migrations()  # Comment this out after first run
    # create_initial_migration()  # Comment this out after first run
    apply_migrations()
```

Run the script to apply the migration:

```bash
python main.py
```

This will create the `users` table in the database according to our model
definition.

## Step 6: Evolve the Schema

Now, let's evolve our schema by adding new fields to the `User` model:

```python
# models.py (updated)
from sqlalchemy import Column, Integer, String, DateTime, Boolean, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    full_name = Column(String(100))  # New field
    is_active = Column(Boolean, default=True)  # New field
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())  # New field
```

Now, let's create a new migration to reflect these changes:

```python
# main.py (add this function)
def create_schema_update_migration():
    """Create a migration for schema updates."""
    revision = AlembicAdapter.create_migration(
        message="Add user profile fields",
        autogenerate=True,
        directory="migrations",
        connection_string="sqlite:///./user_management.db"
    )
    print(f"Created schema update migration: {revision}")

if __name__ == "__main__":
    # init_migrations()  # Comment this out after first run
    # create_initial_migration()  # Comment this out after first run
    # apply_migrations()  # Comment this out after first run
    create_schema_update_migration()
```

Run the script to create the new migration:

```bash
python main.py
```

Then apply the migration:

```python
if __name__ == "__main__":
    # init_migrations()  # Comment this out after first run
    # create_initial_migration()  # Comment this out after first run
    # create_schema_update_migration()  # Comment this out after first run
    apply_migrations()
```

```bash
python main.py
```

## Step 7: Add a New Model

Let's add a new model to our application for user roles:

```python
# models.py (updated)
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    full_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Add relationship to roles
    roles = relationship("UserRole", back_populates="user")


class UserRole(Base):
    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role_name = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=func.now())

    # Add relationship to user
    user = relationship("User", back_populates="roles")
```

Now, let's create a migration for this new model:

```python
# main.py (add this function)
def create_roles_migration():
    """Create a migration for the roles model."""
    revision = AlembicAdapter.create_migration(
        message="Add user roles table",
        autogenerate=True,
        directory="migrations",
        connection_string="sqlite:///./user_management.db"
    )
    print(f"Created roles migration: {revision}")

if __name__ == "__main__":
    # init_migrations()  # Comment this out after first run
    # create_initial_migration()  # Comment this out after first run
    # apply_migrations()  # Comment this out after first run
    # create_schema_update_migration()  # Comment this out after first run
    create_roles_migration()
```

Run the script to create the new migration:

```bash
python main.py
```

Then apply the migration:

```python
if __name__ == "__main__":
    # init_migrations()  # Comment this out after first run
    # create_initial_migration()  # Comment this out after first run
    # create_schema_update_migration()  # Comment this out after first run
    # create_roles_migration()  # Comment this out after first run
    apply_migrations()
```

```bash
python main.py
```

## Step 8: Check Migration Status

Let's add functionality to check the current migration status:

```python
# main.py (add this function)
def check_migration_status():
    """Check the current migration status."""
    current = AlembicAdapter.get_current_revision(
        directory="migrations",
        connection_string="sqlite:///./user_management.db"
    )
    print(f"Current migration revision: {current}")

    history = AlembicAdapter.get_migration_history(
        directory="migrations",
        connection_string="sqlite:///./user_management.db"
    )
    print("\nMigration history:")
    for migration in history:
        print(f"- {migration['revision']}: {migration.get('description', 'No description')}")

if __name__ == "__main__":
    # init_migrations()  # Comment this out after first run
    # create_initial_migration()  # Comment this out after first run
    # apply_migrations()  # Comment this out after first run
    # create_schema_update_migration()  # Comment this out after first run
    # create_roles_migration()  # Comment this out after first run
    check_migration_status()
```

Run the script to check the migration status:

```bash
python main.py
```

## Step 9: Downgrade to a Previous Version

Sometimes you might need to revert to a previous version of your schema. Let's
add functionality to downgrade:

```python
# main.py (add this function)
def downgrade_migration(revision):
    """Downgrade to a specific revision."""
    AlembicAdapter.downgrade(
        revision=revision,
        directory="migrations",
        connection_string="sqlite:///./user_management.db"
    )
    print(f"Downgraded to revision: {revision}")

if __name__ == "__main__":
    # Get the second-to-last revision from history
    history = AlembicAdapter.get_migration_history(
        directory="migrations",
        connection_string="sqlite:///./user_management.db"
    )
    if len(history) >= 2:
        previous_revision = history[-2]['revision']
        downgrade_migration(previous_revision)
    else:
        print("Not enough migrations to downgrade")
```

Run the script to downgrade to the previous migration:

```bash
python main.py
```

## Step 10: Create a Custom Migration

Sometimes you need to create custom migrations that aren't just schema changes.
Let's create a data migration:

```python
# main.py (add this function)
def create_custom_migration():
    """Create a custom data migration."""
    revision = AlembicAdapter.create_migration(
        message="Add default admin user",
        autogenerate=False,  # Don't auto-generate from models
        directory="migrations",
        connection_string="sqlite:///./user_management.db"
    )
    print(f"Created custom migration: {revision}")
    print(f"Edit the migration file in migrations/versions/{revision}_add_default_admin_user.py")

if __name__ == "__main__":
    # init_migrations()  # Comment this out after first run
    # create_initial_migration()  # Comment this out after first run
    # apply_migrations()  # Comment this out after first run
    # create_schema_update_migration()  # Comment this out after first run
    # create_roles_migration()  # Comment this out after first run
    # check_migration_status()  # Comment this out after first run
    create_custom_migration()
```

Run the script to create the custom migration:

```bash
python main.py
```

Now, edit the generated migration file in `migrations/versions/` to add custom
SQL operations:

```python
"""Add default admin user

Revision ID: <your_revision_id>
Revises: <previous_revision_id>
Create Date: 2025-05-16 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '<your_revision_id>'
down_revision = '<previous_revision_id>'
branch_labels = None
depends_on = None

def upgrade():
    # Add a default admin user
    op.execute("""
    INSERT INTO users (username, email, full_name, is_active)
    VALUES ('admin', 'admin@example.com', 'System Administrator', 1)
    """)

    # Get the user ID
    conn = op.get_bind()
    result = conn.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()
    if result:
        user_id = result[0]
        # Add admin role
        op.execute(f"""
        INSERT INTO user_roles (user_id, role_name)
        VALUES ({user_id}, 'admin')
        """)

def downgrade():
    # Remove the admin role and user
    op.execute("DELETE FROM user_roles WHERE role_name = 'admin'")
    op.execute("DELETE FROM users WHERE username = 'admin'")
```

Then apply the migration:

```python
if __name__ == "__main__":
    # init_migrations()  # Comment this out after first run
    # create_initial_migration()  # Comment this out after first run
    # create_schema_update_migration()  # Comment this out after first run
    # create_roles_migration()  # Comment this out after first run
    # check_migration_status()  # Comment this out after first run
    # create_custom_migration()  # Comment this out after first run
    apply_migrations()
```

```bash
python main.py
```

## Step 11: Using Async Migrations

If your application uses asynchronous database connections, you can use the
async migration adapter. Let's modify our code to use async migrations:

```python
# database.py (updated for async)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Use SQLite for simplicity in this tutorial
DATABASE_URL = "sqlite+aiosqlite:///./user_management_async.db"

engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    bind=engine
)

async def get_db():
    async with AsyncSessionLocal() as db:
        yield db
```

```python
# main_async.py
import asyncio
import os
from pydapter.migrations import AsyncAlembicAdapter
import models

async def init_migrations():
    """Initialize the migrations environment."""
    os.makedirs("migrations_async", exist_ok=True)

    await AsyncAlembicAdapter.init_migrations(
        directory="migrations_async",
        connection_string="sqlite+aiosqlite:///./user_management_async.db",
        models_module=models
    )
    print("Async migrations initialized successfully!")

async def create_initial_migration():
    """Create the initial migration."""
    revision = await AsyncAlembicAdapter.create_migration(
        message="Create users table",
        autogenerate=True,
        directory="migrations_async",
        connection_string="sqlite+aiosqlite:///./user_management_async.db"
    )
    print(f"Created initial async migration: {revision}")

async def apply_migrations():
    """Apply all pending migrations."""
    await AsyncAlembicAdapter.upgrade(
        revision="head",
        directory="migrations_async",
        connection_string="sqlite+aiosqlite:///./user_management_async.db"
    )
    print("Async migrations applied successfully!")

async def main():
    await init_migrations()
    await create_initial_migration()
    await apply_migrations()

if __name__ == "__main__":
    asyncio.run(main())
```

Run the async script:

```bash
python main_async.py
```

## Complete Example

Here's a complete example of the main.py file that includes all the migration
operations:

```python
# main.py
import os
from pydapter.migrations import AlembicAdapter
import models

def init_migrations():
    """Initialize the migrations environment."""
    os.makedirs("migrations", exist_ok=True)

    AlembicAdapter.init_migrations(
        directory="migrations",
        connection_string="sqlite:///./user_management.db",
        models_module=models
    )
    print("Migrations initialized successfully!")

def create_initial_migration():
    """Create the initial migration."""
    revision = AlembicAdapter.create_migration(
        message="Create users table",
        autogenerate=True,
        directory="migrations",
        connection_string="sqlite:///./user_management.db"
    )
    print(f"Created initial migration: {revision}")

def apply_migrations():
    """Apply all pending migrations."""
    AlembicAdapter.upgrade(
        revision="head",
        directory="migrations",
        connection_string="sqlite:///./user_management.db"
    )
    print("Migrations applied successfully!")

def create_schema_update_migration():
    """Create a migration for schema updates."""
    revision = AlembicAdapter.create_migration(
        message="Add user profile fields",
        autogenerate=True,
        directory="migrations",
        connection_string="sqlite:///./user_management.db"
    )
    print(f"Created schema update migration: {revision}")

def create_roles_migration():
    """Create a migration for the roles model."""
    revision = AlembicAdapter.create_migration(
        message="Add user roles table",
        autogenerate=True,
        directory="migrations",
        connection_string="sqlite:///./user_management.db"
    )
    print(f"Created roles migration: {revision}")

def check_migration_status():
    """Check the current migration status."""
    current = AlembicAdapter.get_current_revision(
        directory="migrations",
        connection_string="sqlite:///./user_management.db"
    )
    print(f"Current migration revision: {current}")

    history = AlembicAdapter.get_migration_history(
        directory="migrations",
        connection_string="sqlite:///./user_management.db"
    )
    print("\nMigration history:")
    for migration in history:
        print(f"- {migration['revision']}: {migration.get('description', 'No description')}")

def downgrade_migration(revision):
    """Downgrade to a specific revision."""
    AlembicAdapter.downgrade(
        revision=revision,
        directory="migrations",
        connection_string="sqlite:///./user_management.db"
    )
    print(f"Downgraded to revision: {revision}")

def create_custom_migration():
    """Create a custom data migration."""
    revision = AlembicAdapter.create_migration(
        message="Add default admin user",
        autogenerate=False,  # Don't auto-generate from models
        directory="migrations",
        connection_string="sqlite:///./user_management.db"
    )
    print(f"Created custom migration: {revision}")
    print(f"Edit the migration file in migrations/versions/{revision}_add_default_admin_user.py")

if __name__ == "__main__":
    # Uncomment the function you want to run
    # init_migrations()
    # create_initial_migration()
    # apply_migrations()
    # create_schema_update_migration()
    # create_roles_migration()
    # check_migration_status()

    # Downgrade example
    # history = AlembicAdapter.get_migration_history(
    #     directory="migrations",
    #     connection_string="sqlite:///./user_management.db"
    # )
    # if len(history) >= 2:
    #     previous_revision = history[-2]['revision']
    #     downgrade_migration(previous_revision)
    # else:
    #     print("Not enough migrations to downgrade")

    # create_custom_migration()

    # Final upgrade to latest
    apply_migrations()
```

## Summary

In this tutorial, we've demonstrated how to use pydapter's migrations module to
manage database schema evolution. We've covered:

1. Setting up a migrations environment
2. Creating and applying initial migrations
3. Evolving the schema with new fields
4. Adding new models
5. Checking migration status
6. Downgrading to previous versions
7. Creating custom data migrations
8. Using async migrations

The migrations module provides a powerful way to manage database schema changes
in a controlled, versioned manner, making it easier to evolve your application's
data model over time.

## Best Practices

Here are some best practices to follow when working with migrations:

1. **Always back up your database before applying migrations in production**
2. **Keep migrations small and focused on specific changes**
3. **Test migrations thoroughly in development before applying to production**
4. **Include descriptive messages for each migration**
5. **Use version control for your migration files**
6. **Consider using separate migration environments for different deployment
   stages**
7. **Document complex migrations with comments**
8. **Include both upgrade and downgrade operations when possible**
