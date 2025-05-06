# PostgreSQL Adapter Tutorial for Pydapter

This tutorial will show you how to use the PostgreSQL adapters in pydapter to
seamlessly convert between Pydantic models and PostgreSQL databases. We'll cover
both synchronous and asynchronous adapters.

## Prerequisites

### 1. Install Dependencies

```bash
# Create a virtual environment if you haven't already
python -m venv pydapter-demo
source pydapter-demo/bin/activate  # On Windows: pydapter-demo\Scripts\activate

# Install dependencies
pip install pydantic sqlalchemy psycopg  # For synchronous adapter
pip install asyncpg  # For asynchronous adapter

# Install pydapter (if you haven't done so already)
# Either from PyPI when available:
# pip install pydapter
# Or from the repository:
git clone https://github.com/ohdearquant/pydapter.git
cd pydapter
pip install -e .
```

### 2. Set Up PostgreSQL

Make sure you have PostgreSQL installed and running. You can use a local
installation or a Docker container:

```bash
# Using Docker to run PostgreSQL
docker run --name pydapter-postgres -e POSTGRES_PASSWORD=password -e POSTGRES_USER=pydapter -e POSTGRES_DB=pydapter_demo -p 5432:5432 -d postgres:14

# Alternatively, install PostgreSQL locally and create a database
# createuser -s pydapter
# createdb -O pydapter pydapter_demo
```

### 3. Create a Test Table

Connect to your PostgreSQL instance and create a test table:

```sql
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Optional: Add some test data
INSERT INTO users (name, email) VALUES
    ('Alice', 'alice@example.com'),
    ('Bob', 'bob@example.com'),
    ('Charlie', 'charlie@example.com');
```

## Synchronous PostgreSQL Adapter

Let's start with the synchronous PostgreSQL adapter:

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from pydapter.extras.postgres_ import PostgresAdapter

# Define a Pydantic model that maps to our database table
class User(BaseModel):
    id: Optional[int] = None
    name: str
    email: str
    active: bool = True
    created_at: Optional[datetime] = None

# Connection details
db_config = {
    "engine_url": "postgresql+psycopg://pydapter:password@localhost/pydapter_demo"
    # You can also use:
    # "engine_url": "postgresql://pydapter:password@localhost/pydapter_demo"
    # Pydapter will convert it to the correct format
}

# Read data from the database
def read_users():
    # Query all users
    users = PostgresAdapter.from_obj(
        User,
        {
            **db_config,
            "table": "users",
            "selectors": {}  # Empty selectors means "select all"
        },
        many=True  # Return a list of users
    )

    print(f"Found {len(users)} users:")
    for user in users:
        print(f"  - {user.name} ({user.email}): Active={user.active}")

    return users

# Query a specific user
def get_user_by_email(email):
    try:
        user = PostgresAdapter.from_obj(
            User,
            {
                **db_config,
                "table": "users",
                "selectors": {"email": email}
            },
            many=False  # Return a single user
        )
        print(f"Found user: {user.name} ({user.email})")
        return user
    except Exception as e:
        print(f"Error finding user: {e}")
        return None

# Create a new user
def create_user(name, email):
    user = User(name=name, email=email)

    result = PostgresAdapter.to_obj(
        user,
        **db_config,
        table="users",
        many=False
    )

    print(f"Created user: {result}")
    return user

# Main function to demo the adapter
def main():
    print("Reading all users:")
    users = read_users()

    print("\nFinding user by email:")
    alice = get_user_by_email("alice@example.com")

    print("\nCreating a new user:")
    new_user = create_user("Dave", "dave@example.com")

    print("\nVerifying new user was added:")
    read_users()

if __name__ == "__main__":
    main()
```

## Asynchronous PostgreSQL Adapter

Now let's use the asynchronous version with asyncpg:

```python
import asyncio
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from pydapter.extras.async_postgres_ import AsyncPostgresAdapter

# Define a Pydantic model that maps to our database table
class User(BaseModel):
    id: Optional[int] = None
    name: str
    email: str
    active: bool = True
    created_at: Optional[datetime] = None

# Connection details
db_config = {
    "engine_url": "postgresql+asyncpg://pydapter:password@localhost/pydapter_demo"
    # You can also use:
    # "engine_url": "postgresql://pydapter:password@localhost/pydapter_demo"
    # Pydapter will convert it to the correct format with asyncpg
}

