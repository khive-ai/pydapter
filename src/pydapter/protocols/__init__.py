from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Type checking imports
    from typing_extensions import Protocol, runtime_checkable
    from .identifiable import Identifiable
    from .temporal import Temporal
    from .embedable import Embedable
    from .invokable import Invokable
    from .event import Event, EventHandler
    from .types import Embedding, ExecutionStatus, Execution, Log
else:
    try:
        # Runtime imports
        from typing_extensions import Protocol, runtime_checkable
        from .identifiable import Identifiable
        from .temporal import Temporal
        from .embedable import Embedable
        from .invokable import Invokable
        from .event import Event, EventHandler
        from .types import Embedding, ExecutionStatus, Execution, Log
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
    "EventHandler",
    "Embedding",
    "ExecutionStatus",
    "Execution",
    "Log"
]