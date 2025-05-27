from typing import Protocol, Union, runtime_checkable

from pydantic import JsonValue


@runtime_checkable
class Cryptographical(Protocol):
    """An object that can be hashed with a cryptographic hash function"""

    content: JsonValue
    sha256: str | None = None


class CryptographicalMixin:
    def hash_content(self) -> None:
        if self.content is None:
            raise ValueError("Content is not set.")
        self.sha256 = sha256_of_obj(self.content)


def sha256_of_obj(obj: Union[dict, str, JsonValue]) -> str:
    """Deterministic SHA-256 of an arbitrary mapping."""
    import hashlib

    if isinstance(obj, str):
        return hashlib.sha256(memoryview(obj.encode())).hexdigest()
    import orjson

    payload: bytes = orjson.dumps(
        obj,
        option=(
            orjson.OPT_SORT_KEYS  # canonical ordering
            | orjson.OPT_NON_STR_KEYS  # allow int / enum keys if you need them
        ),
    )
    return hashlib.sha256(memoryview(payload)).hexdigest()