# Read data from the database asynchronously
async def read_users():
    # Query all users
    users = await AsyncPostgresAdapter.from_obj(
        User,
        {
            **db_config,
            "table": "users",
            "selectors": {}  # Empty selectors means "select all"
        },
        many=True  # Return a list of users
    )

    print(f"Found {len(users)} users:")
    for user in users:
        print(f"  - {user.name} ({user.email}): Active={user.active}")

    return users

# Query a specific user asynchronously
async def get_user_by_email(email):
    try:
        user = await AsyncPostgresAdapter.from_obj(
            User,
            {
                **db_config,
                "table": "users",
                "selectors": {"email": email}
            },
            many=False  # Return a single user
        )
        print(f"Found user: {user.name} ({user.email})")
        return user
    except Exception as e:
        print(f"Error finding user: {e}")
        return None

# Create a new user asynchronously
async def create_user(name, email):
    user = User(name=name, email=email)

    result = await AsyncPostgresAdapter.to_obj(
        user,
        **db_config,
        table="users",
        many=False
    )

    print(f"Created user: {result}")
    return user

# Main function to demo the async adapter
async def main():
    print("Reading all users:")
    users = await read_users()

    print("\nFinding user by email:")
    alice = await get_user_by_email("alice@example.com")

    print("\nCreating a new user:")
    new_user = await create_user("Eve", "eve@example.com")

    print("\nVerifying new user was added:")
    await read_users()

# Run the async main function
if __name__ == "__main__":
    asyncio.run(main())
```

## Advanced Usage: Using Adaptable Mixin

For a more ergonomic API, you can use the `AsyncAdaptable` mixin:

```python
import asyncio
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from pydapter.async_core import AsyncAdaptable
from pydapter.extras.async_postgres_ import AsyncPostgresAdapter

# Define a model with the AsyncAdaptable mixin
class User(BaseModel, AsyncAdaptable):
    id: Optional[int] = None
    name: str
    email: str
    active: bool = True
    created_at: Optional[datetime] = None

# Register the async PostgreSQL adapter
User.register_async_adapter(AsyncPostgresAdapter)

# Main async function
async def main():
    # Connection configuration
    db_config = {
        "engine_url": "postgresql+asyncpg://pydapter:password@localhost/pydapter_demo",
        "table": "users",
        "selectors": {}
    }

    # Read users using the mixin methods
    users = await User.adapt_from_async(db_config, obj_key="async_pg", many=True)

    print(f"Found {len(users)} users:")
    for user in users:
        print(f"  - {user.name} ({user.email})")

    # Create a new user
    new_user = User(name="Frank", email="frank@example.com")

    # Save to database
    result = await new_user.adapt_to_async(
        obj_key="async_pg",
        engine_url="postgresql+asyncpg://pydapter:password@localhost/pydapter_demo",
        table="users"
    )

    print(f"\nCreated new user: {result}")

    # Verify the user was added
    updated_users = await User.adapt_from_async(db_config, obj_key="async_pg", many=True)
    print(f"\nUpdated user count: {len(updated_users)}")

# Run the async main function
if __name__ == "__main__":
    asyncio.run(main())
```

## Error Handling

Let's demonstrate proper error handling for common PostgreSQL errors:

```python
from pydapter.exceptions import ConnectionError, QueryError, ResourceError
from pydapter.extras.postgres_ import PostgresAdapter
from pydantic import BaseModel

class User(BaseModel):
    id: Optional[int] = None
    name: str
    email: str

def handle_postgres_errors():
    # 1. Connection error - wrong password
    try:
        PostgresAdapter.from_obj(
            User,
            {
                "engine_url": "postgresql://pydapter:wrong_password@localhost/pydapter_demo",
                "table": "users"
            }
        )
    except ConnectionError as e:
        print(f"Authentication error handled: {e}")

    # 2. Connection error - wrong host
    try:
        PostgresAdapter.from_obj(
            User,
            {
                "engine_url": "postgresql://pydapter:password@nonexistent_host/pydapter_demo",
                "table": "users"
            }
        )
    except ConnectionError as e:
        print(f"Host connection error handled: {e}")

    # 3. Resource error - table doesn't exist
    try:
        PostgresAdapter.from_obj(
            User,
            {
                "engine_url": "postgresql://pydapter:password@localhost/pydapter_demo",
                "table": "nonexistent_table"
            }
        )
    except ResourceError as e:
        print(f"Table resource error handled: {e}")

    # 4. Query error - SQL syntax error
    try:
        # This would normally be handled internally, but for demonstration
        # you might encounter this when using raw SQL
        pass
    except QueryError as e:
        print(f"Query error handled: {e}")

