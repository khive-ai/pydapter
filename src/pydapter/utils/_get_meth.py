from typing import Any, TypeVar

T = TypeVar("T")  # Universal type - works with any Python class


def adapt_from(
    subj_cls: type, data: Any, adapt_meth: str, adapt_kw: dict | None
) -> Any:
    meth = getattr(subj_cls, adapt_meth, None)
    if meth is None:
        raise AttributeError(
            f"Method '{adapt_meth}' not found on class {str(subj_cls)}"
        )
    return meth(data, **adapt_kw) if adapt_kw else meth(data)


def adapt_dump(obj: Any, adapt_meth: str, adapt_kw: dict | None) -> dict:
    meth = getattr(obj, adapt_meth, None)
    if meth is None:
        obj_cls = type(obj)
        raise AttributeError(
            f"Method '{adapt_meth}' not found on object of type {str(obj_cls)}"
        )
    return meth(**adapt_kw) if adapt_kw else meth()


def truncate_for_display(
    obj: Any, max_length: int = 100, placeholder: str = "..."
) -> str:
    """
    Safely truncate an object's string representation for error messages.

    Args:
        obj: Any object to display
        max_length: Maximum string length (default 100)
        placeholder: String to append when truncated (default "...")

    Returns:
        Truncated string representation safe for error messages
    """
    if obj is None:
        return "None"

    # Convert to string, handling different types
    if isinstance(obj, bytes):
        try:
            text = obj.decode("utf-8", errors="replace")
        except:
            text = repr(obj)
    elif isinstance(obj, (str, int, float, bool)):
        text = str(obj)
    else:
        # For Path, dicts, lists, etc.
        text = repr(obj)

    # Truncate if needed
    if len(text) <= max_length:
        return text

    # Calculate how much text we can show before adding placeholder
    available = max_length - len(placeholder)
    if available <= 0:
        return placeholder

    return text[:available] + placeholder
