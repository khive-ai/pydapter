"""CSV adapter for converting between Python objects and CSV format."""

from __future__ import annotations

from collections.abc import Callable
import csv
import io
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from ..core import Adapter, AdapterBase, dispatch_adapt_meth
from ..exceptions import PydapterError

T = TypeVar("T", bound=BaseModel)


class CsvAdapter(AdapterBase, Adapter[T]):
    """
    CSV adapter for Python objects.

    Example:
        ```python
        # Parse CSV string
        person = CsvAdapter.from_obj(Person, 'id,name\n1,John', many=True)

        # Parse CSV file
        people = CsvAdapter.from_obj(Person, Path('data.csv'), many=True)

        # Convert to CSV
        csv_str = CsvAdapter.to_obj(people, many=True)
        ```
    """

    adapter_key = "csv"
    obj_key = "csv"  # Backward compatibility

    # Declarative exception handling
    parse_errors = (csv.Error,)

    # ---------------- incoming helpers
    @classmethod
    def _read_obj_to_csv(cls, obj: str | Path, **kw) -> tuple[list[dict], list[str]]:
        """Read and parse CSV, return (rows, fieldnames)."""
        # Read from Path or string
        if isinstance(obj, Path):
            try:
                text = obj.read_text()
            except Exception as e:
                cls._handle_error(e, "resource", resource=str(obj))
        else:
            text = obj

        # Sanitize NULL bytes
        text = text.replace("\0", "")

        # Check for empty input
        if not text.strip():
            cls._handle_error(ValueError("Empty CSV content"), "parse", source=text)

        # Parse CSV
        try:
            reader = csv.DictReader(io.StringIO(text), **kw)
            rows = list(reader)
            fieldnames = list(reader.fieldnames) if reader.fieldnames else []

            if not fieldnames:
                cls._handle_error(ValueError("CSV has no headers"), "parse", source=text)

            return rows, fieldnames

        except cls.parse_errors as e:
            cls._handle_error(e, "parse", source=text)

    @classmethod
    def _validate(
        cls,
        rows: list[dict],
        fieldnames: list[str],
        subj_cls: type[T],
        many: bool,
        adapt_meth: str | Callable,
        adapt_kw: dict | None,
        validation_errors: tuple[type[Exception], ...],
    ) -> T | list[T]:
        """Validate parsed CSV data against model."""
        # Check for missing required fields
        required_fields = [
            field for field, info in subj_cls.model_fields.items() if info.is_required()
        ]
        missing_fields = [f for f in required_fields if f not in fieldnames]

        if missing_fields:
            cls._handle_error(
                ValueError(f"CSV missing required fields: {', '.join(missing_fields)}"),
                "parse",
                fields=missing_fields,
            )

        # Validate rows
        try:
            result = []
            for i, row in enumerate(rows):
                try:
                    result.append(dispatch_adapt_meth(adapt_meth, row, adapt_kw, subj_cls))
                except validation_errors as e:
                    cls._handle_error(
                        e,
                        "validation",
                        data=row,
                        row=i + 1,
                        errors=e.errors() if hasattr(e, "errors") else str(e),
                    )

            # Return single object if many=False and exactly one row
            if len(result) == 1 and not many:
                return result[0]
            return result

        except validation_errors as e:
            cls._handle_error(e, "validation", data=rows, errors=e.errors())

    # ---------------- incoming
    @classmethod
    def from_obj(
        cls,
        subj_cls: type[T],
        obj: str | Path,
        /,
        *,
        many=True,
        adapt_meth: str | Callable = "model_validate",
        adapt_kw: dict | None = None,
        validation_errors: tuple[type[Exception], ...] = (ValidationError,),
        **kw,
    ):
        try:
            # Parse CSV (single pass)
            rows, fieldnames = cls._read_obj_to_csv(obj, **kw)

            if not rows:
                return [] if many else None

            # Validate against model
            return cls._validate(
                rows, fieldnames, subj_cls, many, adapt_meth, adapt_kw, validation_errors
            )

        except PydapterError:
            raise
        except Exception as e:
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

        # Convert to dicts and sanitize NULL bytes
        data = []
        for item in items:
            row = dispatch_adapt_meth(adapt_meth, item, adapt_kw, type(item))
            # Sanitize string values
            data.append(
                {k: v.replace("\0", "") if isinstance(v, str) else v for k, v in row.items()}
            )

        # Write CSV
        buf = io.StringIO()
        fieldnames = list(data[0].keys())
        writer = csv.DictWriter(buf, fieldnames=fieldnames, **kw)
        writer.writeheader()
        writer.writerows(data)
        return buf.getvalue()
