# CRUD Operations with Pydapter

This guide covers the enhanced CRUD (Create, Read, Update, Delete) operations
available in pydapter's async SQL adapters.

## Overview

Pydapter's async SQL adapters now support full CRUD operations through a clean,
config-driven interface. All operations are controlled through configuration
dictionaries, maintaining backward compatibility while adding powerful new
capabilities.

## Installation

```bash
# For PostgreSQL support
pip install pydapter[postgres]

# For generic SQL support
pip install pydapter[sql]
```

## Configuration

### TypedDict Support

Pydapter provides TypedDict classes for better IDE support and type safety:

```python
from pydapter.extras.async_sql_ import AsyncSQLAdapter, SQLReadConfig, SQLWriteConfig

# Type-safe configuration
config: SQLReadConfig = {
    "dsn": "postgresql+asyncpg://user:pass@localhost/db",
    "table": "users",
    "selectors": {"active": True},
    "limit": 10
}
```

### Connection Options

You can provide database connection in three ways:

1. **DSN (recommended)**: Database connection string
2. **engine_url** (legacy): Backward compatibility
3. **engine**: Pre-existing SQLAlchemy AsyncEngine for connection reuse

```python
# Option 1: DSN (recommended)
config = {"dsn": "postgresql+asyncpg://user:pass@localhost/db", "table": "users"}

# Option 2: Legacy engine_url
config = {"engine_url": "postgresql+asyncpg://user:pass@localhost/db", "table": "users"}

# Option 3: Reuse existing engine (most efficient)
from sqlalchemy.ext.asyncio import create_async_engine
engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/db")
config = {"engine": engine, "table": "users"}
```

## CRUD Operations

### SELECT (Read)

```python
from pydantic import BaseModel
from pydapter.extras.async_sql_ import AsyncSQLAdapter

class User(BaseModel):
    id: int
    name: str
    email: str
    age: int

# Select all users (default operation for from_obj)
users = await AsyncSQLAdapter.from_obj(User, {
    "dsn": "postgresql+asyncpg://user:pass@localhost/db",
    "table": "users"
}, many=True)

# Select with filters
config = {
    "dsn": "postgresql+asyncpg://user:pass@localhost/db",
    "table": "users",
    "selectors": {"age": 30, "active": True}
}
filtered_users = await AsyncSQLAdapter.from_obj(User, config, many=True)

# Select with limit and offset
config = {
    "dsn": "postgresql+asyncpg://user:pass@localhost/db",
    "table": "users",
    "limit": 10,
    "offset": 20
}
paginated_users = await AsyncSQLAdapter.from_obj(User, config, many=True)
```

### INSERT (Create)

```python
# Single insert (default operation for to_obj)
new_user = User(name="John Doe", email="john@example.com", age=30)
result = await AsyncSQLAdapter.to_obj(
    new_user,
    dsn="postgresql+asyncpg://user:pass@localhost/db",
    table="users"
)
# Returns: {"inserted_count": 1}

# Bulk insert
users = [
    User(name="Alice", email="alice@example.com", age=25),
    User(name="Bob", email="bob@example.com", age=30),
]
result = await AsyncSQLAdapter.to_obj(
    users,
    dsn="postgresql+asyncpg://user:pass@localhost/db",
    table="users"
)
# Returns: {"inserted_count": 2}
```

### UPDATE

```python
# Update specific records
updated_user = User(name="John Updated", email="john@example.com", age=31)
result = await AsyncSQLAdapter.to_obj(
    updated_user,
    dsn="postgresql+asyncpg://user:pass@localhost/db",
    table="users",
    operation="update",
    where={"email": "john@example.com"}
)
# Returns: {"updated_count": 1}

# Update multiple records
result = await AsyncSQLAdapter.to_obj(
    {"status": "inactive"},
    dsn="postgresql+asyncpg://user:pass@localhost/db",
    table="users",
    operation="update",
    where={"last_login": {"<": "2024-01-01"}}
)
```

### DELETE

```python
# Delete specific records
config = {
    "dsn": "postgresql+asyncpg://user:pass@localhost/db",
    "table": "users",
    "operation": "delete",
    "selectors": {"id": 123}
}
result = await AsyncSQLAdapter.from_obj(User, config)
# Returns: {"deleted_count": 1}

# Delete with multiple conditions
config = {
    "dsn": "postgresql+asyncpg://user:pass@localhost/db",
    "table": "users",
    "operation": "delete",
    "selectors": {"status": "inactive", "created_at": {"<": "2023-01-01"}}
}
result = await AsyncSQLAdapter.from_obj(User, config)
```

### UPSERT (Insert or Update)

