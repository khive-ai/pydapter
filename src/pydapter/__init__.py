"""
pydapter - tiny trait + adapter toolkit.
"""

from .async_core import AsyncAdaptable, AsyncAdapter, AsyncAdapterRegistry
from .core import Adaptable, Adapter, AdapterRegistry
from .fields import (
    ID,
    Embedding,
    Execution,
    Field,
    Undefined,
    UndefinedType,
    create_model,
)
from .protocols import Event, as_event

__all__ = (
    "Adaptable",
    "Adapter",
    "AdapterRegistry",
    "AsyncAdaptable",
    "AsyncAdapter",
    "AsyncAdapterRegistry",
    "Field",
    "create_model",
    "Execution",
    "Embedding",
    "ID",
    "Undefined",
    "UndefinedType",
    "Event",
    "as_event",
)

__version__ = "0.3.0"
