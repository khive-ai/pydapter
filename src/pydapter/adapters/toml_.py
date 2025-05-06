from __future__ import annotations

from pathlib import Path
from typing import TypeVar

import toml
from pydantic import BaseModel, ValidationError

from ..core import Adapter
from ..exceptions import ParseError
from ..exceptions import ValidationError as AdapterValidationError

T = TypeVar("T", bound=BaseModel)


def _ensure_list(d):
    if isinstance(d, list):
        return d
    if isinstance(d, dict) and len(d) == 1 and isinstance(next(iter(d.values())), list):
        return next(iter(d.values()))
    return [d]


class TomlAdapter(Adapter[T]):
    obj_key = "toml"

    @classmethod
    def from_obj(cls, subj_cls: type[T], obj: str | Path, /, *, many=False, **kw):
        try:
            # Handle file path
            if isinstance(obj, Path):
                try:
                    text = Path(obj).read_text()
                except Exception as e:
                    raise ParseError(f"Failed to read TOML file: {e}", source=str(obj))
            else:
                text = obj

            # Check for empty input
            if not text or (isinstance(text, str) and not text.strip()):
                raise ParseError(
                    "Empty TOML content",
                    source=str(obj)[:100] if isinstance(obj, str) else str(obj),
                )

            # Parse TOML
            try:
                parsed = toml.loads(text, **kw)
            except toml.TomlDecodeError as e:
                raise ParseError(
                    f"Invalid TOML: {e}",
                    source=str(text)[:100] if isinstance(text, str) else str(text),
                )

            # Validate against model
            try:
                if many:
                    return [subj_cls.model_validate(x) for x in _ensure_list(parsed)]
                return subj_cls.model_validate(parsed)
            except ValidationError as e:
                raise AdapterValidationError(
                    f"Validation error: {e}",
                    data=parsed,
                    errors=e.errors(),
                )

        except (ParseError, AdapterValidationError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Wrap other exceptions
            raise ParseError(
                f"Unexpected error parsing TOML: {e}",
                source=str(obj)[:100] if isinstance(obj, str) else str(obj),
            )

    @classmethod
    def to_obj(cls, subj: T | list[T], /, *, many=False, **kw) -> str:
        try:
            items = subj if isinstance(subj, list) else [subj]

            if not items:
                return ""

            payload = (
                {"items": [i.model_dump() for i in items]}
                if many
                else items[0].model_dump()
            )
            return toml.dumps(payload, **kw)

        except Exception as e:
            # Wrap exceptions
            raise ParseError(f"Error generating TOML: {e}")
