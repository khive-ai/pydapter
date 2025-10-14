"""
TOML Adapter for Pydantic Models.

This module provides the TomlAdapter class for converting between Pydantic models
and TOML data formats. It supports reading from TOML files or strings and writing
Pydantic models to TOML format.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError
import toml

from ..core import Adapter, AdapterBase, dispatch_adapt_meth
from ..exceptions import PydapterError

T = TypeVar("T", bound=BaseModel)


def _ensure_list(d):
    """
    Helper function to ensure data is in list format when many=True.

    This handles TOML's structure where arrays might be nested in sections.
    """
    if isinstance(d, list):
        return d
    if isinstance(d, dict) and len(d) == 1 and isinstance(next(iter(d.values())), list):
        return next(iter(d.values()))
    return [d]


class TomlAdapter(AdapterBase, Adapter[T]):
    """
    Adapter for converting between Pydantic models and TOML data.

    This adapter handles TOML files and strings, providing methods to:
    - Parse TOML data into Pydantic model instances
    - Convert Pydantic models to TOML format
    - Handle both single objects and arrays of objects

    Attributes:
        adapter_key: The key identifier for this adapter type ("toml")
        obj_key: Legacy key identifier for backward compatibility ("toml")

    Example:
        ```python
        from pydantic import BaseModel
        from pydapter.adapters.toml_ import TomlAdapter

        class Person(BaseModel):
            name: str
            age: int

        # Parse TOML data
        toml_data = '''
        name = "John"
        age = 30
        '''
        person = TomlAdapter.from_obj(Person, toml_data)

        # Parse TOML array
        toml_array = '''
        [[people]]
        name = "John"
        age = 30

        [[people]]
        name = "Jane"
        age = 25
        '''
        people = TomlAdapter.from_obj(Person, toml_array, many=True)

        # Convert to TOML
        toml_output = TomlAdapter.to_obj(person)
        ```
    """

    adapter_key = "toml"
    obj_key = "toml"  # Backward compatibility

    # Declarative exception handling
    parse_errors = (toml.TomlDecodeError,)

    # ---------------- incoming helpers
    @classmethod
    def _read_obj_to_toml(cls, obj: str | Path, **kw) -> dict | list:
        """Read and parse TOML from file or string."""
        text = None

        # Read from Path
        if isinstance(obj, Path):
            try:
                text = obj.read_text()
            except Exception as e:
                cls._handle_error(e, "resource", resource=str(obj))
        else:
            text = obj

        # Check for empty input
        if not text or (isinstance(text, str) and not text.strip()):
            cls._handle_error(
                ValueError("Empty TOML content"),
                "parse",
                source=text,
            )

        # Parse TOML
        try:
            return toml.loads(text, **kw)
        except cls.parse_errors as e:
            cls._handle_error(
                e,
                "parse",
                source=text,
            )

    @classmethod
    def _validate(
        cls,
        data: dict | list,
        subj_cls: type[T],
        many: bool,
        adapt_meth: str | Callable,
        adapt_kw: dict | None,
        validation_errors: tuple[type[Exception], ...],
    ) -> T | list[T]:
        """Validate parsed TOML data against model."""
        try:
            if many:
                # Ensure data is in list format for TOML's structure
                data_list = _ensure_list(data)
                return [dispatch_adapt_meth(adapt_meth, i, adapt_kw, subj_cls) for i in data_list]
            return dispatch_adapt_meth(adapt_meth, data, adapt_kw, subj_cls)
        except validation_errors as e:
            cls._handle_error(e, "validation", data=data, errors=e.errors())

    # ---------------- incoming
    @classmethod
    def from_obj(
        cls,
        subj_cls: type[T],
        obj: str | Path,
        /,
        *,
        many=False,
        adapt_meth: str | Callable = "model_validate",
        adapt_kw: dict | None = None,
        validation_errors: tuple[type[Exception], ...] = (ValidationError,),
        **kw,
    ):
        try:
            # Parse TOML
            toml_data = cls._read_obj_to_toml(obj, **kw)

            # Validate against model
            return cls._validate(toml_data, subj_cls, many, adapt_meth, adapt_kw, validation_errors)

        except PydapterError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Catch any unexpected errors and wrap them
            cls._handle_error(e, "parse", unexpected=True)

    # ---------------- outgoing
    @classmethod
    def to_obj(
        cls,
        subj: T | list[T],
        /,
        *,
        many=False,
        adapt_meth: str | Callable = "model_dump",
        adapt_kw: dict | None = None,
        **kw,
    ) -> str:
        items = subj if isinstance(subj, list) else [subj]

        if not items:
            return ""

        if many:
            payload = {
                "items": [dispatch_adapt_meth(adapt_meth, i, adapt_kw, type(i)) for i in items]
            }
        else:
            payload = dispatch_adapt_meth(adapt_meth, items[0], adapt_kw, type(items[0]))

        return toml.dumps(payload, **kw)