# Run the error handling examples
handle_postgres_errors()
```

## Practical Example: A Task Management System

Let's create a more complete example of a task management system:

```python
import asyncio
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from pydapter.async_core import AsyncAdaptable
from pydapter.extras.async_postgres_ import AsyncPostgresAdapter

# Database setup - Run this SQL in your PostgreSQL database first
"""
CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id),
    title VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    due_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# Define models with AsyncAdaptable
class Project(BaseModel, AsyncAdaptable):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None

class Task(BaseModel, AsyncAdaptable):
    id: Optional[int] = None
    project_id: int
    title: str
    description: Optional[str] = None
    status: str = "pending"
    due_date: Optional[datetime] = None
    created_at: Optional[datetime] = None

# Register adapters
Project.register_async_adapter(AsyncPostgresAdapter)
Task.register_async_adapter(AsyncPostgresAdapter)

# Database configuration
DB_CONFIG = {
    "engine_url": "postgresql+asyncpg://pydapter:password@localhost/pydapter_demo"
}

# Task management system class
class TaskManager:
    def __init__(self, db_config):
        self.db_config = db_config

    async def create_project(self, name, description=None):
        project = Project(name=name, description=description)
        result = await project.adapt_to_async(
            obj_key="async_pg",
            **self.db_config,
            table="projects"
        )

        # Get the new project with its ID
        projects = await Project.adapt_from_async(
            {
                **self.db_config,
                "table": "projects",
                "selectors": {"name": name}
            },
            obj_key="async_pg",
            many=True
        )

        if projects:
            return projects[0]
        return None

    async def get_projects(self):
        return await Project.adapt_from_async(
            {
                **self.db_config,
                "table": "projects"
            },
            obj_key="async_pg",
            many=True
        )

    async def create_task(self, project_id, title, description=None, due_date=None):
        task = Task(
            project_id=project_id,
            title=title,
            description=description,
            due_date=due_date
        )

        result = await task.adapt_to_async(
            obj_key="async_pg",
            **self.db_config,
            table="tasks"
        )

        return task

    async def get_tasks_for_project(self, project_id):
        return await Task.adapt_from_async(
            {
                **self.db_config,
                "table": "tasks",
                "selectors": {"project_id": project_id}
            },
            obj_key="async_pg",
            many=True
        )

    async def update_task_status(self, task_id, new_status):
        # First, get the task
        task = await Task.adapt_from_async(
            {
                **self.db_config,
                "table": "tasks",
                "selectors": {"id": task_id}
            },
            obj_key="async_pg",
            many=False
        )

        # Update the status
        task.status = new_status

        # Save back to database
        result = await task.adapt_to_async(
            obj_key="async_pg",
            **self.db_config,
            table="tasks"
        )

        return task

# Main function to demo the task manager
async def main():
    manager = TaskManager(DB_CONFIG)

    # Create a new project
    print("Creating a new project...")
    project = await manager.create_project(
        "Website Redesign",
        "Redesign the company website with modern UI/UX"
    )
    print(f"Project created: {project.id} - {project.name}")

    # Add tasks to the project
    print("\nAdding tasks to the project...")
    tasks = [
        await manager.create_task(
            project.id,
            "Design mockups",
            "Create initial design mockups for homepage",
            datetime.now().replace(day=datetime.now().day + 7)
        ),
        await manager.create_task(
            project.id,
            "Frontend implementation",
            "Implement the design in React",
            datetime.now().replace(day=datetime.now().day + 14)
        ),
        await manager.create_task(
            project.id,
            "Backend API",
            "Implement the required API endpoints",
            datetime.now().replace(day=datetime.now().day + 10)
        )
    ]

    # Get all projects
    print("\nListing all projects:")
    projects = await manager.get_projects()
    for proj in projects:
        print(f"  - {proj.id}: {proj.name}")

        # Get tasks for this project
        proj_tasks = await manager.get_tasks_for_project(proj.id)
        for task in proj_tasks:
            print(f"      - {task.title} [{task.status}] " +
                  (f"(Due: {task.due_date.strftime('%Y-%m-%d')})" if task.due_date else ""))

    # Update a task status
    print("\nUpdating task status...")
    updated_task = await manager.update_task_status(tasks[0].id, "in_progress")
    print(f"Updated task: {updated_task.title} - Status: {updated_task.status}")

    # Final task list
    print("\nFinal task list:")
    final_tasks = await manager.get_tasks_for_project(project.id)
    for task in final_tasks:
        print(f"  - {task.title} [{task.status}]")

if __name__ == "__main__":
    asyncio.run(main())
```

## Handling Advanced PostgreSQL Features

PostgreSQL has many advanced features like JSON/JSONB fields, arrays, and
full-text search. Here's how to work with some of these using pydapter:

```python
import asyncio
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from pydapter.async_core import AsyncAdaptable
from pydapter.extras.async_postgres_ import AsyncPostgresAdapter

# Database setup - Run this SQL in your PostgreSQL database first
"""
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price NUMERIC(10, 2) NOT NULL,
    categories TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}'
);
"""

# Define our model with PostgreSQL-specific types
class Product(BaseModel, AsyncAdaptable):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    price: float
    categories: List[str] = []
    metadata: Dict[str, Any] = {}

# Register adapter
Product.register_async_adapter(AsyncPostgresAdapter)

# Database config
DB_CONFIG = {
    "engine_url": "postgresql+asyncpg://pydapter:password@localhost/pydapter_demo"
}

async def demo_advanced_postgres_features():
    # Create products with array and JSON data
    products = [
        Product(
            name="Smartphone",
            description="Latest model with advanced features",
            price=999.99,
            categories=["electronics", "mobile", "gadgets"],
            metadata={
                "brand": "TechX",
                "model": "TX-2000",
                "specs": {
                    "cpu": "Octa-core",
                    "ram": "8GB",
                    "storage": "256GB"
                }
            }
        ),
        Product(
            name="Coffee Maker",
            description="Premium coffee machine for home or office",
            price=199.99,
            categories=["appliances", "kitchen", "coffee"],
            metadata={
                "brand": "BrewMaster",
                "features": ["programmable", "thermal carafe", "auto-clean"],
                "dimensions": {
                    "width": 30,
                    "height": 40,
                    "depth": 20
                }
            }
        )
    ]

    # Save products to database
    print("Saving products with arrays and JSON data...")
    for product in products:
        await product.adapt_to_async(
            obj_key="async_pg",
            **DB_CONFIG,
            table="products"
        )

    # Query all products
    print("\nRetrieving products from database:")
    db_products = await Product.adapt_from_async(
        {
            **DB_CONFIG,
            "table": "products"
        },
        obj_key="async_pg",
        many=True
    )

    # Display products with their array and JSON data
    for product in db_products:
        print(f"\n{product.name} - ${product.price}")
        print(f"  Description: {product.description}")
        print(f"  Categories: {', '.join(product.categories)}")
        print(f"  Metadata: {json.dumps(product.metadata, indent=2)}")

if __name__ == "__main__":
    asyncio.run(demo_advanced_postgres_features())
```

## Conclusion

In this tutorial, you learned how to use pydapter's PostgreSQL adapters to
seamlessly work with both synchronous and asynchronous database operations.
These adapters provide a clean interface for converting between Pydantic models
and PostgreSQL database records, with specialized error handling for
PostgreSQL-specific issues.

The asynchronous adapter is particularly useful for high-performance
applications where you want to avoid blocking I/O operations. By using the
`AsyncAdaptable` mixin, you can create a more ergonomic API that makes your code
cleaner and more maintainable.

The key advantages of using pydapter's PostgreSQL adapters include:

1. Automatic validation through Pydantic models
2. Consistent error handling
3. Support for both synchronous and asynchronous operations
4. Easy conversion between models and database records
5. Support for PostgreSQL-specific data types like arrays and JSONB

Try experimenting with these adapters in your own projects to see how they can
simplify your database interactions!
