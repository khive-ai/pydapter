"""JSON adapter for converting between Python objects and JSON format."""

from __future__ import annotations

from collections.abc import Callable
import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from ..core import Adapter, AdapterBase, dispatch_adapt_meth
from ..exceptions import PydapterError
from ..exceptions import ValidationError as AdapterValidationError

T = TypeVar("T", bound=BaseModel)


class JsonAdapter(AdapterBase, Adapter[T]):
    """
    JSON adapter for Python objects with support for files, strings, and bytes.

    Example:
        ```python
        # Parse JSON string
        person = JsonAdapter.from_obj(Person, '{"name": "John", "age": 30}')

        # Parse JSON array
        people = JsonAdapter.from_obj(Person, '[{...}, {...}]', many=True)

        # Convert to JSON
        json_str = JsonAdapter.to_obj(person, indent=4)
        ```
    """

    adapter_key = "json"
    obj_key = "json"  # Backward compatibility

    # Declarative exception handling
    parse_errors = (json.JSONDecodeError,)

    # ---------------- incoming helpers
    @classmethod
    def _read_obj_to_json(cls, obj: str | bytes | Path, **kw) -> dict | list:
        """Read and parse JSON from file/string/bytes."""
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
                ValueError("Empty JSON content"),
                "parse",
                source=str(obj)[:100] if isinstance(obj, str) else str(obj),
            )

        # Parse JSON
        try:
            return json.loads(text, **kw)
        except cls.parse_errors as e:
            cls._handle_error(
                e,
                "parse",
                source=str(text)[:100] if isinstance(text, str) else str(text),
                position=e.pos,
                line=e.lineno,
                column=e.colno,
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
        """Validate parsed JSON data against model."""
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
            # Parse JSON
            json_data = cls._read_obj_to_json(obj, **kw)

            # Check for array when many=True
            if many and not isinstance(json_data, list):
                raise AdapterValidationError(
                    "Expected JSON array for many=True",
                    adapter="json",
                    data=json_data,
                    details={"data_type": type(json_data).__name__, "expected": "list"},
                )

            # Validate against model
            return cls._validate(json_data, subj_cls, many, adapt_meth, adapt_kw, validation_errors)

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

        # Set default JSON serialization options
        json_kwargs = {
            "indent": 2,
            "sort_keys": True,
            "ensure_ascii": False,
            **kw,  # User overrides
        }

        if many:
            payload = [dispatch_adapt_meth(adapt_meth, i, adapt_kw, type(i)) for i in items]
        else:
            payload = dispatch_adapt_meth(adapt_meth, items[0], adapt_kw, type(items[0]))

        return json.dumps(payload, **json_kwargs)
