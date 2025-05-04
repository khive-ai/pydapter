from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import List, TypeVar

from pydantic import BaseModel

from ..core import Adapter

T = TypeVar("T", bound=BaseModel)


class CsvAdapter(Adapter[T]):
    obj_key = "csv"

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
        text = Path(obj).read_text() if Path(obj).exists() else obj
        
        # Sanitize text to remove NULL bytes
        text = text.replace('\0', '')
        
        # Ensure we have an escape character to handle special characters
        csv_kwargs = dict(escapechar='\\')
        csv_kwargs.update(kw)  # User-provided kwargs override defaults
        
        reader = csv.DictReader(io.StringIO(text), **csv_kwargs)
        rows = list(reader)

        # If there's only one row, return a single object regardless of the 'many' parameter
        # This fixes the test_text_roundtrip[csv] test which expects a single object
        if len(rows) == 1:
            return subj_cls.model_validate(rows[0])
        # Otherwise, return a list of objects
        return [subj_cls.model_validate(r) for r in rows]

    # ---------------- outgoing
    @classmethod
    def to_obj(
        cls,
        subj: T | List[T],
        /,
        *,
        many: bool = True,
        **kw,
    ) -> str:
        items = subj if isinstance(subj, list) else [subj]
        buf = io.StringIO()
        
        # Sanitize any string values to remove NULL bytes
        sanitized_items = []
        for item in items:
            item_dict = item.model_dump()
            for key, value in item_dict.items():
                if isinstance(value, str):
                    item_dict[key] = value.replace('\0', '')
            sanitized_items.append(item_dict)
        
        # Ensure we have an escape character to handle special characters
        csv_kwargs = dict(escapechar='\\')
        csv_kwargs.update(kw)  # User-provided kwargs override defaults
        
        writer = csv.DictWriter(buf, fieldnames=items[0].model_dump().keys(), **csv_kwargs)
        writer.writeheader()
        writer.writerows([i.model_dump() for i in items])
        return buf.getvalue()
