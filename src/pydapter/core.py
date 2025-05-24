"""
pydapter.core - Adapter protocol, registry, Adaptable mix-in.
"""

from __future__ import annotations

from typing import Any, ClassVar, Protocol, TypeVar, runtime_checkable

from .exceptions import (
    PYDAPTER_PYTHON_ERRORS,
    AdapterError,
    AdapterNotFoundError,
    ConfigurationError,
)

T = TypeVar("T", contravariant=True)


# ------------------------------------------------------------------ Adapter
@runtime_checkable
class Adapter(Protocol[T]):
    """
    Protocol defining the interface for data format adapters.

    Adapters are stateless conversion helpers that transform data between
    Pydantic models and various formats (CSV, JSON, TOML, etc.).

    Attributes:
        obj_key: Unique identifier for the adapter type (e.g., "csv", "json")

    Example:
        ```python
        from pydantic import BaseModel
        from pydapter.adapters.json_ import JsonAdapter

        class Person(BaseModel):
            name: str
            age: int

        # Convert from JSON to Pydantic model
        json_data = '{"name": "John", "age": 30}'
        person = JsonAdapter.from_obj(Person, json_data)

        # Convert from Pydantic model to JSON
        json_output = JsonAdapter.to_obj(person)
        ```
    """

    obj_key: ClassVar[str]

    @classmethod
    def from_obj(
        cls, subj_cls: type[T], obj: Any, /, *, many: bool = False, **kw: Any
    ) -> T | list[T]:
        """
        Convert from external format to Pydantic model instances.

        Args:
            subj_cls: The Pydantic model class to instantiate
            obj: The source data in the adapter's format
            many: If True, expect/return a list of instances
            **kw: Additional adapter-specific arguments

        Returns:
            Single model instance or list of instances based on 'many' parameter
        """
        ...

    @classmethod
    def to_obj(cls, subj: T | list[T], /, *, many: bool = False, **kw: Any) -> Any:
        """
        Convert from Pydantic model instances to external format.

        Args:
            subj: Single model instance or list of instances
            many: If True, handle as list of instances
            **kw: Additional adapter-specific arguments

        Returns:
            Data in the adapter's external format
        """
        ...


# ----------------------------------------------------------- AdapterRegistry
class AdapterRegistry:
    """
    Registry for managing and accessing data format adapters.

    The registry maintains a mapping of adapter keys to adapter classes,
    providing a centralized way to register and retrieve adapters for
    different data formats.

    Example:
        ```python
        from pydapter.core import AdapterRegistry
        from pydapter.adapters.json_ import JsonAdapter

        registry = AdapterRegistry()
        registry.register(JsonAdapter)

        # Use the registry to adapt data
        json_data = '{"name": "John", "age": 30}'
        person = registry.adapt_from(Person, json_data, obj_key="json")
        ```
    """

    def __init__(self) -> None:
        """Initialize an empty adapter registry."""
        self._reg: dict[str, type[Adapter]] = {}

    def register(self, adapter_cls: type[Adapter]) -> None:
        """
        Register an adapter class with the registry.

        Args:
            adapter_cls: The adapter class to register. Must have an 'obj_key' attribute.

        Raises:
            ConfigurationError: If the adapter class doesn't define 'obj_key'
        """
        key = getattr(adapter_cls, "obj_key", None)
        if not key:
            raise ConfigurationError(
                "Adapter must define 'obj_key'", adapter_cls=adapter_cls.__name__
            )
        self._reg[key] = adapter_cls

    def get(self, obj_key: str) -> type[Adapter]:
        """
        Retrieve an adapter class by its key.

        Args:
            obj_key: The key identifier for the adapter

        Returns:
            The adapter class associated with the key

        Raises:
            AdapterNotFoundError: If no adapter is registered for the given key
        """
        try:
            return self._reg[obj_key]
        except KeyError as exc:
            raise AdapterNotFoundError(
                f"No adapter registered for '{obj_key}'", obj_key=obj_key
            ) from exc

    def adapt_from(
        self, subj_cls: type[T], obj: Any, *, obj_key: str, **kw: Any
    ) -> T | list[T]:
        """
        Convenience method to convert from external format to Pydantic model.

        Args:
            subj_cls: The Pydantic model class to instantiate
            obj: The source data in the specified format
            obj_key: The key identifying which adapter to use
            **kw: Additional adapter-specific arguments

        Returns:
            Model instance(s) created from the source data

        Raises:
            AdapterNotFoundError: If no adapter is registered for obj_key
            AdapterError: If the adaptation process fails
        """
        try:
            result = self.get(obj_key).from_obj(subj_cls, obj, **kw)
            if result is None:
                raise AdapterError(f"Adapter {obj_key} returned None", adapter=obj_key)
            return result

        except Exception as exc:
            if isinstance(exc, AdapterError) or isinstance(exc, PYDAPTER_PYTHON_ERRORS):
                raise

            raise AdapterError(
                f"Error adapting from {obj_key}", original_error=str(exc)
            ) from exc

    def adapt_to(self, subj: Any, *, obj_key: str, **kw: Any) -> Any:
        """
        Convenience method to convert from Pydantic model to external format.

        Args:
            subj: The model instance(s) to convert
            obj_key: The key identifying which adapter to use
            **kw: Additional adapter-specific arguments

        Returns:
            Data in the specified external format

        Raises:
            AdapterNotFoundError: If no adapter is registered for obj_key
            AdapterError: If the adaptation process fails
        """
        try:
            result = self.get(obj_key).to_obj(subj, **kw)
            if result is None:
                raise AdapterError(f"Adapter {obj_key} returned None", adapter=obj_key)
            return result

        except Exception as exc:
            if isinstance(exc, AdapterError) or isinstance(exc, PYDAPTER_PYTHON_ERRORS):
                raise

            raise AdapterError(
                f"Error adapting to {obj_key}", original_error=str(exc)
            ) from exc