```python
# Upsert - insert if not exists, update if exists
user = User(name="Jane Doe", email="jane@example.com", age=28)
result = await AsyncSQLAdapter.to_obj(
    user,
    dsn="postgresql+asyncpg://user:pass@localhost/db",
    table="users",
    operation="upsert",
    conflict_columns=["email"]  # Columns that define uniqueness
)
# Returns: {"inserted_count": 1, "updated_count": 0, "total_count": 1}

# Subsequent upsert with same email will update
user.age = 29
result = await AsyncSQLAdapter.to_obj(
    user,
    dsn="postgresql+asyncpg://user:pass@localhost/db",
    table="users",
    operation="upsert",
    conflict_columns=["email"]
)
# Returns: {"inserted_count": 0, "updated_count": 1, "total_count": 1}
```

### Raw SQL Execution

**Important**: Raw SQL operations do NOT require a `table` parameter and do NOT
perform table inspection. This makes them ideal for:
- Complex queries across multiple tables
- Aggregations and analytical queries
- DDL operations (CREATE, ALTER, DROP)
- Working with databases where async table inspection isn't supported

```python
# Execute custom SQL with parameters (no table parameter needed!)
config = {
    "dsn": "postgresql+asyncpg://user:pass@localhost/db",
    "operation": "raw_sql",
    "sql": """
        SELECT
            department,
            COUNT(*) as user_count,
            AVG(age) as avg_age
        FROM users
        WHERE active = :active
        GROUP BY department
        HAVING COUNT(*) > :min_count
    """,
    "params": {"active": True, "min_count": 5}
}
results = await AsyncSQLAdapter.from_obj(dict, config, many=True)

# ORDER BY queries (common use case)
config = {
    "dsn": "sqlite:///app.db",  # Works with SQLite too!
    "operation": "raw_sql",
    "sql": "SELECT * FROM events ORDER BY created_at DESC LIMIT :limit",
    "params": {"limit": 10}
}
recent_events = await AsyncSQLAdapter.from_obj(dict, config, many=True)

# DDL operations (CREATE, ALTER, DROP)
config = {
    "dsn": "postgresql+asyncpg://user:pass@localhost/db",
    "operation": "raw_sql",
    "sql": "CREATE INDEX idx_users_email ON users(email)",
    "fetch_results": False  # Don't try to fetch results for DDL
}
result = await AsyncSQLAdapter.from_obj(dict, config)
# Returns: {"affected_rows": 0}
```

## PostgreSQL Specific Features

The `AsyncPostgresAdapter` provides PostgreSQL-specific optimizations:

```python
from pydapter.extras.async_postgres_ import AsyncPostgresAdapter

# Automatic DSN format conversion
config = {
    "dsn": "postgresql://user:pass@localhost/db",  # Standard PostgreSQL format
    "table": "users"
}
# Automatically converted to: postgresql+asyncpg://user:pass@localhost/db

users = await AsyncPostgresAdapter.from_obj(User, config, many=True)

# PostgreSQL-specific error handling
try:
    await AsyncPostgresAdapter.to_obj(user, dsn=dsn, table="users")
except ConnectionError as e:
    if "authentication" in str(e):
        print("Authentication failed")
    elif "database does not exist" in str(e):
        print("Database not found")
```

## Real-World Example

```python
import asyncio
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import create_async_engine
from pydapter.extras.async_sql_ import AsyncSQLAdapter

class Customer(BaseModel):
    id: Optional[int] = None
    username: str
    email: str
    full_name: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

async def manage_customers():
    # Create a reusable engine for efficiency
    engine = create_async_engine("postgresql+asyncpg://postgres:postgres@localhost/db")

    try:
        # 1. Insert new customer
        customer = Customer(
            username="johndoe",
            email="john@example.com",
            full_name="John Doe"
        )
        result = await AsyncSQLAdapter.to_obj(
            customer,
            engine=engine,
            table="customers"
        )
        print(f"Created customer: {result}")

        # 2. Find customer by username
        config = {
            "engine": engine,
            "table": "customers",
            "selectors": {"username": "johndoe"}
        }
        found_customer = await AsyncSQLAdapter.from_obj(Customer, config, many=False)
        print(f"Found customer: {found_customer}")

        # 3. Update customer email
        found_customer.email = "newemail@example.com"
        result = await AsyncSQLAdapter.to_obj(
            found_customer,
            engine=engine,
            table="customers",
            operation="update",
            where={"username": "johndoe"}
        )
        print(f"Updated customer: {result}")

        # 4. Get customer statistics
        config = {
            "engine": engine,
            "operation": "raw_sql",
            "sql": """
                SELECT
                    COUNT(*) as total_customers,
                    COUNT(DISTINCT DATE(created_at)) as signup_days
                FROM customers
                WHERE created_at > :since
            """,
            "params": {"since": "2024-01-01"}
        }
        stats = await AsyncSQLAdapter.from_obj(dict, config, many=False)
        print(f"Customer stats: {stats}")

    finally:
        await engine.dispose()

# Run the example
asyncio.run(manage_customers())
```

