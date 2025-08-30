"""
pydapter - tiny adapter toolkit.
"""

from .async_core import AsyncAdaptable, AsyncAdapter, AsyncAdapterRegistry
from .core import Adaptable, Adapter, AdapterRegistry

__all__ = (
    "Adaptable",
    "Adapter",
    "AdapterRegistry",
    "AsyncAdaptable",
    "AsyncAdapter",
    "AsyncAdapterRegistry",
)

__version__ = "1.0.5"
