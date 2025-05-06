# Pydapter: Elegant Adapters for Pydantic Models

[![PyPI version](https://img.shields.io/pypi/v/pydapter.svg)](https://pypi.org/project/pydapter/)
![PyPI - Downloads](https://img.shields.io/pypi/dm/pydapter?color=blue)
![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)
[![License](https://img.shields.io/github/license/ohdearquant/pydapter.svg)](https://github.com/ohdearquant/pydapter/blob/main/LICENSE)

Pydapter is a lightweight, type-safe adapter toolkit for Pydantic that enables
seamless conversion between Pydantic models and various data formats and storage
systems.

## Features

- 🔀 **Two-way Conversion**: Transform data between Pydantic models and external
  formats/sources
- 🧩 **Adaptable Mixin**: Add conversion capabilities directly to your models
- 🔄 **Async Support**: Full support for asynchronous operations
- 📊 **Multiple Formats**: Support for JSON, CSV, TOML, pandas DataFrames,
  Excel, and more
- 💾 **Database Integration**: Connect to PostgreSQL, MongoDB, Neo4j, Qdrant,
  and others
- 🛡️ **Type-Safe**: Leverage Pydantic's validation for reliable data handling
- 🚨 **Error Handling**: Comprehensive error types for different failure
  scenarios

## Installation

```bash
# Basic installation
pip install pydapter

# With database support
pip install "pydapter[postgres,mongo,neo4j,qdrant]"

# With pandas support
pip install "pydapter[pandas]"
```

## Quick Start

### Basic Adapter Usage

```python
from pydantic import BaseModel
from typing import List
from pydapter.adapters.json_ import JsonAdapter

# Define a Pydantic model
class User(BaseModel):
    id: int
    name: str
    email: str
    active: bool = True
    tags: List[str] = []

# Create a user
user = User(id=1, name="Alice", email="alice@example.com", tags=["admin"])

# Convert to JSON
json_data = JsonAdapter.to_obj(user)
print(json_data)

# Convert back to model
loaded_user = JsonAdapter.from_obj(User, json_data)
print(loaded_user)
```

### Using the Adaptable Mixin

```python
from pydantic import BaseModel
from pydapter.core import Adaptable
from pydapter.adapters.json_ import JsonAdapter
from pydapter.adapters.csv_ import CsvAdapter

# Define a model with the Adaptable mixin
class Product(BaseModel, Adaptable):
    id: int
    name: str
    price: float
    in_stock: bool = True

# Register adapters
Product.register_adapter(JsonAdapter)
Product.register_adapter(CsvAdapter)

# Create a product
product = Product(id=101, name="Laptop", price=999.99)

# Convert to different formats using the mixin methods
json_data = product.adapt_to(obj_key="json")
csv_data = product.adapt_to(obj_key="csv")

# Convert back to models
product_from_json = Product.adapt_from(json_data, obj_key="json")
```

## Available Adapters

Pydapter includes adapters for various data formats and storage systems:

### File Format Adapters

- `JsonAdapter`: JSON files and strings
- `CsvAdapter`: CSV files and strings
- `TomlAdapter`: TOML files and strings

### Data Analysis Adapters

- `DataFrameAdapter`: pandas DataFrame
- `SeriesAdapter`: pandas Series
- `ExcelAdapter`: Excel files (requires pandas and openpyxl/xlsxwriter)

### Database Adapters

- `PostgresAdapter` / `AsyncPostgresAdapter`: PostgreSQL
- `MongoAdapter` / `AsyncMongoAdapter`: MongoDB
- `Neo4jAdapter`: Neo4j graph database
- `QdrantAdapter` / `AsyncQdrantAdapter`: Qdrant vector database
- `SQLAdapter` / `AsyncSQLAdapter`: Generic SQL (SQLAlchemy)

## Detailed Examples

### Working with PostgreSQL

```python
from pydantic import BaseModel
from typing import Optional
from pydapter.extras.postgres_ import PostgresAdapter

class User(BaseModel):
    id: Optional[int] = None
    name: str
    email: str

# Read from database
users = PostgresAdapter.from_obj(
    User,
    {
        "engine_url": "postgresql+psycopg://user:pass@localhost/dbname",
        "table": "users",
        "selectors": {"active": True}
    },
    many=True
)

# Store in database
user = User(name="Alice", email="alice@example.com")
PostgresAdapter.to_obj(
    user,
    engine_url="postgresql+psycopg://user:pass@localhost/dbname",
    table="users"
)
```

### Working with MongoDB

```python
from pydantic import BaseModel
from typing import List
from pydapter.extras.mongo_ import MongoAdapter

class Product(BaseModel):
    id: str
    name: str
    price: float
    categories: List[str] = []

# Query from MongoDB
products = MongoAdapter.from_obj(
    Product,
    {
        "url": "mongodb://localhost:27017",
        "db": "shop",
        "collection": "products",
        "filter": {"price": {"$lt": 100}}
    },
    many=True
)

# Store in MongoDB
product = Product(id="prod1", name="Headphones", price=49.99, categories=["audio", "accessories"])
MongoAdapter.to_obj(
    product,
    url="mongodb://localhost:27017",
    db="shop",
    collection="products"
)
```

### Vector Search with Qdrant

```python
from pydantic import BaseModel
from typing import List
from sentence_transformers import SentenceTransformer
from pydapter.extras.qdrant_ import QdrantAdapter

# Load a model to generate embeddings
model = SentenceTransformer('all-MiniLM-L6-v2')

class Document(BaseModel):
    id: str
    title: str
    content: str
    embedding: List[float] = []

    def generate_embedding(self):
        self.embedding = model.encode(self.content).tolist()
        return self

# Create and store a document
doc = Document(
    id="doc1",
    title="Vector Databases",
    content="Vector databases store high-dimensional vectors for similarity search."
).generate_embedding()

QdrantAdapter.to_obj(
    doc,
    collection="documents",
    url="http://localhost:6333"
)

# Search for similar documents
query_vector = model.encode("How do vector databases work?").tolist()
results = QdrantAdapter.from_obj(
    Document,
    {
        "collection": "documents",
        "query_vector": query_vector,
        "top_k": 5,
        "url": "http://localhost:6333"
    },
    many=True
)
```

### Graph Database with Neo4j

```python
from pydantic import BaseModel
from typing import List
from pydapter.extras.neo4j_ import Neo4jAdapter

class Person(BaseModel):
    id: str
    name: str
    age: int

# Store a person in Neo4j
person = Person(id="p1", name="Alice", age=30)
Neo4jAdapter.to_obj(
    person,
    url="bolt://localhost:7687",
    auth=("neo4j", "password"),
    label="Person",
    merge_on="id"
)

# Find people by property
people = Neo4jAdapter.from_obj(
    Person,
    {
        "url": "bolt://localhost:7687",
        "auth": ("neo4j", "password"),
        "label": "Person",
        "where": "n.age > 25"
    },
    many=True
)
```

## Asynchronous Adapters

Many adapters have asynchronous counterparts:

```python
import asyncio
from pydantic import BaseModel
from pydapter.async_core import AsyncAdaptable
from pydapter.extras.async_postgres_ import AsyncPostgresAdapter

class User(BaseModel, AsyncAdaptable):
    id: int
    name: str
    email: str

# Register the async adapter
User.register_async_adapter(AsyncPostgresAdapter)

async def main():
    # Query from database asynchronously
    users = await User.adapt_from_async(
        {
            "engine_url": "postgresql+asyncpg://user:pass@localhost/dbname",
            "table": "users"
        },
        obj_key="async_pg",
        many=True
    )

    # Create a user
    user = User(id=42, name="Bob", email="bob@example.com")

    # Store in database asynchronously
    result = await user.adapt_to_async(
        obj_key="async_pg",
        engine_url="postgresql+asyncpg://user:pass@localhost/dbname",
        table="users"
    )

# Run the async function
asyncio.run(main())
```

## Error Handling

Pydapter provides a rich set of exceptions for detailed error handling:

```python
from pydapter.exceptions import (
    AdapterError, ValidationError, ParseError,
    ConnectionError, QueryError, ResourceError
)
from pydapter.adapters.json_ import JsonAdapter

try:
    # Try to parse invalid JSON
    JsonAdapter.from_obj(User, "{ invalid json }")
except ParseError as e:
    print(f"JSON parsing error: {e}")
except ValidationError as e:
    print(f"Validation error: {e}")
    if hasattr(e, 'errors') and callable(e.errors):
        for error in e.errors():
            print(f"  - {error['loc']}: {error['msg']}")
```

## Extension

Creating your own adapter is straightforward:

```python
from typing import TypeVar
from pydantic import BaseModel
from pydapter.core import Adapter

T = TypeVar("T", bound=BaseModel)

class MyCustomAdapter(Adapter[T]):
    obj_key = "my_format"

    @classmethod
    def from_obj(cls, subj_cls: type[T], obj: Any, /, *, many=False, **kw):
        # Convert from your format to Pydantic models
        ...

    @classmethod
    def to_obj(cls, subj: T | List[T], /, *, many=False, **kw):
        # Convert from Pydantic models to your format
        ...
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for
details.

## Acknowledgements

- [Pydantic](https://docs.pydantic.dev/) - The data validation library that
  makes this possible
- All the amazing database and format libraries this project integrates with

---

Built with ❤️ by the pydapter team
