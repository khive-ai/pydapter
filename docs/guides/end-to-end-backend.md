# Building Multi-Database Backends with Pydapter

## Overview

This guide shows how to build flexible backends that work with multiple database
backends using pydapter's protocol and adapter system, with async PostgreSQL as
the primary database.

## Architecture Pattern

```text
Models (Protocols) → Adapters (DB-specific) → Registry (Unified Interface)
```

**Core Concept**: Define your models with protocols, implement database-specific
adapters, use registry for database abstraction.

## 1. Define Protocol-Based Models

```python
from pydantic import BaseModel
from pydapter.protocols import IdentifiableMixin, TemporalMixin
from uuid import UUID
from datetime import datetime

class User(BaseModel, IdentifiableMixin, TemporalMixin):
    id: UUID
    created_at: datetime
    updated_at: datetime
    name: str
    email: str
    active: bool = True

class Post(BaseModel, IdentifiableMixin, TemporalMixin):
    id: UUID
    created_at: datetime
    updated_at: datetime
    title: str
    content: str
    author_id: UUID
    published: bool = False
```

## 2. Database Adapter Pattern

```python
from pydapter.async_core import AsyncAdapter

class AsyncPostgresUserAdapter(AsyncAdapter[User]):
    obj_key = "postgres_user"

    @classmethod
    async def from_obj(cls, subj_cls: type[User], obj: dict, /, *, many=False, **kw):
        conn_string = obj["connection_string"]
        # Query logic here
        pass

    @classmethod
    async def to_obj(cls, subj: User | list[User], /, *, many=False, **kw):
        # Insert/update logic here
        pass

# Similar adapters for other databases
class AsyncMongoUserAdapter(AsyncAdapter[User]):
    obj_key = "mongo_user"
    # MongoDB-specific implementation

class AsyncNeo4jUserAdapter(AsyncAdapter[User]):
    obj_key = "neo4j_user"
    # Neo4j-specific implementation
```

## 3. Repository Pattern with Registry

```python
from pydapter.async_core import AsyncAdapterRegistry

class UserRepository:
    def __init__(self, registry: AsyncAdapterRegistry, default_adapter: str = "postgres_user"):
        self.registry = registry
        self.default_adapter = default_adapter

    async def get_by_id(self, user_id: UUID, adapter_key: str = None) -> User | None:
        adapter_key = adapter_key or self.default_adapter
        query_config = {
            "connection_string": self._get_connection_string(adapter_key),
            "query": "SELECT * FROM users WHERE id = $1",
            "params": [user_id]
        }
        return await self.registry.adapt_from(User, query_config, obj_key=adapter_key)

    async def create(self, user: User, adapter_key: str = None) -> User:
        adapter_key = adapter_key or self.default_adapter
        config = {
            "connection_string": self._get_connection_string(adapter_key),
            "table": "users"
        }
        return await self.registry.adapt_to(user, obj_key=adapter_key, **config)

    def _get_connection_string(self, adapter_key: str) -> str:
        # Configuration lookup
        pass
```

## 4. Service Layer

```python
class UserService:
    def __init__(self, user_repo: UserRepository, post_repo: PostRepository):
        self.user_repo = user_repo
        self.post_repo = post_repo

    async def create_user_with_welcome_post(self, name: str, email: str) -> tuple[User, Post]:
        # Create user in primary database (PostgreSQL)
        user = User(id=uuid4(), name=name, email=email,
                   created_at=datetime.now(), updated_at=datetime.now())
        created_user = await self.user_repo.create(user)

        # Create welcome post
        welcome_post = Post(
            id=uuid4(), title="Welcome!", content=f"Welcome {name}!",
            author_id=created_user.id, created_at=datetime.now(), updated_at=datetime.now()
        )
        created_post = await self.post_repo.create(welcome_post)

        # Optionally replicate to other databases for analytics
        await self._replicate_to_analytics(created_user)

        return created_user, created_post

    async def _replicate_to_analytics(self, user: User):
        """Replicate user data to analytics database (e.g., MongoDB)"""
        try:
            await self.user_repo.create(user, adapter_key="mongo_user")
        except Exception as e:
            # Log error but don't fail main operation
            logger.warning(f"Failed to replicate user to analytics: {e}")
```

