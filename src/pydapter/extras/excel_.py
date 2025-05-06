"""
Excel adapter (requires pandas + xlsxwriter engine).
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import TypeVar

import pandas as pd
from pydantic import BaseModel

from ..core import Adapter
from ..exceptions import AdapterError, ResourceError
from .pandas_ import DataFrameAdapter

T = TypeVar("T", bound=BaseModel)


class ExcelAdapter(Adapter[T]):
    obj_key = "xlsx"

    # incoming
    @classmethod
    def from_obj(
        cls,
        subj_cls: type[T],
        obj: str | Path | bytes,
        /,
        *,
        many=True,
        sheet_name=0,
        **kw,
    ):
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
