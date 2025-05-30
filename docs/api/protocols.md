# Protocols API Reference

This page provides API documentation for the `pydapter.protocols` module.

## Installation

```bash
pip install pydapter
```

## Overview

The protocols module provides composable interfaces for specialized model behavior:

```text
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   Identifiable  │  │    Temporal     │  │   Embeddable    │
│   (id: UUID)    │  │ (timestamps)    │  │ (content +      │
│                 │  │                 │  │  embedding)     │
└─────────────────┘  └─────────────────┘  └─────────────────┘

┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│    Invokable    │  │ Cryptographical │  │   Auditable     │
│ (execution)     │  │ (hashing)       │  │ (tracking)      │
└─────────────────┘  └─────────────────┘  └─────────────────┘

┌─────────────────┐
│ SoftDeletable   │
│ (soft delete)   │
└─────────────────┘
```

## Quick Start

```python
from pydapter.protocols import IdentifiableMixin, TemporalMixin
from pydantic import BaseModel

class User(BaseModel, IdentifiableMixin, TemporalMixin):
    name: str
    email: str

user = User(name="John", email="john@example.com")
user.update_timestamp()  # Temporal behavior
print(user.id)           # UUID from Identifiable
```

## Event System

```python
from pydapter.protocols.event import as_event

@as_event(event_type="api_call")
async def process_request(data: dict) -> dict:
    return {"result": "processed", "input": data}

event = await process_request({"user_id": 123})
print(event.event_type)  # "api_call"
```

## Protocol Factory

```python
from pydapter.protocols.factory import create_protocol_model_class
from pydapter.protocols.constants import IDENTIFIABLE, TEMPORAL

User = create_protocol_model_class(
    "User",
    IDENTIFIABLE,
    TEMPORAL,
    name=FieldTemplate(base_type=str),
    email=FieldTemplate(base_type=str)
)
```

---

## API Reference

### Core Protocols

::: pydapter.protocols.identifiable
    options:
      show_root_heading: true
      show_source: true

::: pydapter.protocols.temporal
    options:
      show_root_heading: true
      show_source: true

::: pydapter.protocols.embeddable
    options:
      show_root_heading: true
      show_source: true

::: pydapter.protocols.invokable
    options:
      show_root_heading: true
      show_source: true

::: pydapter.protocols.cryptographical
    options:
      show_root_heading: true
      show_source: true

::: pydapter.protocols.auditable
    options:
      show_root_heading: true
      show_source: true

::: pydapter.protocols.soft_deletable
    options:
      show_root_heading: true
      show_source: true

### Event System

::: pydapter.protocols.event
    options:
      show_root_heading: true
      show_source: true

### Factory and Utilities

::: pydapter.protocols.factory
    options:
      show_root_heading: true
      show_source: true

::: pydapter.protocols.registry
    options:
      show_root_heading: true
      show_source: true

::: pydapter.protocols.constants
    options:
      show_root_heading: true
      show_source: true

::: pydapter.protocols.types
    options:
      show_root_heading: true
      show_source: true

::: pydapter.protocols.utils
    options:
      show_root_heading: true
      show_source: true