## 5. Configuration and Setup

```python
# Database configuration
DATABASE_CONFIG = {
    "postgres": {
        "connection_string": "postgresql://user:pass@localhost/main",
        "primary": True
    },
    "mongo": {
        "connection_string": "mongodb://localhost:27017/analytics",
        "use_for": ["analytics", "caching"]
    },
    "neo4j": {
        "connection_string": "bolt://localhost:7687",
        "use_for": ["relationships", "recommendations"]
    }
}

# Registry setup
async def create_registry() -> AsyncAdapterRegistry:
    registry = AsyncAdapterRegistry()

    # Register all adapters
    registry.register(AsyncPostgresUserAdapter)
    registry.register(AsyncMongoUserAdapter)
    registry.register(AsyncNeo4jUserAdapter)
    # ... register adapters for other models

    return registry

# Application factory
async def create_app():
    registry = await create_registry()

    user_repo = UserRepository(registry, default_adapter="postgres_user")
    post_repo = PostRepository(registry, default_adapter="postgres_post")

    user_service = UserService(user_repo, post_repo)

    return user_service
```

## 6. FastAPI Integration

```python
from fastapi import FastAPI, Depends

app = FastAPI()

async def get_user_service() -> UserService:
    return await create_app()

@app.post("/users")
async def create_user(
    user_data: dict,
    service: UserService = Depends(get_user_service)
):
    user, welcome_post = await service.create_user_with_welcome_post(
        name=user_data["name"],
        email=user_data["email"]
    )
    return {"user": user.model_dump(), "welcome_post": welcome_post.model_dump()}

@app.get("/users/{user_id}")
async def get_user(
    user_id: UUID,
    source: str = "postgres",  # Allow client to specify database
    service: UserService = Depends(get_user_service)
):
    adapter_map = {
        "postgres": "postgres_user",
        "mongo": "mongo_user",
        "neo4j": "neo4j_user"
    }

    user = await service.user_repo.get_by_id(
        user_id,
        adapter_key=adapter_map.get(source, "postgres_user")
    )

    if not user:
        raise HTTPException(404, "User not found")

    return user.model_dump()
```

## Key Benefits

### 1. Database Flexibility

- **Primary Database**: PostgreSQL for ACID transactions
- **Analytics Database**: MongoDB for flexible schema and aggregations
- **Graph Database**: Neo4j for relationship queries
- **Easy Migration**: Change adapters without changing business logic

### 2. Protocol Consistency

- Models work across all databases through protocols
- Type safety maintained regardless of storage backend
- Consistent validation and serialization

### 3. Incremental Adoption

- Start with one database, add others as needed
- Gradual migration between databases
- A/B testing with different storage backends

## Common Patterns

### Multi-Database Queries

```python
async def get_user_with_recommendations(self, user_id: UUID):
    # Get user from primary database
    user = await self.user_repo.get_by_id(user_id, "postgres_user")

    # Get recommendations from graph database
    recommendations = await self.recommendation_service.get_for_user(
        user_id, adapter_key="neo4j_recommendation"
    )

    return {"user": user, "recommendations": recommendations}
```

### Data Synchronization

```python
async def sync_user_across_databases(self, user: User):
    """Ensure user exists in all required databases"""
    tasks = [
        self.user_repo.create(user, "postgres_user"),
        self.user_repo.create(user, "mongo_user"),
        self.user_repo.create(user, "neo4j_user"),
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Handle partial failures
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Failed to sync user to database {i}: {result}")
```

## Deployment Considerations

### Environment Configuration

```python
# Production: Use environment variables
POSTGRES_URL = os.getenv("DATABASE_URL")
MONGO_URL = os.getenv("MONGO_URL")
NEO4J_URL = os.getenv("NEO4J_URL")

# Development: Use local databases
# Testing: Use in-memory or test databases
```

### Monitoring and Observability

- Log database adapter usage
- Monitor query performance across databases
- Track replication lag and sync errors
- Use health checks for each database

This pattern provides a robust foundation for building scalable backends that
can evolve with changing requirements while maintaining clean separation of
concerns.
