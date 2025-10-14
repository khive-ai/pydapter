"""YAML adapter for converting between Python objects and YAML format."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError
import yaml

from ..core import Adapter, AdapterBase, dispatch_adapt_meth
from ..exceptions import PydapterError
from ..exceptions import ValidationError as AdapterValidationError

T = TypeVar("T", bound=BaseModel)


class YamlAdapter(AdapterBase, Adapter[T]):
    """
    YAML adapter for Python objects with support for files, strings, and bytes.

    Example:
        ```python
        # Parse YAML string
        person = YamlAdapter.from_obj(Person, 'name: John\\nage: 30')

        # Parse YAML array
        people = YamlAdapter.from_obj(Person, '[{...}, {...}]', many=True)

        # Convert to YAML
        yaml_str = YamlAdapter.to_obj(person)
        ```
    """

    adapter_key = "yaml"
    obj_key = "yaml"  # Backward compatibility

    # Declarative exception handling
    parse_errors = (yaml.YAMLError,)

    # ---------------- incoming helpers
    @classmethod
    def _read_obj_to_yaml(cls, obj: str | bytes | Path, **kw) -> dict | list:
        """Read and parse YAML from file/string/bytes."""
        text = None

        # Read from Path or decode bytes
        if isinstance(obj, Path):
            try:
                text = obj.read_text()
            except Exception as e:
                cls._handle_error(e, "resource", resource=str(obj))
        else:
            text = obj.decode("utf-8") if isinstance(obj, bytes) else obj

        # Check for empty input
        if not text or (isinstance(text, str) and not text.strip()):
            cls._handle_error(
                ValueError("Empty YAML content"),
                "parse",
                source=text,
            )

        # Parse YAML
        try:
            return yaml.safe_load(text)
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
        """Validate parsed YAML data against model."""
        try:
            if many:
                return [dispatch_adapt_meth(adapt_meth, i, adapt_kw, subj_cls) for i in data]
            return dispatch_adapt_meth(adapt_meth, data, adapt_kw, subj_cls)
        except validation_errors as e:
            cls._handle_error(e, "validation", data=data, errors=e.errors())

    # ---------------- incoming
    @classmethod
    def from_obj(
        cls,
        subj_cls: type[T],
        obj: str | bytes | Path,
        /,
        *,
        many=False,
        adapt_meth: str | Callable = "model_validate",
        adapt_kw: dict | None = None,
        validation_errors: tuple[type[Exception], ...] = (ValidationError,),
        **kw,
    ):
        try:
            # Parse YAML
            yaml_data = cls._read_obj_to_yaml(obj, **kw)

            # Check for array when many=True
            if many and not isinstance(yaml_data, list):
                raise AdapterValidationError(
                    "Expected YAML array for many=True",
                    adapter="yaml",
                    data=yaml_data,
                    details={"data_type": type(yaml_data).__name__, "expected": "list"},
                )

            # Validate against model
            return cls._validate(yaml_data, subj_cls, many, adapt_meth, adapt_kw, validation_errors)

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
            return "[]" if many else "{}"

        # Set default YAML serialization options
        yaml_kwargs = {
            "default_flow_style": False,  # Use block style (more readable)
            "allow_unicode": True,  # Support Unicode characters
            "sort_keys": True,  # Sort dictionary keys
            **kw,  # User overrides
        }

        if many:
            payload = [dispatch_adapt_meth(adapt_meth, i, adapt_kw, type(i)) for i in items]
        else:
            payload = dispatch_adapt_meth(adapt_meth, items[0], adapt_kw, type(items[0]))

        return yaml.safe_dump(payload, **yaml_kwargs)
