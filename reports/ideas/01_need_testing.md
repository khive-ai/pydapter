Below is a **single, self-contained master plan** that the whole dev team
(including the new _khive_ agents) can follow from zero-to-shipping without
splitting it into separate issues. Copy this into a single GitHub Issue titled
**“🌐 Pydapter + khive bootstrap & test-automation roadmap”** and let the bots
(or people) run.

---

# 🌐 Pydapter + khive Bootstrap & Test-Automation Roadmap

> **Goal:** integrate the khive multi-agent roles, land a complete adapter-test
> harness (sync + async), containerised back-ends, performance benchmarks, and a
> full CI matrix - in **one coordinated push**.

---

## 0 — Repository seeds

| File / Dir                 | Purpose                                                                                                                                                                                                                   |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `.github/khive_modes.json` | Paste the full role-definition JSON (above).                                                                                                                                                                              |
| `CONTRIBUTING.md`          | Add a new “Automated Roles” section pointing at that file and summarising how the `khive-orchestrator` opens tasks / PRs.                                                                                                 |
| `.coveragerc`              | Exclude `tests/*` and the _generated_ khive JSON from coverage.                                                                                                                                                           |
| `pyproject.toml` updates   | - add `all` extra that aggregates every optional dep <br> - under `[project.optional-dependencies]` list: `pandas`, `excel`, `sql`, `postgres`, `motor`, `asyncpg`, `qdrant`, `weaviate`, `neo4j`, `test` (pytest stack). |

---

## 1 — Test harness (sync + async)

### 1.1 pytest baseline

- `pytest.ini` or `[tool.pytest.ini_options]` in `pyproject.toml`

  ```ini
  addopts = -ra --cov=pydapter --cov-report=term-missing
  testpaths = tests
  ```
- `tests/conftest.py`

  ```python
  import pytest, uuid, tempfile
  from pydapter import Adaptable
  from pydapter.adapters import JsonAdapter, CsvAdapter, TomlAdapter

  class _ModelFactory:
      def __call__(self, **kw):
          from pydantic import BaseModel
          class M(Adaptable, BaseModel):
              id: int
              name: str
              value: float
          M.register_adapter(JsonAdapter)
          M.register_adapter(CsvAdapter)
          M.register_adapter(TomlAdapter)
          return M(**kw)
  @pytest.fixture
  def sample(_ModelFactory):         # pylint: disable=invalid-name
      return _ModelFactory(id=1, name="foo", value=42.5)
  ```

### 1.2 session-scoped container fixtures

_Install_ `testcontainers[postgres,qdrant]`.

```python
@pytest.fixture(scope="session")
def pg_url():
    from testcontainers.postgres import PostgresContainer
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg.get_connection_url()    # postgresql://user:pass@host:port/db
@pytest.fixture(scope="session")
def qdrant_url():
    from testcontainers.qdrant import QdrantContainer
    with QdrantContainer("qdrant/qdrant:v1.8.1") as qc:
        yield f"http://{qc.get_container_host_ip()}:{qc.get_exposed_port(6333)}"
```

---

## 2 — Core round-trip tests (parametrised)

```python
import pytest, json, toml, csv, io
from pydapter.adapters import JsonAdapter, CsvAdapter, TomlAdapter

@pytest.mark.parametrize("adapter_key", ["json", "toml", "csv"])
def test_text_roundtrip(sample, adapter_key):
    dumped   = sample.adapt_to(obj_key=adapter_key)
    restored = sample.__class__.adapt_from(dumped, obj_key=adapter_key)
    assert restored == sample
```

---

## 3 — Async adapters

### 3.1 Register adapters on-the-fly

