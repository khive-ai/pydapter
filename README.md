# pydapter

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
