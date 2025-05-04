from __future__ import annotations

import json
from typing import List, TypeVar

from pydantic import BaseModel

from ..core import Adapter

T = TypeVar("T", bound=BaseModel)


class JsonAdapter(Adapter[T]):
    obj_key = "json"

    # ---------------- incoming
    @classmethod
    def from_obj(cls, subj_cls: type[T], obj: str | bytes, /, *, many=False, **kw):
        data = json.loads(obj)
        if many:
            return [subj_cls.model_validate(i) for i in data]
        return subj_cls.model_validate(data)

    # ---------------- outgoing
    @classmethod
    def to_obj(cls, subj: T | List[T], /, *, many=False, **kw) -> str:
        items = subj if isinstance(subj, list) else [subj]
        payload = [i.model_dump() for i in items] if many else items[0].model_dump()
        return json.dumps(payload, indent=2, sort_keys=True)
