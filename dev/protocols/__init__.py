import warnings

warnings.warn(
    "Importing from dev.protocols is deprecated and will be removed in a future version. "
    "Please use pydapter.protocols instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export from new location
try:
    from pydapter.protocols import *
except ImportError:
    # If the new module isn't available, fall back to local implementation
    from .embedable import Embedable
    from .event import Event, EventHandler
    from .identifiable import Identifiable
    from .invokable import Invokable
    from .temporal import Temporal
    from .types import Embedding, Execution, ExecutionStatus, Log

    __all__ = [
        "Identifiable",
        "Temporal",
        "Embedable",
        "Invokable",
        "Event",
        "EventHandler",
        "Embedding",
        "ExecutionStatus",
        "Execution",
        "Log",
    ]
