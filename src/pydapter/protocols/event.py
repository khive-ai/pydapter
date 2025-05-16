import json
from collections.abc import Callable
from functools import wraps
from typing import Any

from ..async_core import AsyncAdapter
from .embedable import Embedable
from .invokable import Invokable
from .types import Embedding, Log
from .utils import as_async_fn, validate_model_to_dict


class Event(Invokable, Embedable):
    event_type: str = None

    def __init__(
        self,
        event_invoke_function: Callable,
        event_invoke_args: list[Any],
        event_invoke_kwargs: dict[str, Any],
        event_type: str = None,
    ):
        super().__init__(response_obj=None)
        self._invoke_function = event_invoke_function
        self._invoke_args = event_invoke_args or []
        self._invoke_kwargs = event_invoke_kwargs or {}
        if event_type is not None:
            self.event_type = event_type

    def create_content(self):
        if self.content is not None:
            return self.content

        event = {"request": self.request, "response": self.execution.response}
        self.content = json.dumps(event, default=str, ensure_ascii=False)
        return self.content

    def to_log(self, event_type: str | None = None, hash_content: bool = False) -> Log:
        if self.content is None:
            self.create_content()

        # Create a Log object with keyword arguments
        log = Log(
            id=str(self.id),
            created_at=self.created_at.isoformat(),
            updated_at=self.updated_at.isoformat(),
            event_type=event_type or self.__class__.__name__,
            content=self.content,
            embedding=self.embedding,
            duration=self.execution.duration,
            status=self.execution.status.value.lower(),  # Ensure status is lowercase
            error=self.execution.error,
        )

        if hash_content:
            from .utils import sha256_of_dict

            log.sha256 = sha256_of_dict({"content": self.content})

        return log


def as_event(
    *,
    request_arg: str | None = None,
    embed_content: bool = False,
    embed_function: Callable[..., Embedding] | None = None,
    adapt: bool = False,
    adapter: type[AsyncAdapter] | None = None,
    event_type: str | None = None,
    **kw,
):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Event:
            request_obj = kwargs.get(request_arg) if request_arg else None
            if len(args) > 2 and hasattr(args[0], "__class__"):
                args = args[1:]
            request_obj = args[0] if request_obj is None else request_obj
            event = Event(func, list(args), kwargs, event_type=event_type)
            event.request = validate_model_to_dict(request_obj)
            await event.invoke()
            if embed_content and embed_function is not None:
                async_embed = as_async_fn(embed_function)
                event.embedding = await async_embed(event.content)

            if adapt and adapter is not None:
                await adapter.to_obj(event.to_log(event_type=event_type), **kw)

            return event

        return wrapper

    return decorator
