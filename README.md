# 🔄 Pydapter: Universal Data Adapter Framework

[![codecov](https://codecov.io/github/khive-ai/pydapter/graph/badge.svg?token=FAE47FY26T)](https://codecov.io/github/khive-ai/pydapter)
[![PyPI version](https://img.shields.io/pypi/v/pydapter.svg)](https://pypi.org/project/pydapter/)
![PyPI - Downloads](https://img.shields.io/pypi/dm/pydapter?color=blue)
![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
[![License](https://img.shields.io/github/license/ohdearquant/pydapter.svg)](https://github.com/ohdearquant/pydapter/blob/main/LICENSE)

> **Stop writing custom data integration code.** Pydapter provides one consistent interface to connect any model with any data source.

**🔥 What makes Pydapter different:**
- **Universal Interface**: Same pattern works for SQL, MongoDB, CSV, JSON, Neo4j, vector databases, and more
- **Beyond Pydantic**: Dynamic method support works with any model framework, not just Pydantic
- **Production Ready**: Full async support, connection pooling, comprehensive error handling
- **Type Safe**: Protocol-based design with complete type hints

---

## ⚡ See the Power: One Interface, Any Data Source

The same simple pattern works everywhere:

```python
from pydantic import BaseModel
from pydapter.adapters.json_ import JSONAdapter
from pydapter.extras.postgres_ import PostgresAdapter
from pydapter.extras.mongo_ import MongoAdapter
from pydapter.adapters.csv_ import CsvAdapter

class User(BaseModel):
    name: str
    email: str
    age: int

# Same pattern for JSON
users = JSONAdapter.from_obj(User, json_data, many=True)
JSONAdapter.to_obj(users, many=True)

# Same pattern for PostgreSQL
users = PostgresAdapter.from_obj(User, {
    "engine_url": "postgresql://localhost/db",
    "table": "users"
}, many=True)
PostgresAdapter.to_obj(users, engine_url="postgresql://localhost/db", table="users", many=True)

# Same pattern for MongoDB
users = MongoAdapter.from_obj(User, {
    "url": "mongodb://localhost:27017",
    "db": "app",
    "collection": "users"
}, many=True)
MongoAdapter.to_obj(users, url="mongodb://localhost:27017", db="app", collection="users", many=True)

# Same pattern for CSV
users = CsvAdapter.from_obj(User, csv_data, many=True)
CsvAdapter.to_obj(users, many=True)
```

**One interface. Any data source. Complete type safety.**

---

## 🚀 Revolutionary: Works with Any Model Framework

Pydapter v1.0.0 introduces **dynamic method support** - use it with any model system:

```python
# Works with Pydantic (default)
user = JSONAdapter.from_obj(PydanticUser, json_data)

# Works with custom model classes
class CustomNode:
    def from_dict(self, data): ...
    def to_dict(self): ...

# Specify custom methods
node = JSONAdapter.from_obj(CustomNode, json_data, adapt_meth="from_dict")
json_out = JSONAdapter.to_obj(node, adapt_meth="to_dict")

# Works with dataclasses, attrs, or any class with validation methods
result = PostgresAdapter.from_obj(DataclassModel, db_config, adapt_meth="from_dict")
```

**Finally, a universal adapter that works with your existing model system.**

---

## 🎯 Complete Data Source Coverage

| **Category** | **Adapters** | **Async Support** |
|-------------|-------------|------------------|
| **Databases** | PostgreSQL, MongoDB, Neo4j, SQLite, MySQL | ✅ |
| **Vector DBs** | Qdrant, Weaviate | ✅ |
| **Files** | JSON, CSV, TOML, Excel | ✅ |
| **Data Science** | Pandas DataFrame, Series | ✅ |
| **Cloud/AI** | Memvid (video memory) | ✅ |

---

## 📦 Installation

```bash
# Core installation
pip install pydapter

# Database support
pip install "pydapter[postgres,mongo,neo4j,qdrant]"

# All features
pip install "pydapter[all]"
```

---

## 🔥 Key Features

### 🎯 **Universal Interface**
- **One Pattern Everywhere**: Master one interface, work with any data source
- **Consistent API**: Same `from_obj()`/`to_obj()` pattern across all adapters
- **Batch Operations**: Built-in `many=True` support for collections

### ⚡ **Production Ready**
- **Full Async Support**: Async versions of all major adapters
- **Connection Pooling**: Efficient resource management for databases
- **Comprehensive Error Handling**: Detailed exceptions with context
- **Type Safety**: Protocol-based design with complete type hints

### 🔧 **Dynamic & Flexible**
- **Custom Methods**: Use any validation/serialization methods, not just Pydantic
- **Extensible**: Protocol-based architecture for custom adapters
- **Framework Agnostic**: Works with Pydantic, dataclasses, attrs, custom classes

### 🛡️ **Enterprise Grade**
- **Validation**: Rich error reporting with field-level details
- **Testing**: >90% code coverage with comprehensive integration tests
- **Documentation**: Complete guides and API reference
- **Backward Compatible**: Smooth upgrade path with v1.0.0 stability

---

## 🚀 Quick Start

### Basic Usage
```python
from pydantic import BaseModel
from pydapter.adapters.json_ import JSONAdapter

class User(BaseModel):
    name: str
    email: str
    active: bool = True

# Parse JSON
user = JSONAdapter.from_obj(User, '{"name": "Alice", "email": "alice@example.com"}')

# Generate JSON
json_data = JSONAdapter.to_obj(user)
```

### Database Integration
```python
from pydapter.extras.postgres_ import PostgresAdapter

# Query database
users = PostgresAdapter.from_obj(User, {
    "engine_url": "postgresql://localhost/myapp",
    "table": "users",
    "selectors": {"active": True}  # WHERE active = true
}, many=True)

# Insert data
new_user = User(name="Bob", email="bob@example.com")
PostgresAdapter.to_obj(new_user,
    engine_url="postgresql://localhost/myapp",
    table="users"
)
```

### Async Operations
```python
import asyncio
from pydapter.extras.async_mongo_ import AsyncMongoAdapter

async def main():
    # Async MongoDB query
    users = await AsyncMongoAdapter.from_obj(User, {
        "url": "mongodb://localhost:27017",
        "db": "myapp",
        "collection": "users",
        "filter": {"active": True}
    }, many=True)

    # Async insert
    await AsyncMongoAdapter.to_obj(users,
        url="mongodb://localhost:27017",
        db="myapp",
        collection="users_backup",
        many=True
    )

asyncio.run(main())
```

---

## 🔥 Advanced Examples

### Vector Search with Qdrant
```python
from pydapter.extras.qdrant_ import QdrantAdapter
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')

class Document(BaseModel):
    id: str
    title: str
    content: str
    embedding: list[float] = []

# Store document with embedding
doc = Document(id="1", title="AI Guide", content="Introduction to AI...")
doc.embedding = model.encode(doc.content).tolist()

QdrantAdapter.to_obj(doc, collection="docs", url="http://localhost:6333")

# Vector similarity search
query_vector = model.encode("What is artificial intelligence?").tolist()
results = QdrantAdapter.from_obj(Document, {
    "collection": "docs",
    "query_vector": query_vector,
    "top_k": 5,
    "url": "http://localhost:6333"
}, many=True)
```

### Graph Database with Neo4j
```python
from pydapter.extras.neo4j_ import Neo4jAdapter

class Person(BaseModel):
    name: str
    age: int
    skills: list[str] = []

# Store in graph database
person = Person(name="Alice", age=30, skills=["Python", "AI"])
Neo4jAdapter.to_obj(person,
    url="bolt://localhost:7687",
    auth=("neo4j", "password"),
    label="Person",
    merge_on="name"
)

# Cypher-like queries
developers = Neo4jAdapter.from_obj(Person, {
    "url": "bolt://localhost:7687",
    "auth": ("neo4j", "password"),
    "label": "Person",
    "where": "'Python' IN n.skills"
}, many=True)
```

### Custom Model Integration
```python
from dataclasses import dataclass
from pydapter.adapters.json_ import JSONAdapter

@dataclass
class Product:
    name: str
    price: float

    @classmethod
    def from_dict(cls, data):
        return cls(**data)

    def to_dict(self):
        return {"name": self.name, "price": self.price}

# Use custom methods instead of Pydantic defaults
product = JSONAdapter.from_obj(Product,
    '{"name": "Laptop", "price": 999.99}',
    adapt_meth="from_dict"  # Custom deserialization method
)

json_data = JSONAdapter.to_obj(product,
    adapt_meth="to_dict"    # Custom serialization method
)
```

---

## 🛡️ Error Handling

Comprehensive exception hierarchy for debugging:

```python
from pydapter.exceptions import (
    ValidationError, ParseError, ConnectionError,
    QueryError, ResourceError
)

try:
    users = PostgresAdapter.from_obj(User, config, many=True)
except ConnectionError as e:
    print(f"Database connection failed: {e}")
except QueryError as e:
    print(f"Query error: {e}")
    print(f"Query: {e.query}")
except ValidationError as e:
    print(f"Data validation failed: {e}")
    for error in e.errors():
        print(f"  {error['loc']}: {error['msg']}")
```

---

## 🔧 Create Custom Adapters

Extend pydapter with your own data sources:

```python
from typing import TypeVar
from pydantic import BaseModel
from pydapter.core import Adapter

T = TypeVar("T", bound=BaseModel)

class MyCustomAdapter(Adapter[T]):
    obj_key = "my_format"

    @classmethod
    def from_obj(cls, subj_cls: type[T], obj: Any, /, *,
                 many: bool = False, adapt_meth: str = "model_validate", **kw):
        # Your deserialization logic
        data = parse_my_format(obj)
        if many:
            return [getattr(subj_cls, adapt_meth)(item) for item in data]
        return getattr(subj_cls, adapt_meth)(data)

    @classmethod
    def to_obj(cls, subj: T | list[T], /, *,
               many: bool = False, adapt_meth: str = "model_dump", **kw):
        # Your serialization logic
        items = subj if isinstance(subj, list) else [subj]
        data = [getattr(item, adapt_meth)() for item in items]
        return generate_my_format(data)
```

---

## 📚 Documentation & Resources

- **📖 [Full Documentation](https://khive-ai.github.io/pydapter/)** - Complete guides and API reference
- **🚀 [Getting Started Guide](https://khive-ai.github.io/pydapter/getting_started/)** - Step-by-step tutorials
- **🏗️ [Architecture Guide](https://khive-ai.github.io/pydapter/guides/architecture/)** - Understanding the design
- **🔧 [Creating Custom Adapters](https://khive-ai.github.io/pydapter/guides/creating-adapters/)** - Extend pydapter
- **⚡ [Async Patterns](https://khive-ai.github.io/pydapter/guides/async-patterns/)** - Best practices for async code

---

## 🤝 Contributing

We welcome contributions! Pydapter is built by the community, for the community.

1. **Fork** the repository
2. **Create** your feature branch (`git checkout -b feature/amazing-feature`)
3. **Test** locally (`python scripts/ci.py`)
4. **Commit** your changes (`git commit -m 'Add amazing feature'`)
5. **Push** to the branch (`git push origin feature/amazing-feature`)
6. **Open** a Pull Request

### 🧪 Local Development
```bash
# Run all checks
python scripts/ci.py

# Skip Docker-dependent integration tests
python scripts/ci.py --skip-integration

# Quick lint/format check
python scripts/ci.py --skip-unit --skip-integration --skip-type-check --skip-coverage
```

---

## 🙏 Acknowledgments

**Pydapter is built on the shoulders of giants:**
- **[Pydantic](https://docs.pydantic.dev/)** - The foundation for type-safe data validation
- **SQLAlchemy, Motor, Neo4j Driver, Qdrant Client** - The excellent libraries we integrate with
- **Our Contributors** - The amazing developers who make this project possible

---

## 📄 License

Apache-2.0 License - see [LICENSE](LICENSE) file for details.

---

<div align="center">

**🔄 Ready to stop writing custom data integration code?**

**Install Pydapter today and experience the power of universal data adaptation.**

```bash
pip install pydapter
```

*One interface. Any data source. Complete type safety.*

---

**Built with ❤️ by the Pydapter community**

[⭐ Star us on GitHub](https://github.com/khive-ai/pydapter) • [📖 Read the docs](https://khive-ai.github.io/pydapter/) • [💬 Join discussions](https://github.com/khive-ai/pydapter/discussions)

</div>
