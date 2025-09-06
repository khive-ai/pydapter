"""JSON Adapter, obj_key = 'json'"""

from __future__ import annotations

import json
from pathlib import Path

from ..core import Adapter
from ..exceptions import ParseError, ResourceError, ValidationError
from ..utils import T, adapt_dump, adapt_from


class JsonAdapter(Adapter[T]):
    """
    Adapter for converting between Pydantic models and JSON data.

    Parameters:
        adapt_kw: Parameters passed to Pydantic model methods (model_validate/model_dump)
        **kw: Parameters passed to JSON operations (json.loads/json.dumps)

    Example:
        ```python
        # Parse with validation options
        person = JsonAdapter.from_obj(
            Person, json_data,
            adapt_kw={"strict": True}  # To model_validate
        )

        # Convert with formatting
        json_output = JsonAdapter.to_obj(
            person,
            adapt_kw={"exclude_unset": True},  # To model_dump
            indent=4, sort_keys=True           # To json.dumps
        )
        ```
    """

    obj_key = "json"

    # ---------------- incoming
    @classmethod
    def from_obj(
        cls,
        subj_cls: type[T],
        obj: str | bytes | Path,
        /,
        *,
        many=False,
        adapt_meth: str = "model_validate",
        adapt_kw: dict | None = None,
        **kw,
    ):
        # Handle file path
        if isinstance(obj, Path):
            try:
                text = Path(obj).read_text()
            except Exception as e:
                raise ResourceError.from_adapter(
                    cls, "Failed to read JSON file", source=obj, cause=e
                )
        else:
            text = obj.decode("utf-8") if isinstance(obj, bytes) else obj
        # Check for empty input
        if not text or (isinstance(text, str) and not text.strip()):
            raise ParseError.from_adapter(cls, "Empty JSON content", source=obj)

        # Parse JSON
        try:
            data = json.loads(text, **kw)
        except json.JSONDecodeError as e:
            raise ParseError.from_adapter(
                cls,
                f"Invalid JSON: {e}",
                source=text,
                position=e.pos,
                line=e.lineno,
                column=e.colno,
                cause=e,
            )

        # Convert to target class instances
        try:
            if many:
                if not isinstance(data, list):
                    raise ValidationError.from_adapter(
                        cls, "Expected JSON array for many=True", data=data
                    )
                return [adapt_from(subj_cls, i, adapt_meth, adapt_kw) for i in data]
            return adapt_from(subj_cls, data, adapt_meth, adapt_kw)
        except Exception as e:
            raise ValidationError.from_adapter(
                cls,
                "Data conversion failed",
                data=data,
                adapt_method=adapt_meth,
                cause=e,
            )

    # ---------------- outgoing
    @classmethod
    def to_obj(
        cls,
        subj: T | list[T],
        /,
        *,
        many=False,
        adapt_meth: str = "model_dump",
        adapt_kw: dict | None = None,
        **kw,
    ) -> str:
        try:
            items = subj if isinstance(subj, list) else [subj]

            if not items:
                return "[]" if many else "{}"

            # Extract JSON serialization options from kwargs
            json_kwargs = {
                "indent": kw.pop("indent", 2),
                "sort_keys": kw.pop("sort_keys", True),
                "ensure_ascii": kw.pop("ensure_ascii", False),
            }

            payload = (
                [adapt_dump(i, adapt_meth, adapt_kw) for i in items]
                if many
                else adapt_dump(items[0], adapt_meth, adapt_kw)
            )
            return json.dumps(payload, **json_kwargs)

        except Exception as e:
            # Wrap exceptions
            raise ParseError.from_adapter(
                cls, "Error generating JSON", adapt_method=adapt_meth, cause=e
            )
