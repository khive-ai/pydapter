from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from ..core import Adapter
from ..exceptions import ParseError
from ..exceptions import ValidationError as AdapterValidationError

T = TypeVar("T", bound=BaseModel)


class JsonAdapter(Adapter[T]):
    obj_key = "json"

    # ---------------- incoming
    @classmethod
    def from_obj(
        cls, subj_cls: type[T], obj: str | bytes | Path, /, *, many=False, **kw
    ):
        try:
            # Handle file path
            if isinstance(obj, Path):
                try:
                    text = Path(obj).read_text()
                except Exception as e:
                    raise ParseError(f"Failed to read JSON file: {e}", source=str(obj))
            else:
                text = obj
            # Check for empty input
            if not text or (isinstance(text, str) and not text.strip()):
                raise ParseError(
                    "Empty JSON content",
                    source=str(obj)[:100] if isinstance(obj, str) else str(obj),
                )

            # Parse JSON
            try:
                data = json.loads(text)
            except json.JSONDecodeError as e:
                raise ParseError(
                    f"Invalid JSON: {e}",
                    source=str(text)[:100] if isinstance(text, str) else str(text),
                    position=e.pos,
                    line=e.lineno,
                    column=e.colno,
                )

            # Validate against model
            try:
                if many:
                    if not isinstance(data, list):
                        raise AdapterValidationError(
                            "Expected JSON array for many=True", data=data
                        )
                    return [subj_cls.model_validate(i) for i in data]
                return subj_cls.model_validate(data)
            except ValidationError as e:
                raise AdapterValidationError(
                    f"Validation error: {e}",
                    data=data,
                    errors=e.errors(),
                )

        except (ParseError, AdapterValidationError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Wrap other exceptions
            raise ParseError(
                f"Unexpected error parsing JSON: {e}",
                source=str(obj)[:100] if isinstance(obj, str) else str(obj),
            )

    # ---------------- outgoing
    @classmethod
    def to_obj(cls, subj: T | list[T], /, *, many=False, **kw) -> str:
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

            payload = [i.model_dump() for i in items] if many else items[0].model_dump()
            return json.dumps(payload, **json_kwargs)

        except Exception as e:
            # Wrap exceptions
            raise ParseError(f"Error generating JSON: {e}")
