"""
pydapter - tiny trait + adapter toolkit.
"""

from .async_core import AsyncAdaptable, AsyncAdapter, AsyncAdapterRegistry
from .core import Adaptable, Adapter, AdapterRegistry

__all__ = [
    "Adaptable",
    "Adapter",
    "AdapterRegistry",
    "AsyncAdaptable",
    "AsyncAdapter",
    "AsyncAdapterRegistry",
]
__version__ = "0.1.5"