```python
import pytest, asyncio, pytest_asyncio
from pydapter.extras.async_postgres_ import AsyncPostgresAdapter
from pydapter.extras.async_mongo_    import AsyncMongoAdapter
from pydapter.extras.async_qdrant_   import AsyncQdrantAdapter

ASYNC_KEYS = {
    "async_pg":  AsyncPostgresAdapter,
    "async_mongo": AsyncMongoAdapter,
    "async_qdrant": AsyncQdrantAdapter,
}

@pytest.mark.asyncio
@pytest.mark.parametrize("adapter_key", list(ASYNC_KEYS))
async def test_async_roundtrip(sample, adapter_key, pg_url, qdrant_url):
    adapter_cls = ASYNC_KEYS[adapter_key]
    sample.__class__.register_async_adapter(adapter_cls)
    kwargs_out = dict()
    if adapter_key == "async_pg":
        kwargs_out = {"dsn": pg_url, "table": "trades"}
    elif adapter_key == "async_qdrant":
        kwargs_out = {"collection": "test", "url": qdrant_url}

    await sample.adapt_to_async(obj_key=adapter_key, **kwargs_out)

    kwargs_in = kwargs_out.copy()
    if adapter_key == "async_pg":
        kwargs_in = {"dsn": pg_url, "table": "trades",
                     "selectors": {"id": sample.id}}
    elif adapter_key == "async_qdrant":
        kwargs_in = {"collection": "test",
                     "query_vector": sample.embedding, "url": qdrant_url,
                     "top_k": 1}

    fetched = await sample.__class__.adapt_from_async(kwargs_in,
                                                     obj_key=adapter_key,
                                                     many=False)
    assert fetched == sample
```

---

## 4 — Performance bench (pytest-benchmark)

`tests/test_bench_json.py`

```python
def test_json_perf(benchmark, sample):
    benchmark(JsonAdapter.to_obj, sample)
```

Add `--benchmark-skip` to CI run if on slow runner.

---

## 5 — CI matrix

`.github/workflows/ci.yml`

```yaml
name: ci
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      docker: {image: docker:dind, options: --privileged}
    strategy:
      matrix:
        py: ["3.9", "3.10", "3.11", "3.12"]
        extras: ["minimal", "all"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: ${{ matrix.py }}}
      - run: pip install uv
      - run: >
          uv pip install -e ".[$([[ ${{ matrix.extras }} == all ]] && echo all || echo test)]"
      - run: pytest -q
```

---

## 6 — Coverage & Codecov

- Add Codecov token secret.
- After tests: `pytest --cov=pydapter --cov-report=xml`.
- Upload via `codecov/codecov-action@v3`.

---

## 7 — Docs & badges

- README: add CI badge, coverage badge, quick-start snippet.
- DOCUMENTER role will generate API docs once CI is green.

---

## 8 — Rollout order for the bots

1. **khive-implementer** commits sections _0-2_ in a single PR.
2. **khive-quality-reviewer** reviews; on ✅ CI merges.
3. **implementer** adds _3_ (async) and _4_ (bench).
4. **quality-reviewer** approves, **orchestrator** merges.
5. **implementer** lands CI workflow (_5_) and Codecov config (_6_).
6. **documenter** updates README (_7_).
7. Done - master branch now has agents, tests, coverage, CI matrix.

---

### Definition-of-Done for the entire plan

- `.github/khive_modes.json` present and valid.
- `pip install -e .[all,test] && pytest -q` passes locally.
- GitHub Actions matrix green on PR.
- Coverage ≥ 90 % (core + adapters).
- README shows passing badge and coverage badge.

Once this single issue is created, the khive bots can autonomously open the PRs
in the order above. Human maintainers only need to merge once reviews are green.

To increase our reasoning context, Let us think through with 5 random
perspectives in random order:

[^System] The pydapter project requires a comprehensive testing strategy. The
feedback provides insights into effective testing approaches including
parameterization, containerization, and CI setup. A well-designed test suite
should verify both sync and async adapter functionality.

[^Breakdown] We need to create a phased implementation plan that builds the
infrastructure incrementally: test harness first, then container fixtures,
parameterized tests for standard adapters, async adapter tests, and finally CI
integration.

[^Critical] The feedback emphasizes several critical improvements to the initial
proposal: using testcontainers instead of environment checks, pytest-benchmark
for performance testing, and pytest.importorskip for optional dependencies.

[^Stakeholder] From a maintainer's perspective, we need balanced coverage with
execution speed, an issue/PR sequence that provides incremental value, and a
testing approach that scales as new adapters are added.

## [^Risk] External system dependencies and async code paths present the highest testing risks. Our strategy must prioritize containerization for deterministic results and proper async fixtures for reliable testing.

Based on the excellent feedback received, I'll outline a comprehensive
implementation plan for testing the pydapter package. This plan will guide our
development team in setting up a robust testing infrastructure.

