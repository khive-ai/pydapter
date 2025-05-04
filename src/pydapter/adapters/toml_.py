from __future__ import annotations

from pathlib import Path
from typing import List, TypeVar

import toml
from pydantic import BaseModel

from ..core import Adapter

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
        text = (
            Path(obj).read_text()
            if isinstance(obj, (str, Path)) and Path(obj).exists()
            else obj
        )
        parsed = toml.loads(text, **kw)
        if many:
            return [subj_cls.model_validate(x) for x in _ensure_list(parsed)]
        return subj_cls.model_validate(parsed)

    @classmethod
    def to_obj(cls, subj: T | List[T], /, *, many=False, **kw) -> str:
        items = subj if isinstance(subj, list) else [subj]
        payload = (
            {"items": [i.model_dump() for i in items]}
            if many
            else items[0].model_dump()
        )
        return toml.dumps(payload, **kw)
