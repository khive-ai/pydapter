"""Core types and lionagi-compatible error interface."""

from __future__ import annotations

import urllib.parse
from typing import Any, ClassVar

__all__ = ("BaseError",)

# URL schemes that may carry embedded credentials.
_CREDENTIAL_SCHEMES = frozenset(
    {
        "postgresql",
        "postgresql+asyncpg",
        "postgresql+psycopg2",
        "postgresql+psycopg",
        "mysql",
        "mysql+pymysql",
        "mysql+aiomysql",
        "mongodb",
        "mongodb+srv",
        "redis",
        "rediss",
        "amqp",
        "amqps",
        "http",
        "https",
        "neo4j",
        "neo4j+s",
        "neo4j+ssc",
        "bolt",
        "bolt+s",
        "bolt+ssc",
    }
)

# Dict keys whose values should never appear in error output.
_SENSITIVE_KEYS = frozenset(
    {
        "password",
        "passwd",
        "token",
        "secret",
        "api_key",
        "apikey",
        "dsn",
        "connection_string",
        "connection_url",
        "database_url",
        "db_url",
        "url",
        "uri",
    }
)

_MAX_DETAIL_LEN = 500


def _redact_url(value: str) -> str:
    """Return *value* with the password component replaced by '***'.

    Uses ``urllib.parse`` so that driver-specific schemes such as
    ``postgresql+asyncpg://`` and ``mongodb+srv://`` are handled correctly
    without fragile regex patterns.
    """
    try:
        parsed = urllib.parse.urlparse(value)
    except Exception:
        return value

    # Only touch schemes that plausibly carry credentials.
    scheme = parsed.scheme.lower()
    if scheme not in _CREDENTIAL_SCHEMES:
        return value

    if parsed.password:
        # Rebuild netloc with password replaced.
        userinfo = parsed.username or ""
        userinfo = f"{userinfo}:***"
        host = parsed.hostname or ""
        netloc = f"{userinfo}@{host}:{parsed.port}" if parsed.port else f"{userinfo}@{host}"
        sanitized = parsed._replace(netloc=netloc)
        return urllib.parse.urlunparse(sanitized)

    return value


def _redact_value(key: str, value: Any) -> Any:
    """Redact *value* when *key* is a known sensitive field name."""
    key_lower = key.lower()
    if key_lower in _SENSITIVE_KEYS:
        if isinstance(value, str):
            return _redact_url(value) if "://" in value else "***"
        if isinstance(value, dict):
            # Redact the entire dict — it may contain nested passwords.
            return dict.fromkeys(value, "***")
        return "***"
    if isinstance(value, str) and "://" in value:
        return _redact_url(value)
    return value


def _redact_details(details: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of *details* with credentials scrubbed.

    Rules applied in order:
    1. Keys in ``_SENSITIVE_KEYS`` → value replaced with ``'***'`` (or a
       URL-sanitised variant when the value looks like a connection string).
    2. Any string value containing ``'://'`` → URL-sanitised.
    3. Values longer than ``_MAX_DETAIL_LEN`` characters → truncated.
    """
    redacted: dict[str, Any] = {}
    for k, v in details.items():
        v = _redact_value(k, v)
        # Truncate excessively long string values to prevent payload leakage.
        if isinstance(v, str) and len(v) > _MAX_DETAIL_LEN:
            v = v[:_MAX_DETAIL_LEN] + "... (truncated)"
        redacted[k] = v
    return redacted


class BaseError(Exception):
    """Lionagi-compatible base error class."""

    default_message: ClassVar[str] = "Error"
    default_status_code: ClassVar[int] = 500
    __slots__ = ("message", "details", "status_code")

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, Any] | None = None,
        status_code: int | None = None,
        cause: Exception | None = None,
    ):
        super().__init__(message or self.default_message)
        if cause:
            self.__cause__ = cause  # preserves traceback
        self.message = message or self.default_message
        self.details = details or {}
        self.status_code = status_code or type(self).default_status_code

    def __str__(self) -> str:
        safe = _redact_details(self.details)
        details_str = ", ".join(f"{k}={v!r}" for k, v in safe.items())
        if details_str:
            return f"{self.message} ({details_str})"
        return self.message

    def __getattr__(self, name: str) -> Any:
        """Allow attribute-style access to details fields."""
        if name == "context":
            # Backward compatibility: context is alias for details
            return self.details
        if name in self.details:
            return self.details[name]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def to_dict(self, *, include_cause: bool = False) -> dict[str, Any]:
        """Serialize to dict for logging/API responses.

        Credential-bearing values are redacted before serialisation so that
        this dict is safe to pass to loggers, API responses, and monitoring
        systems.
        """
        safe_details = _redact_details(self.details)
        data = {
            "error": self.__class__.__name__,
            "message": self.message,
            "status_code": self.status_code,
            **({"details": safe_details} if safe_details else {}),
        }
        if include_cause and (cause := self.get_cause()):
            data["cause"] = repr(cause)
        return data

    def get_cause(self) -> Exception | None:
        """Get __cause__ if any."""
        return self.__cause__ if hasattr(self, "__cause__") else None

    @classmethod
    def from_value(
        cls,
        value: Any,
        *,
        expected: str | None = None,
        message: str | None = None,
        status_code: int | None = None,
        cause: Exception | None = None,
        **extra: Any,
    ):
        """Create error from value with type/expected info in details."""
        details = {
            "value": value,
            "type": type(value).__name__,
            **({"expected": expected} if expected else {}),
            **extra,
        }
        return cls(message=message, details=details, status_code=status_code, cause=cause)