# pydapter Testing Implementation Plan

## Overview

We'll implement a comprehensive test suite for pydapter with the following key
characteristics:

1. **Pytest-based infrastructure** with coverage reporting and parameterized
   tests
2. **Containerized dependencies** using testcontainers-python for reliable,
   deterministic testing
3. **Balanced coverage** across sync/async adapters (excluding Weaviate and
   Neo4j)
4. **Performance benchmarking** using pytest-benchmark
5. **CI integration** with GitHub Actions matrix testing

## Implementation Phases

### Phase 1: Bootstrap Test Infrastructure

**Goal:** Establish the base testing framework and configuration.

**Implementation:**

1. Set up `tests/` directory structure:
   ```
   tests/
   ├── conftest.py            # Shared fixtures and configuration
   ├── schemas.py             # Test model definitions
   ├── test_core.py           # Core protocol tests
   ```

2. Configure pytest in `pyproject.toml`:
   ```toml
   [tool.pytest.ini_options]
   minversion = "7.0"
   addopts = "-ra --cov=pydapter --cov-report=term-missing"
   testpaths = ["tests"]
   markers = [
       "adapter: mark tests that focus on specific adapters",
       "sync: synchronous adapter tests",
       "async: asynchronous adapter tests",
   ]
   ```

3. Create `requirements-test.txt` with test dependencies:
   ```
   pytest>=7.0.0
   pytest-cov>=4.1.0
   pytest-asyncio>=0.21.0
   pytest-benchmark>=4.0.0
   testcontainers-python>=3.7.0
   ```

4. Add an `all` extra in `pyproject.toml` or `setup.py` that includes all
   optional dependencies:
   ```python
   extras_require={
       "test": ["pytest>=7.0.0", "pytest-cov", "pytest-asyncio", "pytest-benchmark", "testcontainers-python"],
       "pandas": ["pandas>=1.3.0"],
       "sql": ["sqlalchemy>=2.0.0"],
       "postgres": ["asyncpg>=0.27.0", "psycopg>=3.1.8"],
       "mongo": ["pymongo>=4.3.0"],
       "asyncmongo": ["motor>=3.1.0"],
       "vector": ["qdrant-client>=1.1.0"],
       "excel": ["openpyxl>=3.0.10", "xlsxwriter>=3.0.3"],
       "all": ["pandas>=1.3.0", "sqlalchemy>=2.0.0", "asyncpg>=0.27.0", "psycopg>=3.1.8",
               "pymongo>=4.3.0", "motor>=3.1.0", "qdrant-client>=1.1.0",
               "openpyxl>=3.0.10", "xlsxwriter>=3.0.3"],
   }
   ```

### Phase 2: Container Fixtures and Test Data

**Goal:** Create reusable test fixtures for database dependencies and sample
data.

**Implementation:**

1. Implement session-scoped container fixtures in `conftest.py`:

```python
import pytest
import pytest_asyncio
from testcontainers.postgres import PostgresContainer
from testcontainers.core.container import DockerContainer

@pytest.fixture(scope="session")
def pg_url():
    """Session-scoped PostgreSQL container with pgvector extension."""
    with PostgresContainer("postgres:16-alpine") as container:
        # Initialize with pgvector extension if needed
        yield container.get_connection_url()

@pytest.fixture(scope="session")
def qdrant_url():
    """Session-scoped Qdrant vector database container."""
    with DockerContainer("qdrant/qdrant:v1.8.1") \
            .with_exposed_ports(6333, 6334) as container:
        api_port = container.get_exposed_port(6333)
        yield f"http://{container.get_container_host_ip()}:{api_port}"

@pytest_asyncio.fixture(scope="session")
async def mongo_url():
    """Session-scoped MongoDB container."""
    from testcontainers.mongodb import MongoDbContainer
    with MongoDbContainer() as mongo:
        yield mongo.get_connection_url()
```

2. Create sample data fixtures in `conftest.py`:

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# Define test models in schemas.py
class TestItem(BaseModel):
    """Simple test model for adapter testing."""
    id: int
    name: str
    value: float
    tags: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None

