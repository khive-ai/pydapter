from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from ..core import Adapter
from ..exceptions import ParseError
from ..exceptions import ValidationError as AdapterValidationError

T = TypeVar("T", bound=BaseModel)


class CsvAdapter(Adapter[T]):
    obj_key = "csv"

    # Default CSV dialect settings
    DEFAULT_CSV_KWARGS = {
        "escapechar": "\\",
        "quotechar": '"',
        "delimiter": ",",
        "quoting": csv.QUOTE_MINIMAL,
    }

    # ---------------- incoming
    @classmethod
    def from_obj(
        cls,
        subj_cls: type[T],
        obj: str | Path,
        /,
        *,
        many: bool = True,
        **kw,
    ):
        try:
            # Handle file path or string content
            if isinstance(obj, Path):
                try:
                    text = Path(obj).read_text()
                except Exception as e:
                    raise ParseError(f"Failed to read CSV file: {e}", source=str(obj))
            else:
                text = obj

            # Sanitize text to remove NULL bytes
            text = text.replace("\0", "")

            if not text.strip():
                raise ParseError(
                    "Empty CSV content",
                    source=str(obj)[:100] if isinstance(obj, str) else str(obj),
                )

            # Merge default CSV kwargs with user-provided kwargs
            csv_kwargs = cls.DEFAULT_CSV_KWARGS.copy()
            csv_kwargs.update(kw)  # User-provided kwargs override defaults

            # Parse CSV
            try:
                reader = csv.DictReader(io.StringIO(text), **csv_kwargs)
                rows = list(reader)

                if not rows:
                    return [] if many else None

                # Check for missing fieldnames
                if not reader.fieldnames:
                    raise ParseError("CSV has no headers", source=text[:100])

                # Check for missing required fields in the model
                model_fields = subj_cls.model_fields
                required_fields = [
                    field for field, info in model_fields.items() if info.is_required()
                ]

                missing_fields = [
                    field for field in required_fields if field not in reader.fieldnames
                ]

                if missing_fields:
                    raise ParseError(
                        f"CSV missing required fields: {', '.join(missing_fields)}",
                        source=text[:100],
                        fields=missing_fields,
                    )

                # Convert rows to model instances
                result = []
                for i, row in enumerate(rows):
                    try:
                        result.append(subj_cls.model_validate(row))
                    except ValidationError as e:
                        raise AdapterValidationError(
                            f"Validation error in row {i + 1}: {e}",
                            data=row,
                            row=i + 1,
                            errors=e.errors(),
                        )

                # If there's only one row and many=False, return a single object
                if len(result) == 1 and not many:
                    return result[0]
                # Otherwise, return a list of objects
                return result

            except csv.Error as e:
                raise ParseError(f"CSV parsing error: {e}", source=text[:100])

        except (ParseError, AdapterValidationError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Wrap other exceptions
            raise ParseError(
                f"Unexpected error parsing CSV: {e}",
                source=str(obj)[:100] if isinstance(obj, str) else str(obj),
            )

    # ---------------- outgoing
    @classmethod
    def to_obj(
        cls,
        subj: T | list[T],
        /,
        *,
        many: bool = True,
        **kw,
    ) -> str:
        try:
            items = subj if isinstance(subj, list) else [subj]

            if not items:
                return ""

            buf = io.StringIO()

            # Sanitize any string values to remove NULL bytes
            sanitized_items = []
            for item in items:
                item_dict = item.model_dump()
                for key, value in item_dict.items():
                    if isinstance(value, str):
                        item_dict[key] = value.replace("\0", "")
                sanitized_items.append(item_dict)

            # Merge default CSV kwargs with user-provided kwargs
            csv_kwargs = cls.DEFAULT_CSV_KWARGS.copy()
            csv_kwargs.update(kw)  # User-provided kwargs override defaults

            # Get fieldnames from the first item
            fieldnames = list(items[0].model_dump().keys())

            writer = csv.DictWriter(buf, fieldnames=fieldnames, **csv_kwargs)
            writer.writeheader()
            writer.writerows([i.model_dump() for i in items])
            return buf.getvalue()

        except Exception as e:
            # Wrap exceptions
            raise ParseError(f"Error generating CSV: {e}")
