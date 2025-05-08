# pydapter 0.1.4 Tutorial

_Bridge Pydantic ⇆ SQLAlchemy (with optional pgvector)_

---

## 1 Installation

```bash
# core features
pip install pydapter>=0.1.4 sqlalchemy>=2.0 alembic

# add pgvector support and drivers
pip install pydapter[pgvector] psycopg[binary] pgvector
```

---

## 2 Quick-start (scalar models)

### 2.1 Define your validation model

```python
from pydantic import BaseModel

class UserSchema(BaseModel):
    id: int | None = None          # promoted to PK
    name: str
    email: str | None = None
    active: bool = True
```

### 2.2 Generate the ORM class

```python
from pydapter.model_adapters import SQLModelAdapter

UserSQL = SQLModelAdapter.pydantic_model_to_sql(UserSchema)
```

`UserSQL` is a fully-mapped SQLAlchemy declarative model—Alembic will pick it up
automatically.

### 2.3 Round-trip back to Pydantic (optional)

```python
RoundTrip = SQLModelAdapter.sql_model_to_pydantic(UserSQL)
user_json = RoundTrip.model_validate(UserSQL(name="Ann")).model_dump()
```

---

## 3 Embeddings with `pgvector`

### 3.1 Validation layer

```python
from pydantic import BaseModel, Field

class DocSchema(BaseModel):
    id: int | None = None
    text: str
    embedding: list[float] = Field(..., vector_dim=768)
```

### 3.2 Generate vector-aware model

```python
from pydapter.model_adapters import SQLVectorModelAdapter

DocSQL = SQLVectorModelAdapter.pydantic_model_to_sql(DocSchema)
```

Result:

```text
Column('embedding', Vector(768), nullable=False)
```

### 3.3 Reverse conversion

```python
DocSchemaRT = SQLVectorModelAdapter.sql_model_to_pydantic(DocSQL)
assert DocSchemaRT.model_fields["embedding"].json_schema_extra["vector_dim"] == 768
```

---

## 4 Alembic integration

1. **Add pgvector extension (first migration only)**

   ```python
   # env.py or an initial upgrade() block
   op.execute("CREATE EXTENSION IF NOT EXISTS pgvector")
   ```

2. **Autogenerate migrations**

   ```bash
   alembic revision --autogenerate -m "init tables"
   ```

All columns—including `Vector(dim)`—appear in the diff.

---

## 5 Advanced options

| Need                    | How                                                                           |
| ----------------------- | ----------------------------------------------------------------------------- |
| Custom table name       | `SQLModelAdapter.pydantic_model_to_sql(UserSchema, table_name="users")`       |
| Alternate PK field      | `…, pk_field="uuid"`                                                          |
| Cache generated classes | Wrap the call in your own memoization layer; generation runs once per import. |
| Unsupported types       | Extend `_PY_TO_SQL` / `_SQL_TO_PY` dictionaries or subclass the adapter.      |

---

## 6 Testing & CI

Unit tests rely only on SQLAlchemy inspection—no database spin-up.

```bash
pytest -q
```

To include vector tests:

```bash
pytest -q -m "not pgvector"          # skip
pytest -q                            # run all (pgvector installed)
```

---

## 7 Troubleshooting

| Symptom                         | Fix                                                                        |
| ------------------------------- | -------------------------------------------------------------------------- |
| `TypeError: Unsupported type …` | Add a mapping in the adapter or exclude the field.                         |
| Alembic shows no changes        | Ensure generated classes share `metadata` or are imported in `env.py`.     |
| Vector dim missing              | Provide `vector_dim` in `json_schema_extra`, or accept flexible dimension. |

---

## 8 Wrap-up

pydapter 0.1.4 lets you:

- Keep **one source of truth**—your Pydantic models.
- **Ship migrations** without hand-writing ORM classes.
- **Store embeddings** directly in Postgres with pgvector.

Update, generate, migrate—done. Happy coding! 🚀