@pytest.fixture
def sample_item():
    """Sample test item for single-object tests."""
    from tests.schemas import TestItem
    return TestItem(
        id=1,
        name="test item",
        value=42.5,
        tags=["test", "example"],
        created_at=datetime(2025, 1, 1)
    )

@pytest.fixture
def sample_items():
    """Sample collection of items for many-object tests."""
    from tests.schemas import TestItem
    return [
        TestItem(id=i, name=f"item-{i}", value=i * 1.5, tags=["test"])
        for i in range(1, 6)
    ]
```

### Phase 3: Core Protocol Tests

**Goal:** Test the core adapter protocols and registry mechanisms.

**Implementation:**

1. Create `test_core.py` for synchronous adapter protocol tests:

```python
import pytest
from pydantic import BaseModel
from typing import ClassVar

from pydapter.core import Adapter, AdapterRegistry, Adaptable

def test_adapter_registry():
    """Test AdapterRegistry registration and retrieval."""
    registry = AdapterRegistry()

    # Mock adapter class
    class MockAdapter:
        obj_key: ClassVar[str] = "mock"

    # Register adapter
    registry.register(MockAdapter)

    # Retrieve adapter
    adapter_cls = registry.get("mock")
    assert adapter_cls == MockAdapter

    # Test error on non-existent adapter
    with pytest.raises(KeyError):
        registry.get("nonexistent")

def test_adaptable_mixin():
    """Test the Adaptable mixin functionality."""
    # Create a test model with Adaptable
    class TestModel(BaseModel, Adaptable):
        name: str
        value: int

    # Create a mock adapter
    class MockAdapter:
        obj_key = "mock"

        @classmethod
        def from_obj(cls, subj_cls, obj, /, *, many=False, **kw):
            return subj_cls(name="from_mock", value=100)

        @classmethod
        def to_obj(cls, subj, /, *, many=False, **kw):
            return "mock_output"

    # Register adapter with the model class
    TestModel.register_adapter(MockAdapter)

    # Test adapt_from
    obj = TestModel.adapt_from("anything", obj_key="mock")
    assert obj.name == "from_mock"
    assert obj.value == 100

    # Test adapt_to
    obj = TestModel(name="test", value=42)
    result = obj.adapt_to(obj_key="mock")
    assert result == "mock_output"
```

2. Create `test_async_core.py` for asynchronous adapter tests:

```python
import pytest
import pytest_asyncio
from pydantic import BaseModel

from pydapter.async_core import AsyncAdapter, AsyncAdapterRegistry, AsyncAdaptable

# Skip tests if pytest-asyncio is not available
pytest.importorskip("pytest_asyncio")

@pytest.mark.asyncio
async def test_async_adapter_registry():
    """Test AsyncAdapterRegistry registration and retrieval."""
    registry = AsyncAdapterRegistry()

    # Mock async adapter
    class MockAsyncAdapter:
        obj_key = "mock_async"

        @classmethod
        async def from_obj(cls, subj_cls, obj, /, *, many=False, **kw):
            pass

        @classmethod
        async def to_obj(cls, subj, /, *, many=False, **kw):
            pass

    # Register adapter
    registry.register(MockAsyncAdapter)

    # Retrieve adapter
    adapter_cls = registry.get("mock_async")
    assert adapter_cls == MockAsyncAdapter

    # Test error on non-existent adapter
    with pytest.raises(KeyError):
        registry.get("nonexistent")

@pytest.mark.asyncio
async def test_async_adaptable_mixin():
    """Test the AsyncAdaptable mixin functionality."""
    # Create a test model with AsyncAdaptable
    class TestModel(BaseModel, AsyncAdaptable):
        name: str
        value: int

    # Create a mock async adapter
    class MockAsyncAdapter:
        obj_key = "mock_async"

        @classmethod
        async def from_obj(cls, subj_cls, obj, /, *, many=False, **kw):
            return subj_cls(name="from_async", value=200)

        @classmethod
        async def to_obj(cls, subj, /, *, many=False, **kw):
            return "async_mock_output"

    # Register adapter with the model class
    TestModel.register_async_adapter(MockAsyncAdapter)

    # Test adapt_from_async
    obj = await TestModel.adapt_from_async("anything", obj_key="mock_async")
    assert obj.name == "from_async"
    assert obj.value == 200

    # Test adapt_to_async
    obj = TestModel(name="test", value=42)
    result = await obj.adapt_to_async(obj_key="mock_async")
    assert result == "async_mock_output"
