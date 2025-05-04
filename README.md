# pydapter

[![CI](https://github.com/ohdearquant/pydapter/actions/workflows/ci.yml/badge.svg)](https://github.com/ohdearquant/pydapter/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/ohdearquant/pydapter/branch/main/graph/badge.svg)](https://codecov.io/gh/ohdearquant/pydapter)

**pydapter** is a micro-library that lets any Pydantic model become _adaptable_
to / from arbitrary external representations (JSON, CSV, vector stores,
databases …).

```python
from pydapter import Adaptable
from pydapter.adapters import JsonAdapter
from pydantic import BaseModel

class User(Adaptable, BaseModel):
    name: str
    age: int

User.register_adapter(JsonAdapter)

u   = User(name="Alice", age=30)
raw = u.adapt_to(obj_key="json")
u2  = User.adapt_from(raw, obj_key="json")
assert u == u2
```

The library ships with a tiny core and optional extra adapters you can drop in
only when you need them.

## Features

- **Simple API**: Just mix in `Adaptable` and register adapters
- **Extensible**: Create your own adapters for any data source
- **Type-safe**: Leverages Pydantic's validation system
- **Async support**: Works with async data sources via `AsyncAdaptable`
- **Robust error handling**: Comprehensive exception hierarchy for clear error messages

## Error Handling

pydapter provides a robust error handling system with a comprehensive exception hierarchy:

```python
try:
    user = User.adapt_from(invalid_data, obj_key="json")
except pydapter.exceptions.ParseError as e:
    print(f"Failed to parse JSON: {e}")
except pydapter.exceptions.ValidationError as e:
    print(f"Validation failed: {e}")
except pydapter.exceptions.AdapterError as e:
    print(f"Other adapter error: {e}")
```

See [Error Handling Documentation](docs/error_handling.md) for more details.