# ----------------------------------------------------------------- Adaptable
class Adaptable:
    """
    Mixin class that adds adapter functionality to Pydantic models.

    This mixin provides convenient methods for converting to/from various data formats
    by maintaining a registry of adapters and providing high-level convenience methods.

    When mixed into a Pydantic model, it adds:
    - Class methods for registering adapters
    - Class methods for creating instances from external formats
    - Instance methods for converting to external formats

    Example:
        ```python
        from pydantic import BaseModel
        from pydapter.core import Adaptable
        from pydapter.adapters.json_ import JsonAdapter

        class Person(BaseModel, Adaptable):
            name: str
            age: int

        # Register an adapter
        Person.register_adapter(JsonAdapter)

        # Create from JSON
        json_data = '{"name": "John", "age": 30}'
        person = Person.adapt_from(json_data, obj_key="json")

        # Convert to JSON
        json_output = person.adapt_to(obj_key="json")
        ```
    """

    _adapter_registry: ClassVar[AdapterRegistry | None] = None

    @classmethod
    def _registry(cls) -> AdapterRegistry:
        """Get or create the adapter registry for this class."""
        if cls._adapter_registry is None:
            cls._adapter_registry = AdapterRegistry()
        return cls._adapter_registry

    @classmethod
    def register_adapter(cls, adapter_cls: type[Adapter]) -> None:
        """
        Register an adapter class with this model.

        Args:
            adapter_cls: The adapter class to register
        """
        cls._registry().register(adapter_cls)

    @classmethod
    def adapt_from(cls, obj: Any, *, obj_key: str, **kw: Any) -> Any:
        """
        Create model instance(s) from external data format.

        Args:
            obj: The source data in the specified format
            obj_key: The key identifying which adapter to use
            **kw: Additional adapter-specific arguments

        Returns:
            Model instance(s) created from the source data
        """
        return cls._registry().adapt_from(cls, obj, obj_key=obj_key, **kw)

    def adapt_to(self, *, obj_key: str, **kw: Any) -> Any:
        """
        Convert this model instance to external data format.

        Args:
            obj_key: The key identifying which adapter to use
            **kw: Additional adapter-specific arguments

        Returns:
            Data in the specified external format
        """
        return self._registry().adapt_to(self, obj_key=obj_key, **kw)
