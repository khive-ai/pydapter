import asyncio
from asyncio.log import logger
from collections.abc import Callable
from typing import Any

from pydantic import Field, PrivateAttr

from .temporal import Temporal
from .types import Execution, ExecutionStatus
from .utils import as_async_fn, validate_model_to_dict


class Invokable(Temporal):
    """An executable can be invoked with a request"""

    request: dict | None = None
    execution: Execution = Field(default_factory=Execution)
    response_obj: Any = Field(None, exclude=True)
    _invoke_function: Callable | None = PrivateAttr(None)
    _invoke_args: list[Any] = PrivateAttr([])
    _invoke_kwargs: dict[str, Any] = PrivateAttr({})

    @property
    def has_invoked(self) -> bool:
        return self.execution.status in [
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
        ]

    async def _invoke(self):
        if self._invoke_function is None:
            raise ValueError("Event invoke function is not set.")
        async_fn = as_async_fn(self._invoke_function)
        return await async_fn(*self._invoke_args, **self._invoke_kwargs)

    async def invoke(self) -> None:
        start = asyncio.get_event_loop().time()
        response = None
        e1 = None

        try:
            # Use the endpoint as a context manager
            response = await self._invoke()

        except asyncio.CancelledError as ce:
            e1 = ce
            logger.warning("invoke() canceled by external request.")
            raise
        except Exception as ex:
            e1 = ex  # type: ignore

        finally:
            self.execution.duration = asyncio.get_event_loop().time() - start
            if response is None and e1 is not None:
                self.execution.error = str(e1)
                self.execution.status = ExecutionStatus.FAILED
                logger.error(f"invoke() failed for event {str(self.id)[:6]}...")
            else:
                self.response_obj = response
                self.execution.response = validate_model_to_dict(response)
                self.execution.status = ExecutionStatus.COMPLETED
            self.update_timestamp()
