from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Type checking imports
    from typing import runtime_checkable

    from typing_extensions import Protocol

    from .embedable import Embedable
    from .event import Event
    from .identifiable import Identifiable
    from .invokable import Invokable
    from .temporal import Temporal
    from .types import Embedding, Execution, ExecutionStatus, Log
else:
    try:
        # Runtime imports
        from typing import runtime_checkable

        from typing_extensions import Protocol

        from .embedable import Embedable
        from .event import Event
        from .identifiable import Identifiable
        from .invokable import Invokable
        from .temporal import Temporal
        from .types import Embedding, Execution, ExecutionStatus, Log
    except ImportError:
        # Import error handling - define stub classes
        from ..utils.dependencies import check_protocols_dependencies

        def __getattr__(name):
            check_protocols_dependencies()
            raise ImportError(f"Cannot import {name} because dependencies are missing")


__all__ = [
    "Protocol",
    "runtime_checkable",
    "Identifiable",
    "Temporal",
    "Embedable",
    "Invokable",
    "Event",
    "Embedding",
    "ExecutionStatus",
    "Execution",
    "Log",
]
