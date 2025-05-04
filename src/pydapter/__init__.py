"""
pydapter - tiny trait + adapter toolkit.
"""

from .core import Adaptable, Adapter, AdapterRegistry
from .async_core import AsyncAdaptable, AsyncAdapter, AsyncAdapterRegistry

__all__ = ["Adaptable", "Adapter", "AdapterRegistry",
           "AsyncAdaptable", "AsyncAdapter", "AsyncAdapterRegistry"]
__version__ = "0.1.0"
