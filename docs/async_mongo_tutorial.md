# End-to-End Tutorial: Using Pydapter's Async MongoDB Adapter

This comprehensive tutorial will guide you through using Pydapter's async
MongoDB adapter for seamless data operations between Pydantic models and
MongoDB collections.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Setting Up MongoDB](#setting-up-mongodb)
- [Basic Usage](#basic-usage)
- [CRUD Operations](#crud-operations)
- [Advanced Querying](#advanced-querying)
- [Error Handling](#error-handling)
- [Practical Example](#practical-example)
- [Performance Tips](#performance-tips)
- [Best Practices](#best-practices)

## Overview

The AsyncMongoAdapter provides asynchronous methods to:

- Query MongoDB collections and convert documents to Pydantic models
- Insert Pydantic models as documents into MongoDB collections
- Handle async MongoDB operations using Motor (async MongoDB driver)
- Support various async MongoDB operations (find, insert, update, delete)

**Key Features:**

- Full async/await support
- Automatic Pydantic model validation
- Comprehensive error handling
- MongoDB query filter support
- Batch operations for performance

## Prerequisites

- Python 3.8+
- MongoDB server (local or remote)
- Basic knowledge of async/await in Python
- Familiarity with Pydantic models
- Understanding of MongoDB concepts

## Installation

Install the required dependencies:

```bash
pip install motor pymongo pydantic
```

## Setting Up MongoDB

### Local MongoDB with Docker

```bash
# Start MongoDB container
docker run -d -p 27017:27017 --name mongodb mongo:latest

# Or use docker-compose
version: '3.8'
services:
  mongodb:
    image: mongo:latest
    ports:
      - "27017:27017"
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: password
```

### MongoDB Atlas (Cloud)

For production environments, consider using MongoDB Atlas:

1. Create account at [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Create cluster and get connection string
3. Update connection string in your code

## Basic Usage

### Import and Setup

```python
import asyncio
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from pydapter.extras.async_mongo_ import AsyncMongoAdapter
from pydapter.exceptions import ConnectionError, ResourceError, AdapterValidationError

# Configuration
MONGO_URL = "mongodb://localhost:27017"
DATABASE_NAME = "tutorial_db"
```

### Defining Data Models

```python
class User(BaseModel):
    """User model for our application."""
    id: int
    username: str
    email: str
    age: int
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)

class Product(BaseModel):
    """Product model for an e-commerce system."""
    id: int
    name: str
    description: str
    price: float
    category: str
    in_stock: bool = True
    tags: List[str] = []

class Order(BaseModel):
    """Order model linking users and products."""
    id: int
    user_id: int
    product_ids: List[int]
    total_amount: float
    status: str = "pending"
    order_date: datetime = Field(default_factory=datetime.now)
```

## CRUD Operations

### Creating (Inserting) Data

#### Single Document Insert

```python
async def create_single_user():
    """Create and insert a single user."""
    user = User(
        id=1,
        username="john_doe",
        email="john@example.com",
        age=30
    )

    try:
        result = await AsyncMongoAdapter.to_obj(
            user,
            url=MONGO_URL,
            db=DATABASE_NAME,
            collection="users",
            many=False
        )
        print(f"User created successfully")
        return result
    except Exception as e:
        print(f"Error creating user: {e}")
        raise
```

#### Batch Insert

```python
async def create_multiple_users():
    """Create and insert multiple users."""
    users = [
        User(id=1, username="john_doe", email="john@example.com", age=30),
        User(id=2, username="jane_smith", email="jane@example.com", age=25),
        User(id=3, username="bob_wilson", email="bob@example.com", age=35),
    ]

    try:
        result = await AsyncMongoAdapter.to_obj(
            users,
            url=MONGO_URL,
            db=DATABASE_NAME,
            collection="users",
            many=True
        )
        print(f"Successfully inserted {result['inserted_count']} users")
        return result
    except Exception as e:
        print(f"Error inserting users: {e}")
        raise
```

### Reading (Querying) Data

#### Get All Documents

```python
async def get_all_users():
    """Retrieve all users from MongoDB."""
    try:
        users = await AsyncMongoAdapter.from_obj(
            User,
            {
                "url": MONGO_URL,
                "db": DATABASE_NAME,
                "collection": "users"
            },
            many=True
        )

        print(f"Retrieved {len(users)} users")
        for user in users:
            print(f"  - {user.username} ({user.email})")

        return users
    except Exception as e:
        print(f"Error retrieving users: {e}")
        raise
```

#### Get Single Document

```python
async def get_user_by_id(user_id: int):
    """Get a specific user by ID."""
    try:
        user = await AsyncMongoAdapter.from_obj(
            User,
            {
                "url": MONGO_URL,
                "db": DATABASE_NAME,
                "collection": "users",
                "filter": {"id": user_id}
            },
            many=False
        )

        print(f"Found user: {user.username}")
        return user
    except ResourceError:
        print(f"User with ID {user_id} not found")
        return None
    except Exception as e:
        print(f"Error retrieving user: {e}")
        raise
```

## Advanced Querying

### MongoDB Query Filters

The async MongoDB adapter supports full MongoDB query syntax:

```python
async def advanced_queries():
    """Demonstrate advanced MongoDB queries."""

    # Range queries
    adult_users = await AsyncMongoAdapter.from_obj(
        User,
        {
            "url": MONGO_URL,
            "db": DATABASE_NAME,
            "collection": "users",
            "filter": {"age": {"$gte": 18}}
        },
        many=True
    )

    # Multiple conditions
    active_adults = await AsyncMongoAdapter.from_obj(
        User,
        {
            "url": MONGO_URL,
            "db": DATABASE_NAME,
            "collection": "users",
            "filter": {
                "age": {"$gte": 18},
                "is_active": True
            }
        },
        many=True
    )

    # Regular expressions
    gmail_users = await AsyncMongoAdapter.from_obj(
        User,
        {
            "url": MONGO_URL,
            "db": DATABASE_NAME,
            "collection": "users",
            "filter": {"email": {"$regex": "@gmail.com$"}}
        },
        many=True
    )

    # Array queries
    tech_products = await AsyncMongoAdapter.from_obj(
        Product,
        {
            "url": MONGO_URL,
            "db": DATABASE_NAME,
            "collection": "products",
            "filter": {"tags": {"$in": ["tech", "electronics"]}}
        },
        many=True
    )

    return adult_users, active_adults, gmail_users, tech_products
```

### Complex Aggregation-style Queries

```python
async def complex_queries():
    """Demonstrate complex query patterns."""

    # Price range with category filter
    affordable_electronics = await AsyncMongoAdapter.from_obj(
        Product,
        {
            "url": MONGO_URL,
            "db": DATABASE_NAME,
            "collection": "products",
            "filter": {
                "category": "Electronics",
                "price": {"$gte": 50, "$lte": 500},
                "in_stock": True
            }
        },
        many=True
    )

    # Text search in multiple fields
    search_products = await AsyncMongoAdapter.from_obj(
        Product,
        {
            "url": MONGO_URL,
            "db": DATABASE_NAME,
            "collection": "products",
            "filter": {
                "$or": [
                    {"name": {"$regex": "laptop", "$options": "i"}},
                    {"description": {"$regex": "laptop", "$options": "i"}}
                ]
            }
        },
        many=True
    )

    return affordable_electronics, search_products
```

## Error Handling

### Exception Types

The async MongoDB adapter provides specific exception types:

```python
from pydapter.exceptions import (
    ConnectionError,      # Connection issues
    ResourceError,        # Resource not found
    AdapterValidationError,  # Validation errors
    QueryError           # Query execution errors
)
```

### Comprehensive Error Handling

```python
async def robust_data_operation():
    """Demonstrate comprehensive error handling."""

    try:
        # Attempt to get user
        user = await AsyncMongoAdapter.from_obj(
            User,
            {
                "url": MONGO_URL,
                "db": DATABASE_NAME,
                "collection": "users",
                "filter": {"id": 1}
            },
            many=False
        )
        return user

    except ConnectionError as e:
        print(f"Database connection failed: {e}")
        # Handle connection issues (retry, fallback, etc.)
        return None

    except ResourceError as e:
        print(f"User not found: {e}")
        # Handle missing resources
        return None

    except AdapterValidationError as e:
        print(f"Data validation failed: {e}")
        # Handle validation errors
        return None

    except QueryError as e:
        print(f"Query execution failed: {e}")
        # Handle query issues
        return None

    except Exception as e:
        print(f"Unexpected error: {e}")
        # Handle unexpected errors
        raise
```

### Retry Logic

```python
import asyncio
from typing import TypeVar, Callable, Any

T = TypeVar('T')

async def retry_on_connection_error(
    func: Callable[[], Awaitable[T]],
    max_retries: int = 3,
    delay: float = 1.0
) -> T:
    """Retry function on connection errors."""

    for attempt in range(max_retries):
        try:
            return await func()
        except ConnectionError as e:
            if attempt == max_retries - 1:
                raise
            print(f"Connection failed (attempt {attempt + 1}/{max_retries}): {e}")
            await asyncio.sleep(delay * (2 ** attempt))  # Exponential backoff

    raise ConnectionError("Max retries exceeded")

# Usage
async def get_users_with_retry():
    """Get users with automatic retry on connection errors."""

    async def _get_users():
        return await AsyncMongoAdapter.from_obj(
            User,
            {
                "url": MONGO_URL,
                "db": DATABASE_NAME,
                "collection": "users"
            },
            many=True
        )

    return await retry_on_connection_error(_get_users)
```

## Practical Example

### Order Management System

Here's a complete example showing how to build an order management system:

```python
class OrderManager:
    """A comprehensive order management system."""

    def __init__(self, mongo_url: str, database: str):
        self.mongo_url = mongo_url
        self.database = database

    async def create_order(
        self,
        user_id: int,
        product_ids: List[int]
    ) -> Order:
        """Create a new order with validation."""

        # Verify user exists and is active
        try:
            user = await AsyncMongoAdapter.from_obj(
                User,
                {
                    "url": self.mongo_url,
                    "db": self.database,
                    "collection": "users",
                    "filter": {"id": user_id, "is_active": True}
                },
                many=False
            )
        except ResourceError:
            raise ValueError(f"Active user {user_id} not found")

        # Verify all products exist and are in stock
        products = await AsyncMongoAdapter.from_obj(
            Product,
            {
                "url": self.mongo_url,
                "db": self.database,
                "collection": "products",
                "filter": {
                    "id": {"$in": product_ids},
                    "in_stock": True
                }
            },
            many=True
        )

        if len(products) != len(product_ids):
            found_ids = {p.id for p in products}
            missing_ids = set(product_ids) - found_ids
            raise ValueError(f"Products not available: {missing_ids}")

        # Calculate total
        total_amount = sum(p.price for p in products)

        # Generate order ID
        order_id = await self._generate_order_id()

        # Create order
        order = Order(
            id=order_id,
            user_id=user_id,
            product_ids=product_ids,
            total_amount=total_amount
        )

        # Save order
        await AsyncMongoAdapter.to_obj(
            order,
            url=self.mongo_url,
            db=self.database,
            collection="orders",
            many=False
        )

        print(f"Order {order.id} created for {user.username} - ${total_amount:.2f}")
        return order

    async def get_user_orders(self, user_id: int) -> List[Order]:
        """Get all orders for a user."""

        orders = await AsyncMongoAdapter.from_obj(
            Order,
            {
                "url": self.mongo_url,
                "db": self.database,
                "collection": "orders",
                "filter": {"user_id": user_id}
            },
            many=True
        )

        return sorted(orders, key=lambda o: o.order_date, reverse=True)

    async def get_order_summary(self, order_id: int) -> dict:
        """Get detailed order information."""

        try:
            # Get order
            order = await AsyncMongoAdapter.from_obj(
                Order,
                {
                    "url": self.mongo_url,
                    "db": self.database,
                    "collection": "orders",
                    "filter": {"id": order_id}
                },
                many=False
            )

            # Get user
            user = await AsyncMongoAdapter.from_obj(
                User,
                {
                    "url": self.mongo_url,
                    "db": self.database,
                    "collection": "users",
                    "filter": {"id": order.user_id}
                },
                many=False
            )

            # Get products
            products = await AsyncMongoAdapter.from_obj(
                Product,
                {
                    "url": self.mongo_url,
                    "db": self.database,
                    "collection": "products",
                    "filter": {"id": {"$in": order.product_ids}}
                },
                many=True
            )

            return {
                "order": order,
                "user": user,
                "products": products,
                "summary": {
                    "order_id": order.id,
                    "customer": user.username,
                    "items": len(products),
                    "total": order.total_amount,
                    "status": order.status
                }
            }

        except ResourceError:
            raise ValueError(f"Order {order_id} not found")

    async def _generate_order_id(self) -> int:
        """Generate next order ID."""

        orders = await AsyncMongoAdapter.from_obj(
            Order,
            {
                "url": self.mongo_url,
                "db": self.database,
                "collection": "orders"
            },
            many=True
        )

        if not orders:
            return 1

        return max(order.id for order in orders) + 1

# Usage example
async def demo_order_system():
    """Demonstrate the order management system."""

    order_manager = OrderManager(MONGO_URL, DATABASE_NAME)

    # Create an order
    order = await order_manager.create_order(
        user_id=1,
        product_ids=[1, 2, 3]
    )

    # Get user's orders
    user_orders = await order_manager.get_user_orders(1)
    print(f"User has {len(user_orders)} orders")

    # Get order summary
    summary = await order_manager.get_order_summary(order.id)
    print(f"Order summary: {summary['summary']}")
```

## Performance Tips

### 1. Batch Operations

Always prefer batch operations over individual operations:

```python
# ✅ Good: Batch insert
users = [User(...) for _ in range(100)]
await AsyncMongoAdapter.to_obj(
    users,
    url=MONGO_URL,
    db=DATABASE_NAME,
    collection="users",
    many=True
)

# ❌ Bad: Individual inserts
for user in users:
    await AsyncMongoAdapter.to_obj(
        user,
        url=MONGO_URL,
        db=DATABASE_NAME,
        collection="users",
        many=False
    )
```

### 2. Efficient Filtering

Use specific filters to reduce data transfer:

```python
# ✅ Good: Specific filter
users = await AsyncMongoAdapter.from_obj(
    User,
    {
        "url": MONGO_URL,
        "db": DATABASE_NAME,
        "collection": "users",
        "filter": {"id": {"$in": [1, 2, 3]}}
    },
    many=True
)

# ❌ Bad: Broad query then filter in Python
all_users = await AsyncMongoAdapter.from_obj(User, config, many=True)
filtered_users = [u for u in all_users if u.id in [1, 2, 3]]
```

### 3. Connection Management

```python
# The adapter handles connections automatically
# Each operation creates a new connection
# Connections are properly closed after use

# For high-frequency operations, consider connection pooling at the application level
```

### 4. Memory Management

```python
# For large datasets, consider pagination
async def get_users_paginated(page: int, size: int = 100):
    """Get users with pagination."""

    skip = page * size
    # Note: MongoDB skip/limit would be implemented differently
    # This is a simplified example

    users = await AsyncMongoAdapter.from_obj(
        User,
        {
            "url": MONGO_URL,
            "db": DATABASE_NAME,
            "collection": "users",
            "filter": {}  # Add pagination logic here
        },
        many=True
    )

    return users[skip:skip + size]
```

## Best Practices

### 1. Model Design

```python
# ✅ Good: Clear, specific models
class User(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        # Add any Pydantic config here
        validate_assignment = True

# ❌ Bad: Generic, unclear models
class Data(BaseModel):
    stuff: dict
    things: list
```

### 2. Error Handling Strategy

```python
# ✅ Good: Specific exception handling
try:
    user = await get_user(user_id)
except ResourceError:
    # Handle missing resource
    return None
except ConnectionError:
    # Handle connection issues
    raise ServiceUnavailableError()
except AdapterValidationError as e:
    # Handle validation errors
    raise BadRequestError(f"Invalid data: {e}")

# ❌ Bad: Generic exception handling
try:
    user = await get_user(user_id)
except Exception:
    return None
```

### 3. Configuration Management

```python
# ✅ Good: Centralized configuration
class MongoConfig:
    def __init__(self):
        self.url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
        self.database = os.getenv("MONGO_DB", "myapp")
        self.timeout = int(os.getenv("MONGO_TIMEOUT", "5000"))

config = MongoConfig()

# ❌ Bad: Hardcoded values
MONGO_URL = "mongodb://localhost:27017"  # Hardcoded
```

### 4. Testing

```python
import pytest
from unittest.mock import patch

@pytest.mark.asyncio
async def test_create_user():
    """Test user creation."""

    with patch('pydapter.extras.async_mongo_.AsyncMongoAdapter.to_obj') as mock_to_obj:
        mock_to_obj.return_value = {"inserted_count": 1}

        user = User(id=1, username="test", email="test@example.com", age=25)
        result = await AsyncMongoAdapter.to_obj(
            user,
            url="mongodb://test",
            db="test_db",
            collection="users",
            many=False
        )

        assert result["inserted_count"] == 1
        mock_to_obj.assert_called_once()
```

### 5. Production Considerations

```python
# ✅ Production setup
async def create_production_order_manager():
    """Create order manager with production settings."""

    return OrderManager(
        mongo_url=os.getenv("MONGO_URL"),
        database=os.getenv("MONGO_DATABASE")
    )

# Add proper logging
import logging

logger = logging.getLogger(__name__)

async def safe_create_order(*args, **kwargs):
    """Create order with proper logging."""

    try:
        order = await order_manager.create_order(*args, **kwargs)
        logger.info(f"Order {order.id} created successfully")
        return order
    except Exception as e:
        logger.error(f"Failed to create order: {e}", exc_info=True)
        raise
```

## Summary

The AsyncMongoAdapter provides a powerful, async-first approach to working with
MongoDB in Python applications. Key benefits include:

- **Seamless Integration**: Direct conversion between Pydantic models and
  MongoDB documents
- **Async Performance**: Full async/await support for non-blocking operations
- **Robust Error Handling**: Specific exceptions for different error scenarios
- **MongoDB Query Support**: Full MongoDB query syntax support
- **Type Safety**: Pydantic model validation ensures data integrity

### Quick Reference

```python
# Basic operations
await AsyncMongoAdapter.to_obj(
    model, url=url, db=db, collection=coll, many=False
)
await AsyncMongoAdapter.from_obj(Model, config, many=True)

# Error handling
try:
    result = await AsyncMongoAdapter.from_obj(...)
except (ConnectionError, ResourceError, AdapterValidationError) as e:
    handle_error(e)

# Configuration
config = {
    "url": "mongodb://localhost:27017",
    "db": "database_name",
    "collection": "collection_name",
    "filter": {"field": "value"}  # Optional
}
```

This tutorial provides a comprehensive foundation for using Pydapter's async
MongoDB adapter in real-world applications. Remember to always handle errors
appropriately, use batch operations for performance, and follow MongoDB best
practices for schema design and querying.
