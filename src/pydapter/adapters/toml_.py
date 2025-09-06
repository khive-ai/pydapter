"""TOML Adapter, obj_key = 'toml'"""

from __future__ import annotations

from pathlib import Path

import toml

from ..core import Adapter
from ..exceptions import ParseError, ResourceError, ValidationError
from ..utils import T, adapt_dump, adapt_from


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


class TomlAdapter(Adapter[T]):
    """
    Adapter for converting between Pydantic models and TOML data.

    Parameters:
        adapt_kw: Parameters passed to Pydantic model methods (model_validate/model_dump)
        **kw: Parameters passed to TOML operations (toml.dumps)

    Example:
        ```python
        # Parse with validation options
        person = TomlAdapter.from_obj(
            Person, toml_data,
            adapt_kw={"strict": True}  # To model_validate
        )

        # Convert with custom options
        toml_output = TomlAdapter.to_obj(
            person,
            adapt_kw={"exclude_unset": True}  # To model_dump
        )
        ```
    """

    obj_key = "toml"

    @classmethod
    def from_obj(
        cls,
        subj_cls: type[T],
        obj: str | Path,
        /,
        *,
        many=False,
        adapt_meth: str = "model_validate",
        adapt_kw: dict | None = None,
        **kw,
    ):
        try:
            # Handle file path
            if isinstance(obj, Path):
                try:
                    text = Path(obj).read_text()
                except Exception as e:
                    raise ResourceError.from_adapter(
                        cls, "Failed to read TOML file", source=obj, cause=e
                    )
            else:
                text = obj

            # Check for empty input
            if not text or (isinstance(text, str) and not text.strip()):
                raise ParseError.from_adapter(cls, "Empty TOML content", source=obj)

            # Parse TOML
            try:
                parsed = toml.loads(text, **kw)
            except toml.TomlDecodeError as e:
                raise ParseError.from_adapter(cls, "Invalid TOML", source=text, cause=e)

            # Validate against model
            try:
                if many:
                    return [
                        adapt_from(subj_cls, x, adapt_meth, adapt_kw)
                        for x in _ensure_list(parsed)
                    ]
                return adapt_from(subj_cls, parsed, adapt_meth, adapt_kw)
            except Exception as e:
                raise ValidationError.from_adapter(
                    cls,
                    "Data conversion failed",
                    data=parsed,
                    adapt_method=adapt_meth,
                    cause=e,
                )

        except (ParseError, ResourceError, ValidationError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Wrap other exceptions
            raise ParseError.from_adapter(
                cls, "Unexpected error parsing TOML", source=obj, cause=e
            )

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
        items = subj if isinstance(subj, list) else [subj]

        if not items:
            return ""

        if many:
            payload = {"items": [adapt_dump(i, adapt_meth, adapt_kw) for i in items]}
        else:
            payload = adapt_dump(items[0], adapt_meth, adapt_kw)

        try:
            return toml.dumps(payload, **kw)
        except Exception as e:
            raise ParseError.from_adapter(
                cls, "Error generating TOML", adapt_method=adapt_meth, cause=e
            )