```

### Phase 4: Parameterized Adapter Tests

**Goal:** Implement parameterized tests for standard adapters (JSON, CSV, TOML).

**Implementation:**

1. Create `test_standard_adapters.py` with parameterized tests:

```python
import pytest
from tempfile import NamedTemporaryFile
import json
import csv
import io
import os

from pydapter.adapters import JsonAdapter, CsvAdapter, TomlAdapter
from tests.schemas import TestItem

@pytest.mark.parametrize("adapter_key,adapter_cls", [
    ("json", JsonAdapter),
    ("csv", CsvAdapter),
    ("toml", TomlAdapter),
])
def test_standard_adapter_roundtrip(sample_item, adapter_key, adapter_cls):
    """Test roundtrip serialization/deserialization for standard adapters."""
    # Register the adapter with the model class
    TestItem.register_adapter(adapter_cls)

    # Convert to serialized form
    serialized = sample_item.adapt_to(obj_key=adapter_key)

    # Convert back to model instance
    restored = TestItem.adapt_from(serialized, obj_key=adapter_key)

    # Verify properties preserved
    assert restored.id == sample_item.id
    assert restored.name == sample_item.name
    assert restored.value == sample_item.value
    assert restored.tags == sample_item.tags
    # Datetime comparison may need special handling depending on serialization

@pytest.mark.parametrize("adapter_key,adapter_cls", [
    ("json", JsonAdapter),
    ("csv", CsvAdapter),
    ("toml", TomlAdapter),
])
def test_standard_adapter_collection(sample_items, adapter_key, adapter_cls):
    """Test roundtrip for collections with standard adapters."""
    # Register the adapter with the model class
    TestItem.register_adapter(adapter_cls)

    # Convert to serialized form
    serialized = adapter_cls.to_obj(sample_items, many=True)

    # Convert back to model instances
    restored = adapter_cls.from_obj(TestItem, serialized, many=True)

    # Verify collection size preserved
    assert len(restored) == len(sample_items)

    # Verify each item's properties
    for orig, rest in zip(sample_items, restored):
        assert rest.id == orig.id
        assert rest.name == orig.name
        assert rest.value == orig.value
```

2. Create `test_pandas_adapters.py` for pandas-related adapters:

```python
import pytest
import os

# Skip tests if pandas is not available
pd = pytest.importorskip("pandas")

from pydapter.extras.pandas_ import DataFrameAdapter, SeriesAdapter
from pydapter.extras.excel_ import ExcelAdapter
from tests.schemas import TestItem

@pytest.mark.parametrize("adapter_key,adapter_cls", [
    ("pd.DataFrame", DataFrameAdapter),
    ("pd.Series", SeriesAdapter),
])
def test_pandas_adapter_roundtrip(sample_item, adapter_key, adapter_cls):
    """Test roundtrip for pandas adapters."""
    # Skip Series tests for collections
    if adapter_key == "pd.Series" and isinstance(sample_item, list):
        pytest.skip("SeriesAdapter doesn't support collections")

    # Register the adapter with the model class
    TestItem.register_adapter(adapter_cls)

    # Convert to pandas object
    pd_obj = sample_item.adapt_to(obj_key=adapter_key)

    # Verify type
    if adapter_key == "pd.DataFrame":
        assert isinstance(pd_obj, pd.DataFrame)
    else:
        assert isinstance(pd_obj, pd.Series)

    # Convert back to model instance
    restored = TestItem.adapt_from(pd_obj, obj_key=adapter_key)

    # Verify properties preserved
    assert restored.id == sample_item.id
    assert restored.name == sample_item.name
    assert restored.value == sample_item.value

