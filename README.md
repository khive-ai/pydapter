# 🔄 Pydapter: Infrastructure for the Post-Database World

[![codecov](https://codecov.io/github/khive-ai/pydapter/graph/badge.svg?token=FAE47FY26T)](https://codecov.io/github/khive-ai/pydapter)
[![PyPI version](https://img.shields.io/pypi/v/pydapter.svg)](https://pypi.org/project/pydapter/)
![PyPI - Downloads](https://img.shields.io/pypi/dm/pydapter?color=blue)
![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
[![License](https://img.shields.io/github/license/ohdearquant/pydapter.svg)](https://github.com/ohdearquant/pydapter/blob/main/LICENSE)
[![Discord](https://img.shields.io/discord/YOUR_SERVER_ID?color=5865F2&logo=discord&logoColor=white)](https://discord.gg/JDj9ENhUE8)

---

## The Problem We're Solving

Modern applications don't fit in one database anymore.

Your LLM extracts insights that need PostgreSQL for transactions, Qdrant for vector search, Neo4j for relationships. Each integration means different APIs, different patterns, weeks of custom code.

**We calculated it: engineers spend 40% of their time on data plumbing instead of building intelligence.**

## Why Pydapter Exists

We believe the data layer should be invisible. When you build an application, you should think about your domain models and business logic, not about cursor management or connection pooling.

**Pydapter makes storage a deployment decision, not an architecture decision.**

---
## The Paradigm Shift

Traditional thinking: Choose a database, design around its constraints, live with the tradeoffs forever.

**The new reality: Data flows where it provides the most value.**

```python
# One model, multiple destinations based on need
from pydantic import BaseModel

class CustomerInsight(BaseModel):
    """Your domain model - doesn't care about storage"""
    customer_id: str
    insight_text: str
    embedding: list[float]
    relationships: dict

# Same model flows to different systems based on purpose
PostgresAdapter.to_obj(insight, table="insights")        # Transactional storage
QdrantAdapter.to_obj(insight, collection="vectors")      # Similarity search
Neo4jAdapter.to_obj(insight, label="Insight")           # Relationship mapping
```

**When integration friction disappears, architecture becomes liquid.**

---

## What This Enables

### 1. **Multi-Modal AI Pipelines**
Your LLM processes a document and extracts entities. Those entities need to be stored for compliance (PostgreSQL), searchable by meaning (vector database), and analyzed for relationships (graph database). With Pydapter, it's the same three lines of code for each destination.

### 2. **Storage-Agnostic Applications**
Deploy the same application on-premise with PostgreSQL, in AWS with DynamoDB, or at the edge with SQLite. Just change configuration, not code.

### 3. **Evolutionary Architecture**
Start with PostgreSQL. Add vector search when needed. Migrate to a graph database for complex relationships. Your application code doesn't change - only deployment configuration evolves.

### 4. **True Vendor Independence**
No more lock-in through proprietary APIs. Switch between cloud providers, databases, or storage systems without touching application logic.

---

## How It Works

One consistent interface for everything:

```python
# Read from any source
data = Adapter.from_obj(YourModel, source_config, many=True)

# Write to any destination
Adapter.to_obj(data, destination_config, many=True)
```

Whether it's a local JSON file or a distributed database cluster, the pattern never changes.

### Real Example: AI Content Pipeline

```python
from pydantic import BaseModel
from pydapter.extras.postgres_ import PostgresAdapter
from pydapter.extras.qdrant_ import QdrantAdapter
from pydapter.extras.neo4j_ import Neo4jAdapter


class Document(BaseModel):
    id: str
    content: str
    summary: str
    embedding: list[float]
    entities: list[str]

# Your AI pipeline extracts information
doc = ai_pipeline.process(raw_document)

# One model, multiple destinations
PostgresAdapter.to_obj(doc,
    engine_url="postgresql://localhost/app",
    table="documents"
)

QdrantAdapter.to_obj(doc,
    collection="documents",
    url="http://localhost:6333"
)

Neo4jAdapter.to_obj(doc,
    url="bolt://localhost:7687",
    label="Document"
)
```

---

## Why Framework Agnostic Matters

Pydapter works with **any** model framework, not just Pydantic:

```python
# Works with dataclasses
@dataclass
class Product:
    name: str
    price: float

    def to_dict(self):
        return {"name": self.name, "price": self.price}

# Use your existing serialization methods
PostgresAdapter.to_obj(product,
    adapt_meth="to_dict",  # Your method
    table="products"
)

# Works with custom classes, attrs, or any validation framework
```

**No need to rewrite your models. Pydapter adapts to you.**

---

## Production Ready

- **Battle Tested**: >90% test coverage, used in production systems
- **Enterprise Features**: Full async support, connection pooling, comprehensive error handling
- **Type Safe**: Complete type hints and protocol-based design
- **Performance**: Minimal overhead - the bottleneck is your database, not Pydapter

---

## Data Source Coverage

| **Category** | **Supported** | **Async** |
|-------------|--------------|-----------|
| **SQL Databases** | PostgreSQL, MySQL, SQLite | ✅ |
| **NoSQL** | MongoDB, DynamoDB | ✅ |
| **Vector Stores** | Qdrant, Weaviate, Pinecone | ✅ |
| **Graph Databases** | Neo4j, ArangoDB | ✅ |
| **Files** | JSON, CSV, Excel, Parquet | ✅ |

---

## Installation

```bash
pip install pydapter

# Add specific integrations as needed
pip install "pydapter[postgres,mongo,qdrant]"
```

---

## Real-World Patterns

### Pattern 1: Multi-Stage AI Pipeline

```python
# LLM processes document → multiple specialized storage systems
class ProcessedDocument(BaseModel):
    doc_id: str
    content: str
    summary: str
    entities: list[str]
    embedding: list[float]

# Stage 1: Store for compliance
PostgresAdapter.to_obj(doc, table="documents")

# Stage 2: Enable semantic search
QdrantAdapter.to_obj(doc, collection="docs")

# Stage 3: Map entity relationships
Neo4jAdapter.to_obj(doc, label="Document")
```

### Pattern 2: Environment-Specific Deployment

```python
import os

# Same code, different storage based on environment
if os.getenv("ENVIRONMENT") == "local":
    adapter = SqliteAdapter
    config = {"db_path": "local.db"}
elif os.getenv("ENVIRONMENT") == "aws":
    adapter = DynamoAdapter
    config = {"table": "prod-data", "region": "us-east-1"}
else:
    adapter = PostgresAdapter
    config = {"engine_url": os.getenv("DATABASE_URL")}

# Application code remains unchanged
data = adapter.from_obj(Model, config, many=True)
```

### Pattern 3: Gradual Migration

```python
# Migrate from MongoDB to PostgreSQL without downtime
async def migrate_with_dual_writes():
    # Read from old system
    data = await AsyncMongoAdapter.from_obj(Model, mongo_config, many=True)

    # Write to both during migration
    await AsyncMongoAdapter.to_obj(data, mongo_config, many=True)
    await AsyncPostgresAdapter.to_obj(data, postgres_config, many=True)

    # Later: switch reads to PostgreSQL, remove MongoDB
```

---

## Advanced Features

### Async-First Design

All major adapters support async operations for modern applications:

```python
async with AsyncPostgresAdapter() as adapter:
    results = await adapter.from_obj(Model, config, many=True)
    await adapter.to_obj(new_data, config, many=True)
```

### Custom Serialization

Use your existing model methods:

```python
class CustomModel:
    def to_dict(self): ...

    @classmethod
    def from_dict(cls, data): ...

# Pydapter uses your methods
data = Adapter.from_obj(CustomModel, source, adapt_meth="from_dict")
Adapter.to_obj(data, destination, adapt_meth="to_dict")
```

### Error Handling

Rich exceptions with context for debugging:

```python
from pydapter.exceptions import ValidationError, ConnectionError

try:
    data = PostgresAdapter.from_obj(Model, config)
except ConnectionError as e:
    # Detailed connection diagnostics
    logger.error(f"Database unreachable: {e}")
except ValidationError as e:
    # Field-level validation errors
    for error in e.errors():
        logger.error(f"{error['loc']}: {error['msg']}")
```

---

## Creating Custom Adapters

Extend Pydapter for your specific needs:

```python
from pydapter.core import Adapter

class RedisAdapter(Adapter[T]):
    """Example: Redis key-value adapter"""

    @classmethod
    def from_obj(cls, model_cls, config, /, *, many=False, **kw):
        client = redis.from_url(config["url"])
        if many:
            keys = client.keys(config.get("pattern", "*"))
            return [model_cls.model_validate_json(client.get(k)) for k in keys]
        return model_cls.model_validate_json(client.get(config["key"]))

    @classmethod
    def to_obj(cls, data, /, *, many=False, **kw):
        client = redis.from_url(kw["url"])
        items = data if many else [data]
        for item in items:
            client.set(f"{kw['prefix']}:{item.id}", item.model_dump_json())
```

---

## Why v1.0.0 Matters

This isn't just another release. It's a commitment.

**API Stability**: The patterns you learn today will work in v2.0. We've spent two years refining the interface to be both powerful and permanent.

**Production Trust**: Battle-tested in real systems handling millions of records. When you build on Pydapter, you build on solid ground.

**The Standard**: We're establishing how modern applications should handle data. One interface, everywhere.

---

## The Philosophy

We're not building another ORM or database wrapper. We're building infrastructure for a fundamental shift in how applications relate to data.

**Three principles guide everything:**

1. **Storage is tactical, not strategic** - Choose databases based on current needs, not future fears
2. **Data should flow like water** - Between systems, across boundaries, without friction
3. **Applications outlive their databases** - Your business logic shouldn't be coupled to storage decisions

---

## Documentation

- **[Full Documentation](https://khive-ai.github.io/pydapter/)** - Complete API reference and guides
- **[Architecture Overview](https://khive-ai.github.io/pydapter/guides/architecture/)** - Understanding the design
- **[Getting Started](https://khive-ai.github.io/pydapter/getting_started/)** - From zero to production

---

## Contributing

Pydapter is built by the community, for the community. We believe in the vision of invisible data layers and need your help to make it reality.

See our [Contributing Guide](https://github.com/khive-ai/pydapter/blob/main/CONTRIBUTING.md) to get started.

---

## License

Apache-2.0 License - see [LICENSE](LICENSE) for details.

---

<div align="center">

## The Future is Fluid

In the post-database world, data flows where it provides value. Storage adapts to your needs. Architecture evolves without rewrites.

**Join us in building infrastructure for applications that outlive their databases.**

```bash
pip install pydapter
```

- **[GitHub](https://github.com/khive-ai/pydapter)**
- **[Documentation](https://khive-ai.github.io/pydapter/)**
- **[Discussions](https://github.com/khive-ai/pydapter/discussions)**

---

*What will you build when the data layer disappears?*

</div>
