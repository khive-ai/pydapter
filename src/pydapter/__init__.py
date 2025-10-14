"""pydapter - tiny adapter toolkit."""

from .async_core import AsyncAdaptable, AsyncAdapter, AsyncAdapterRegistry
from .core import Adaptable, Adapter, AdapterBase, AdapterRegistry, dispatch_adapt_meth

__all__ = (
    "Adaptable",
    "Adapter",
    "AdapterBase",
    "AdapterRegistry",
    "dispatch_adapt_meth",
    "AsyncAdaptable",
    "AsyncAdapter",
    "AsyncAdapterRegistry",
)

__version__ = "1.2.0"