def test_excel_adapter(sample_items, tmp_path):
    """Test Excel adapter roundtrip using temporary files."""
    # Skip if openpyxl/xlsxwriter not available
    pytest.importorskip("openpyxl")
    pytest.importorskip("xlsxwriter")

    from pydapter.extras.excel_ import ExcelAdapter

    # Register adapter
    TestItem.register_adapter(ExcelAdapter)

    # Create a temporary path for the Excel file
    excel_path = os.path.join(tmp_path, "test.xlsx")

    # Convert to Excel bytes
    excel_bytes = ExcelAdapter.to_obj(sample_items, many=True)

    # Write to file
    with open(excel_path, "wb") as f:
        f.write(excel_bytes)

    # Read back from file
    restored = ExcelAdapter.from_obj(TestItem, excel_path, many=True)

    # Verify data
    assert len(restored) == len(sample_items)
    for orig, rest in zip(sample_items, restored):
        assert rest.id == orig.id
        assert rest.name == orig.name
        assert rest.value == orig.value
```

### Phase 5: Database Adapter Tests

**Goal:** Implement tests for SQL, MongoDB, and Qdrant adapters.

**Implementation:**

1. Create `test_sql_adapters.py` for SQL-related adapters:

```python
import pytest
import os
import sqlalchemy as sa

# Skip tests if SQLAlchemy is not available
pytest.importorskip("sqlalchemy")

from pydapter.extras.sql_ import SQLAdapter
from pydapter.extras.postgres_ import PostgresAdapter
from tests.schemas import TestItem

def setup_test_table(engine, table_name="test_items"):
    """Set up a test table for SQL adapter tests."""
    metadata = sa.MetaData()
    table = sa.Table(
        table_name,
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(50)),
        sa.Column("value", sa.Float),
        sa.Column("tags", sa.JSON),
        sa.Column("created_at", sa.DateTime),
    )
    metadata.create_all(engine)
    return table

def test_sql_adapter_sqlite(sample_item, tmp_path):
    """Test SQLAdapter with SQLite."""
    # Create a SQLite engine with a temporary database
    db_path = os.path.join(tmp_path, "test.db")
    engine_url = f"sqlite:///{db_path}"
    engine = sa.create_engine(engine_url)

    # Set up test table
    setup_test_table(engine)

    # Register adapter
    TestItem.register_adapter(SQLAdapter)

    # Write to database
    sample_item.adapt_to(
        obj_key="sql",
        engine_url=engine_url,
        table="test_items"
    )

    # Read from database
    restored = TestItem.adapt_from(
        {
            "engine_url": engine_url,
            "table": "test_items",
            "selectors": {"id": sample_item.id}
        },
        obj_key="sql",
        many=False
    )

    # Verify data
    assert restored.id == sample_item.id
    assert restored.name == sample_item.name
    assert restored.value == sample_item.value

@pytest.mark.parametrize("adapter_key", ["postgres"])
def test_postgres_adapter(sample_items, pg_url, adapter_key):
    """Test PostgresAdapter with real Postgres container."""
    # Skip if psycopg is not available
    pytest.importorskip("psycopg")

    from pydapter.extras.postgres_ import PostgresAdapter

    # Create engine and table
    engine = sa.create_engine(pg_url)
    setup_test_table(engine)

    # Register adapter
    TestItem.register_adapter(PostgresAdapter)

    # Write to database
    PostgresAdapter.to_obj(
        sample_items,
        engine_url=pg_url,
        table="test_items",
        many=True
    )

    # Read from database
    restored = PostgresAdapter.from_obj(
        TestItem,
        {
            "engine_url": pg_url,
            "table": "test_items",
        },
        many=True
    )

    # Verify count
    assert len(restored) == len(sample_items)

    # Verify each item
    for orig in sample_items:
        found = next((r for r in restored if r.id == orig.id), None)
        assert found is not None
        assert found.name == orig.name
        assert found.value == orig.value
```

2. Create `test_mongo_adapter.py` for MongoDB adapter:

```python
import pytest

# Skip tests if pymongo is not available
pytest.importorskip("pymongo")

from pydapter.extras.mongo_ import MongoAdapter
from tests.schemas import TestItem

def test_mongo_adapter(sample_items, mongo_url):
    """Test MongoAdapter with MongoDB container."""
    # Register adapter
    TestItem.register_adapter(MongoAdapter)

    # Write to database
    MongoAdapter.to_obj(
        sample_items,
        url=mongo_url,
        db="test",
        collection="items",
        many=True
    )

    # Read from database
    restored = MongoAdapter.from_obj(
        TestItem,
        {
            "url": mongo_url,
            "db": "test",
            "collection": "items",
        },
        many=True
    )

    # Verify count
    assert len(restored) == len(sample_items)

    # Verify each item
    for orig in sample_items:
        found = next((r for r in restored if r.id == orig.id), None)
        assert found is not None
        assert found.name == orig.name
        assert found.value == orig.value
