"""
DataFrame & Series adapters (require `pandas`).
"""

from __future__ import annotations

from typing import TypeVar

import pandas as pd
from pydantic import BaseModel

from ..core import Adapter

T = TypeVar("T", bound=BaseModel)


class DataFrameAdapter(Adapter[T]):
    obj_key = "pd.DataFrame"

    @classmethod
    def from_obj(cls, subj_cls: type[T], obj: pd.DataFrame, /, *, many=True, **kw):
        if many:
            return [subj_cls.model_validate(r) for r in obj.to_dict(orient="records")]
        return subj_cls.model_validate(obj.iloc[0].to_dict(), **kw)

    @classmethod
    def to_obj(cls, subj: T | list[T], /, *, many=True, **kw) -> pd.DataFrame:
        items = subj if isinstance(subj, list) else [subj]
        return pd.DataFrame([i.model_dump() for i in items], **kw)


class SeriesAdapter(Adapter[T]):
    obj_key = "pd.Series"

    @classmethod
    def from_obj(cls, subj_cls: type[T], obj: pd.Series, /, *, many=False, **kw):
        if many:
            raise ValueError("SeriesAdapter supports single records only.")
        return subj_cls.model_validate(obj.to_dict(), **kw)

    @classmethod
    def to_obj(cls, subj: T, /, *, many=False, **kw) -> pd.Series:
        if many:
            raise ValueError("SeriesAdapter supports single records only.")
        return pd.Series(subj.model_dump(), **kw)
