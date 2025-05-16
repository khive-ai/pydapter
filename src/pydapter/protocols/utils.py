# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

import asyncio
import contextlib
import functools
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import cache
from typing import TypeVar
from uuid import UUID

from pydantic import BaseModel

Import = TypeVar("I")

HasLen = TypeVar("HasLen")
Bin = list[int]
T = TypeVar("T")

__all__ = (
    "get_bins",
    "import_module",
    "sha256_of_dict",
    "convert_to_datetime",
    "validate_uuid",
    "validate_model_to_dict",
    "is_package_installed",
    "is_coroutine_function",
    "as_async_fn",
)


def import_module(
    package_name: str,
    module_name: str | None = None,
    import_name: str | list | None = None,
) -> Import | list[Import]:
    """Import a module by its path."""
    try:
        full_import_path = (
            f"{package_name}.{module_name}" if module_name else package_name
        )

        if import_name:
            import_name = (
                [import_name] if not isinstance(import_name, list) else import_name
            )
            a = __import__(
                full_import_path,
                fromlist=import_name,
            )
            if len(import_name) == 1:
                return getattr(a, import_name[0])
            return [getattr(a, name) for name in import_name]
        return __import__(full_import_path)

    except ImportError as e:
        error_msg = f"Failed to import module {full_import_path}: {e}"
        raise ImportError(error_msg) from e


def is_package_installed(package_name: str):
    from importlib.util import find_spec

    return find_spec(package_name) is not None


def get_bins(input_: list[HasLen], /, upper: int) -> list[Bin]:
    """Organizes indices of items into bins based on a cumulative upper limit length.

    Args:
        input_ (list[str]): The list of strings to be binned.
        upper (int): The cumulative length upper limit for each bin.

    Returns:
        list[list[int]]: A list of bins, each bin is a list of indices from the input list.
    """
    current = 0
    bins = []
    current_bin = []
    for idx, item in enumerate(input_):
        if current + len(item) < upper:
            current_bin.append(idx)
            current += len(item)
        else:
            bins.append(current_bin)
            current_bin = [idx]
            current = len(item)
    if current_bin:
        bins.append(current_bin)
    return bins


def sha256_of_dict(obj: dict) -> str:
    """Deterministic SHA-256 of an arbitrary mapping."""
    import hashlib

    import orjson

    payload: bytes = orjson.dumps(
        obj,
        option=(
            orjson.OPT_SORT_KEYS  # canonical ordering
            | orjson.OPT_NON_STR_KEYS  # allow int / enum keys if you need them
        ),
    )
    return hashlib.sha256(memoryview(payload)).hexdigest()


def convert_to_datetime(v):
    if isinstance(v, datetime):
        return v
    if isinstance(v, str):
        with contextlib.suppress(ValueError):
            return datetime.fromisoformat(v)

    error_msg = "Input value for field <created_at> should be a `datetime.datetime` object or `isoformat` string"
    raise ValueError(error_msg)


def validate_uuid(v: str | UUID) -> UUID:
    if isinstance(v, UUID):
        return v
    try:
        return UUID(str(v))
    except Exception as e:
        error_msg = "Input value for field <id> should be a `uuid.UUID` object or a valid `uuid` representation"
        raise ValueError(error_msg) from e


def validate_model_to_dict(v):
    """Serialize a Pydantic model to a dictionary. kwargs are passed to model_dump."""

    if isinstance(v, BaseModel):
        return v.model_dump()
    if v is None:
        return {}
    if isinstance(v, dict):
        return v

    error_msg = "Input value for field <model> should be a `pydantic.BaseModel` object or a `dict`"
    raise ValueError(error_msg)


@cache
def is_coroutine_function(fn, /) -> bool:
    """Check if a function is a coroutine function."""
    return asyncio.iscoroutinefunction(fn)


def force_async(fn: Callable[..., T], /) -> Callable[..., Callable[..., T]]:
    """force a function to be async."""
    pool = ThreadPoolExecutor()

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        future = pool.submit(fn, *args, **kwargs)
        return asyncio.wrap_future(future)  # Make it awaitable

    return wrapper


@cache
def as_async_fn(fn, /):
    """forcefully get the async call of a function"""
    if is_coroutine_function(fn):
        return fn
    return force_async(fn)