```

3. Create `test_qdrant_adapter.py` for vector database adapter:

```python
import pytest
import numpy as np

# Skip tests if qdrant-client is not available
pytest.importorskip("qdrant_client")

from pydapter.extras.qdrant_ import QdrantAdapter
from tests.schemas import TestItem
from pydantic import BaseModel, Field

# Extend TestItem with vector field for Qdrant
class VectorItem(TestItem):
    embedding: list[float] = Field(default_factory=lambda: list(np.random.random(384)))

@pytest.fixture
def vector_items():
    """Sample collection of items with vectors."""
    return [
        VectorItem(
            id=i,
            name=f"vector-{i}",
            value=i * 1.5,
            tags=["test"],
            embedding=list(np.random.random(384))
        )
        for i in range(1, 6)
    ]

def test_qdrant_adapter(vector_items, qdrant_url):
    """Test QdrantAdapter with Qdrant container."""
    # Register adapter
    VectorItem.register_adapter(QdrantAdapter)

    # Write to Qdrant
    QdrantAdapter.to_obj(
        vector_items,
        url=qdrant_url,
        collection="test_items",
        vector_field="embedding",
        id_field="id"
    )

    # Read from Qdrant using the first item's vector as query
    query_vector = vector_items[0].embedding
    restored = QdrantAdapter.from_obj(
        VectorItem,
        {
            "url": qdrant_url,
            "collection": "test_items",
            "query_vector": query_vector,
            "top_k": 5
        },
        many=True
    )

    # Verify results were returned
    assert len(restored) > 0

    # Check that at least the query item was found
    found = any(r.id == vector_items[0].id for r in restored)
    assert found
```

### Phase 6: Async Adapter Tests

**Goal:** Test async adapters (AsyncSQL, AsyncMongo, AsyncQdrant).

**Implementation:**

1. Create `test_async_adapters.py` for async adapter tests:

```python
import pytest
import pytest_asyncio
import sqlalchemy as sa
import os

# Skip tests if dependencies not available
pytest.importorskip("pytest_asyncio")
pytest.importorskip("sqlalchemy")

from tests.schemas import TestItem

@pytest.mark.asyncio
async def test_async_postgres_adapter(sample_items, pg_url):
    """Test AsyncPostgresAdapter with Postgres container."""
    # Skip if asyncpg not available
    pytest.importorskip("asyncpg")

    from pydapter.extras.async_postgres_ import AsyncPostgresAdapter

    # Set up table (using sync SQLAlchemy for simplicity)
    engine = sa.create_engine(pg_url)
    metadata = sa.MetaData()
    table = sa.Table(
        "async_test_items",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(50)),
        sa.Column("value", sa.Float),
        sa.Column("tags", sa.JSON),
        sa.Column("created_at", sa.DateTime),
    )
    metadata.create_all(engine)

    # Register adapter
    TestItem.register_async_adapter(AsyncPostgresAdapter)

    # Write to database
    await AsyncPostgresAdapter.to_obj(
        sample_items,
        engine_url=pg_url,
        table="async_test_items",
        many=True
    )

    # Read from database
    restored = await AsyncPostgresAdapter.from_obj(
        TestItem,
        {
            "engine_url": pg_url,
            "table": "async_test_items",
        },
        many=True
    )

    # Verify count
    assert len(restored) == len(sample_items)

    # Verify each item
    for orig in sample_items:
        found = next((r for r in restored if r.id == orig.id), None)
        assert found is not None
        assert found.name == orig.name
        assert found.value == orig.value

