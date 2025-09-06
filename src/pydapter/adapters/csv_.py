"""CSV Adapter, obj_key = 'csv'"""

from __future__ import annotations

import csv
import io
from pathlib import Path

from ..core import Adapter
from ..exceptions import ParseError, ResourceError, ValidationError
from ..utils import T, adapt_dump, adapt_from


class CsvAdapter(Adapter[T]):
    """
    Adapter for converting between Pydantic models and CSV data.

    Parameters:
        adapt_kw: Parameters passed to Pydantic model methods (model_validate/model_dump)
        **kw: Parameters passed to csv.DictReader/DictWriter

    Example:
        ```python
        # Parse with validation options
        people = CsvAdapter.from_obj(
            Person, csv_data, many=True,
            adapt_kw={"strict": True}  # To model_validate
        )

        # Convert with CSV formatting
        csv_output = CsvAdapter.to_obj(
            people, many=True,
            adapt_kw={"exclude_unset": True},  # To model_dump
            delimiter=";", quoting=csv.QUOTE_ALL  # To csv.DictWriter
        )
        ```
    """

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
        adapt_meth: str = "model_validate",
        adapt_kw: dict | None = None,
        **kw,
    ):
        """kw for csv.DictReader."""
        # Handle file path or string content
        if isinstance(obj, Path):
            try:
                text = Path(obj).read_text()
            except Exception as e:
                raise ResourceError.from_adapter(
                    cls, "Failed to read CSV file", source=str(obj), cause=e
                )
        else:
            text = obj

        # Sanitize text to remove NULL bytes
        text = text.replace("\0", "")

        if not text.strip():
            raise ParseError.from_adapter(cls, "Empty CSV content", source=obj)

        # Merge default CSV kwargs with user-provided kwargs
        csv_kwargs = cls.DEFAULT_CSV_KWARGS.copy()
        csv_kwargs.update(kw)  # User-provided kwargs override defaults

        # Parse CSV
        try:
            # Extract specific parameters from csv_kwargs
            delimiter = ","
            quotechar = '"'
            escapechar = "\\"
            quoting = csv.QUOTE_MINIMAL

            if "delimiter" in csv_kwargs:
                delimiter = str(csv_kwargs.pop("delimiter"))
            if "quotechar" in csv_kwargs:
                quotechar = str(csv_kwargs.pop("quotechar"))
            if "escapechar" in csv_kwargs:
                escapechar = str(csv_kwargs.pop("escapechar"))
            if "quoting" in csv_kwargs:
                quoting_value = csv_kwargs.pop("quoting")
                if isinstance(quoting_value, int):
                    quoting = quoting_value
                else:
                    quoting = csv.QUOTE_MINIMAL

            reader = csv.DictReader(
                io.StringIO(text),
                delimiter=delimiter,
                quotechar=quotechar,
                escapechar=escapechar,
                quoting=quoting,
            )
            rows = list(reader)

            if not rows:
                return [] if many else None

            # Check for missing fieldnames
            if not reader.fieldnames:
                raise ParseError.from_adapter(cls, "CSV has no headers", source=text)

            # Convert rows to model instances
            result = []
            for i, row in enumerate(rows):
                try:
                    result.append(adapt_from(subj_cls, row, adapt_meth, adapt_kw))
                except Exception as e:
                    raise ValidationError.from_adapter(
                        cls,
                        f"Data conversion failed in row {i + 1}",
                        row_data=row,
                        row_number=i + 1,
                        adapt_method=adapt_meth,
                        cause=e,
                    )

            # If there's only one row and many=False, return a single object
            if len(result) == 1 and not many:
                return result[0]
            # Otherwise, return a list of objects
            return result

        except csv.Error as e:
            raise ParseError.from_adapter(
                cls, "CSV parsing error", source=text, cause=e
            )
        except (ParseError, ValidationError, ResourceError):
            # Let our custom errors bubble up directly
            raise
        except Exception as e:
            raise ParseError.from_adapter(
                cls, "Unexpected error parsing CSV", source=obj, cause=e
            )

    # ---------------- outgoing
    @classmethod
    def to_obj(
        cls,
        subj: T | list[T],
        /,
        *,
        many: bool = False,
        adapt_meth: str = "model_dump",
        adapt_kw: dict | None = None,
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
                item_dict = adapt_dump(item, adapt_meth, adapt_kw)
                for key, value in item_dict.items():
                    if isinstance(value, str):
                        item_dict[key] = value.replace("\0", "")
                sanitized_items.append(item_dict)

            # Merge default CSV kwargs with user-provided kwargs
            csv_kwargs = cls.DEFAULT_CSV_KWARGS.copy()
            csv_kwargs.update(kw)  # User-provided kwargs override defaults

            fieldnames = list(sanitized_items[0].keys())

            # Extract specific parameters from csv_kwargs
            delimiter = ","
            quotechar = '"'
            escapechar = "\\"
            quoting = csv.QUOTE_MINIMAL

            if "delimiter" in csv_kwargs:
                delimiter = str(csv_kwargs.pop("delimiter"))
            if "quotechar" in csv_kwargs:
                quotechar = str(csv_kwargs.pop("quotechar"))
            if "escapechar" in csv_kwargs:
                escapechar = str(csv_kwargs.pop("escapechar"))
            if "quoting" in csv_kwargs:
                quoting_value = csv_kwargs.pop("quoting")
                if isinstance(quoting_value, int):
                    quoting = quoting_value
                else:
                    quoting = csv.QUOTE_MINIMAL

            writer = csv.DictWriter(
                buf,
                fieldnames=fieldnames,
                delimiter=delimiter,
                quotechar=quotechar,
                escapechar=escapechar,
                quoting=quoting,
            )
            writer.writeheader()
            writer.writerows(sanitized_items)
            return buf.getvalue()

        except Exception as e:
            # Wrap exceptions
            raise ParseError.from_adapter(
                cls, "Error generating CSV", adapt_method=adapt_meth, cause=e
            )
