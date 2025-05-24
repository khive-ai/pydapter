"""
Excel adapter (requires pandas + xlsxwriter engine).
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any, TypeVar

import pandas as pd
from pydantic import BaseModel

from ..core import Adapter
from ..exceptions import AdapterError, ResourceError
from .pandas_ import DataFrameAdapter

T = TypeVar("T", bound=BaseModel)


class ExcelAdapter(Adapter[T]):
    """
    Adapter for converting between Pydantic models and Excel files.

    This adapter handles Excel (.xlsx) files, providing methods to:
    - Read Excel files into Pydantic model instances
    - Write Pydantic models to Excel files
    - Support for different sheets and pandas read_excel options

    Attributes:
        obj_key: The key identifier for this adapter type ("xlsx")

    Example:
        ```python
        from pathlib import Path
        from pydantic import BaseModel
        from pydapter.extras.excel_ import ExcelAdapter

        class Person(BaseModel):
            name: str
            age: int

        # Read from Excel file
        excel_file = Path("people.xlsx")
        people = ExcelAdapter.from_obj(Person, excel_file, many=True)

        # Write to Excel file
        output_bytes = ExcelAdapter.to_obj(people, many=True)
        with open("output.xlsx", "wb") as f:
            f.write(output_bytes)
        ```
    """

    obj_key = "xlsx"

    @classmethod
    def from_obj(
        cls,
        subj_cls: type[T],
        obj: str | Path | bytes,
        /,
        *,
        many: bool = True,
        sheet_name: str | int = 0,
        **kw: Any,
    ) -> T | list[T]:
        """
        Convert Excel data to Pydantic model instances.

        Args:
            subj_cls: The Pydantic model class to instantiate
            obj: Excel file path, file-like object, or bytes
            many: If True, convert all rows; if False, convert only first row
            sheet_name: Sheet name or index to read (default: 0)
            **kw: Additional arguments passed to pandas.read_excel

        Returns:
            List of model instances if many=True, single instance if many=False

        Raises:
            ResourceError: If the Excel file cannot be read
            AdapterError: If the data cannot be converted to models
        """
        try:
            if isinstance(obj, bytes):
                df = pd.read_excel(io.BytesIO(obj), sheet_name=sheet_name, **kw)
            else:
                df = pd.read_excel(obj, sheet_name=sheet_name, **kw)
            return DataFrameAdapter.from_obj(subj_cls, df, many=many)
        except FileNotFoundError as e:
            raise ResourceError(f"File not found: {e}", resource=str(obj)) from e
        except ValueError as e:
            raise AdapterError(
                f"Error adapting from xlsx (original_error='{e}')", adapter="xlsx"
            ) from e
        except Exception as e:
            raise AdapterError(
                f"Unexpected error in Excel adapter: {e}", adapter="xlsx"
            ) from e

    # outgoing
    @classmethod
    def to_obj(
        cls,
        subj: T | list[T],
        /,
        *,
        many=True,
        sheet_name="Sheet1",
        **kw,
    ) -> bytes:
        df = DataFrameAdapter.to_obj(subj, many=many)
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="xlsxwriter") as wr:
            df.to_excel(wr, sheet_name=sheet_name, index=False)
        return buf.getvalue()