@pytest.mark.asyncio
async def test_async_mongo_adapter(sample_items, mongo_url):
    """Test AsyncMongoAdapter with MongoDB container."""
    # Skip if motor not available
    pytest.importorskip("motor")

    from pydapter.extras.async_mongo_ import AsyncMongoAdapter

    # Register adapter
    TestItem.register_async_adapter(AsyncMongoAdapter)

    # Write to database
    await AsyncMongoAdapter.to_obj(
        sample_items,
        url=mongo_url,
        db="test",
        collection="async_items",
        many=True
    )

    # Read from database
    restored = await AsyncMongoAdapter.from_obj(
        TestItem,
        {
            "url": mongo_url,
            "db": "test",
            "collection": "async_items",
        },
        many=True
    )

    # Verify count
    assert len(restored) == len(sample_items)

    # Verify each item
    for orig in sample_items:
        found = next((r for r in restored if r.id == orig.id), None)
        assert found is not None
        assert found.name == orig.name
        assert found.value == orig.value
```

### Phase 7: Performance Benchmarks

**Goal:** Implement performance benchmarking for key adapter operations.

**Implementation:**

1. Create `test_benchmarks.py` for performance tests:

```python
import pytest
import json
import io
import csv

from pydapter.adapters import JsonAdapter, CsvAdapter, TomlAdapter
from tests.schemas import TestItem

@pytest.fixture
def large_dataset():
    """Generate a large dataset for benchmarking."""
    return [
        TestItem(id=i, name=f"item-{i}", value=i * 0.5, tags=["benchmark"])
        for i in range(1000)
    ]

def test_json_adapter_to_obj_benchmark(large_dataset, benchmark):
    """Benchmark JsonAdapter.to_obj performance."""
    result = benchmark(JsonAdapter.to_obj, large_dataset, many=True)
    # Verify result is valid JSON
    assert json.loads(result)
    assert len(json.loads(result)) == len(large_dataset)

def test_json_adapter_from_obj_benchmark(large_dataset, benchmark):
    """Benchmark JsonAdapter.from_obj performance."""
    # First convert to JSON
    json_data = JsonAdapter.to_obj(large_dataset, many=True)

    # Benchmark deserialization
    result = benchmark(JsonAdapter.from_obj, TestItem, json_data, many=True)

    # Verify result
    assert len(result) == len(large_dataset)
    assert all(isinstance(item, TestItem) for item in result)

def test_csv_adapter_to_obj_benchmark(large_dataset, benchmark):
    """Benchmark CsvAdapter.to_obj performance."""
    result = benchmark(CsvAdapter.to_obj, large_dataset, many=True)
    # Verify result is valid CSV
    reader = csv.DictReader(io.StringIO(result))
    rows = list(reader)
    assert len(rows) == len(large_dataset)

def test_csv_adapter_from_obj_benchmark(large_dataset, benchmark):
    """Benchmark CsvAdapter.from_obj performance."""
    # First convert to CSV
    csv_data = CsvAdapter.to_obj(large_dataset, many=True)

    # Benchmark deserialization
    result = benchmark(CsvAdapter.from_obj, TestItem, csv_data, many=True)

    # Verify result
    assert len(result) == len(large_dataset)
    assert all(isinstance(item, TestItem) for item in result)
```

### Phase 8: CI Configuration

**Goal:** Set up GitHub Actions for matrix testing.

**Implementation:**

1. Create `.github/workflows/test.yml`:

```yaml
name: Test

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.9", "3.10", "3.11", "3.12"]
        extras: ["minimal", "all"]
        include:
          - extras: "minimal"
            install: ".[test]"
          - extras: "all"
            install: ".[all,test]"

    services:
      docker:
        image: docker:dind
        options: --privileged

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          python -m pip install -e "${{ matrix.install }}"

      - name: Run tests
        run: |
          pytest --cov=pydapter --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          file: ./coverage.xml
          fail_ci_if_error: false
```

2. Create a `.coveragerc` file:

```ini
[run]
source = pydapter
omit =
    */tests/*
    */site-packages/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise NotImplementedError
    if __name__ == .__main__.:
    pass
```

## Summary of Testing Strategy

This comprehensive testing plan:

1. **Uses parameterization** to test multiple adapters with the same core logic
2. **Leverages testcontainers** for reliable, deterministic testing
3. **Properly handles async tests** with pytest-asyncio
4. **Benchmarks critical operations** using pytest-benchmark
5. **Supports both minimal and full dependency configurations**
6. **Includes CI configuration** for matrix testing

The plan can be implemented incrementally, starting with the basic
infrastructure and adding more sophisticated tests in phases. Each phase builds
on the previous one, ensuring continuous progress and value.