## Best Practices

1. **Use TypedDict for Configuration**: Provides better IDE support and type safety

   ```python
   config: SQLReadConfig = {"dsn": dsn, "table": "users"}
   ```

2. **Reuse Engines for Bulk Operations**: Create one engine and pass it to
   multiple operations for efficiency

   ```python
   # Create engine once for the entire batch operation
   engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/db")

   try:
       # Process multiple batches using the same engine
       for batch in data_batches:
           # Pass the engine directly - avoids creating new connections
           result = await AsyncSQLAdapter.to_obj(
               batch,
               engine=engine,  # Reuses connection pool
               table="users"
           )
           print(f"Inserted {result['inserted_count']} records")

       # Or for multiple different operations
       await AsyncSQLAdapter.to_obj(users, engine=engine, table="users")
       await AsyncSQLAdapter.to_obj(orders, engine=engine, table="orders")
       await AsyncSQLAdapter.to_obj(items, engine=engine, table="items")

   finally:
       # Always dispose of the engine when done
       await engine.dispose()
   ```

   **Note**: SQLAlchemy engines manage their own connection pools internally.
   You don't use `async with engine:` context managers with engines - that pattern
   is for connections/sessions.

3. **Handle None Values**: The adapter automatically excludes None values from
   INSERT/UPDATE operations

   ```python
   user = User(id=None, name="John")  # id=None will be excluded
   ```

4. **Use Parameterized Queries**: Always use parameters for raw SQL to prevent
   SQL injection

   ```python
   config = {
       "operation": "raw_sql",
       "sql": "SELECT * FROM users WHERE email = :email",
       "params": {"email": user_input}  # Safe parameterization
   }
   ```

5. **Error Handling**: Use specific exception types for better error handling

   ```python
   from pydapter.exceptions import ConnectionError, QueryError, ValidationError

   try:
       result = await AsyncSQLAdapter.from_obj(User, config)
   except ConnectionError:
       # Handle connection issues
   except QueryError:
       # Handle query errors
   except ValidationError:
       # Handle validation errors
   ```

## Testing

Pydapter includes comprehensive tests for all CRUD operations:

```bash
# Run tests
pytest libs/pydapter/tests/test_async_sql_crud.py -v

# Run with coverage
pytest libs/pydapter/tests/test_async_sql_crud.py --cov=pydapter.extras
```

## Migration from Basic Operations

If you're currently using basic pydapter operations, migration is simple:

```python
# Old: Basic insert only
await adapter.to_obj(user, engine_url=url, table="users")

# New: Full CRUD support (backward compatible)
await adapter.to_obj(user, dsn=url, table="users")  # INSERT (default)
await adapter.to_obj(user, dsn=url, table="users", operation="update", where={"id": 1})
await adapter.to_obj(user, dsn=url, table="users", operation="upsert", conflict_columns=["email"])
```

## Troubleshooting

### Common Issues

1. **"Multiple engine parameters provided"**: Only use one of `dsn`, `engine_url`, or `engine`
2. **"Missing required parameter"**: For select/delete operations, ensure you
   provide a connection parameter and table name. For raw_sql operations, only
   the connection parameter and sql are required
3. **SQL parameter syntax**: Use `:param_name` for SQLAlchemy, not `%(param_name)s`
4. **None values in primary keys**: The adapter automatically filters out None values

### Performance Tips

1. **Connection Pooling**: Reuse engines instead of creating new ones
2. **Batch Operations**: Use bulk insert/update for multiple records
3. **Indexing**: Ensure proper database indexes for WHERE clause columns
4. **Raw SQL**: Use raw SQL for complex queries that don't fit the CRUD pattern

## API Reference

### SQLReadConfig

Configuration for read operations (`from_obj`):

- `dsn` / `engine_url` / `engine`: Database connection (one required)
- `table`: Table name (required for select/delete, NOT required for raw_sql)
- `operation`: "select" (default), "delete", or "raw_sql"
- `selectors`: WHERE conditions for select/delete
- `limit`: Maximum records to return (select only)
- `offset`: Number of records to skip (select only)
- `order_by`: ORDER BY clause (select only)
- `sql`: Raw SQL statement (required for raw_sql operation)
- `params`: SQL parameters (for raw_sql operation)
- `fetch_results`: Whether to fetch results (raw_sql only, default: True)

### SQLWriteConfig

Configuration for write operations (`to_obj` kwargs):

- `dsn` / `engine_url` / `engine`: Database connection (one required)
- `table`: Table name (required)
- `operation`: "insert" (default), "update", or "upsert"
- `where`: WHERE conditions for UPDATE
- `conflict_columns`: Columns defining uniqueness for UPSERT

## Support

For issues or questions, please refer to the
[pydapter GitHub repository](https://github.com/khive-ai/pydapter) or the
comprehensive test suite in `tests/test_async_sql_crud.py`.
