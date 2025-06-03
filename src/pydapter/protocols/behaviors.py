"""Standard protocol behaviors with integrated field definitions."""

from datetime import datetime, timezone
from typing import Optional
import uuid

from .core import Protocol
from ..fields.templates import (
    UUIDField,
    StringField,
    IntField,
    DateTimeField,
    BoolField,
    ListField,
    FloatField,
)


class Identifiable(Protocol):
    """Protocol for entities with unique identifiers."""

    __protocol_id__ = "identifiable"
    __required_fields__ = {
        "id": UUIDField(auto_generate=True, metadata={"primary_key": True}),
    }
    __optional_fields__ = {}
    __behaviors__ = ["get_id", "equals_by_id"]

    @staticmethod
    def get_id(obj) -> uuid.UUID:
        """Get the entity's ID."""
        return obj.id

    @staticmethod
    def equals_by_id(obj, other) -> bool:
        """Check equality by ID."""
        if not hasattr(other, "id"):
            return False
        return obj.id == other.id


class Temporal(Protocol):
    """Protocol for entities with creation and update timestamps."""

    __protocol_id__ = "temporal"
    __required_fields__ = {
        "created_at": DateTimeField(
            timezone_aware=True, auto_now_add=True, metadata={"index": True}
        ),
        "updated_at": DateTimeField(
            timezone_aware=True, auto_now=True, metadata={"index": True}
        ),
    }
    __optional_fields__ = {}
    __behaviors__ = ["touch", "age", "was_modified"]

    @staticmethod
    def touch(obj) -> None:
        """Update the updated_at timestamp."""
        obj.updated_at = datetime.now(timezone.utc)

    @staticmethod
    def age(obj) -> float:
        """Get age in seconds since creation."""
        now = datetime.now(timezone.utc)
        return (now - obj.created_at).total_seconds()

    @staticmethod
    def was_modified(obj) -> bool:
        """Check if entity was modified after creation."""
        return obj.updated_at > obj.created_at


class Auditable(Protocol):
    """Protocol for entities that track who created/modified them."""

    __protocol_id__ = "auditable"
    __required_fields__ = {}
    __optional_fields__ = {
        "created_by": StringField(required=False),
        "updated_by": StringField(required=False),
        "created_by_id": UUIDField(required=False),
        "updated_by_id": UUIDField(required=False),
    }
    __behaviors__ = ["set_created_by", "set_updated_by", "get_audit_info"]

    @staticmethod
    def set_created_by(obj, user_id: str, user_name: Optional[str] = None) -> None:
        """Set created by information."""
        if hasattr(obj, "created_by_id"):
            obj.created_by_id = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        if user_name and hasattr(obj, "created_by"):
            obj.created_by = user_name

    @staticmethod
    def set_updated_by(obj, user_id: str, user_name: Optional[str] = None) -> None:
        """Set updated by information."""
        if hasattr(obj, "updated_by_id"):
            obj.updated_by_id = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        if user_name and hasattr(obj, "updated_by"):
            obj.updated_by = user_name

        # Also update timestamp if temporal
        if hasattr(obj, "touch"):
            obj.touch()

    @staticmethod
    def get_audit_info(obj) -> dict:
        """Get audit information."""
        info = {}
        for field in ["created_by", "updated_by", "created_by_id", "updated_by_id"]:
            if hasattr(obj, field):
                info[field] = getattr(obj, field)
        return info


class Versionable(Protocol):
    """Protocol for entities with version tracking."""

    __protocol_id__ = "versionable"
    __required_fields__ = {
        "version": IntField(default=1, min_value=1),
    }
    __optional_fields__ = {}
    __behaviors__ = ["increment_version", "check_version"]

    @staticmethod
    def increment_version(obj) -> None:
        """Increment the version number."""
        obj.version += 1
        
        # Update timestamp if temporal
        if hasattr(obj, "touch"):
            obj.touch()

    @staticmethod
    def check_version(obj, expected_version: int) -> bool:
        """Check if version matches expected."""
        return obj.version == expected_version


class SoftDeletable(Protocol):
    """Protocol for entities that support soft deletion."""

    __protocol_id__ = "soft_deletable"
    __required_fields__ = {}
    __optional_fields__ = {
        "deleted_at": DateTimeField(
            timezone_aware=True, required=False, metadata={"index": True}
        ),
        "is_deleted": BoolField(default=False, metadata={"index": True}),
        "deleted_by": StringField(required=False),
    }
    __behaviors__ = ["soft_delete", "restore", "is_active"]

    @staticmethod
    def soft_delete(obj, deleted_by: Optional[str] = None) -> None:
        """Mark entity as deleted."""
        obj.deleted_at = datetime.now(timezone.utc)
        obj.is_deleted = True
        if deleted_by and hasattr(obj, "deleted_by"):
            obj.deleted_by = deleted_by

    @staticmethod
    def restore(obj) -> None:
        """Restore soft-deleted entity."""
        obj.deleted_at = None
        obj.is_deleted = False
        if hasattr(obj, "deleted_by"):
            obj.deleted_by = None

    @staticmethod
    def is_active(obj) -> bool:
        """Check if entity is active (not deleted)."""
        return not getattr(obj, "is_deleted", False)


class Taggable(Protocol):
    """Protocol for entities that can be tagged."""

    __protocol_id__ = "taggable"
    __required_fields__ = {}
    __optional_fields__ = {
        "tags": ListField(item_type=str, default=list, metadata={"index": True}),
    }
    __behaviors__ = ["add_tag", "remove_tag", "has_tag", "clear_tags", "get_tags"]

    @staticmethod
    def add_tag(obj, tag: str) -> None:
        """Add a tag."""
        if tag not in obj.tags:
            obj.tags.append(tag)

    @staticmethod
    def remove_tag(obj, tag: str) -> None:
        """Remove a tag."""
        if tag in obj.tags:
            obj.tags.remove(tag)

    @staticmethod
    def has_tag(obj, tag: str) -> bool:
        """Check if entity has a tag."""
        return tag in obj.tags

    @staticmethod
    def clear_tags(obj) -> None:
        """Clear all tags."""
        obj.tags.clear()

    @staticmethod
    def get_tags(obj) -> list:
        """Get all tags."""
        return obj.tags.copy()


class Searchable(Protocol):
    """Protocol for entities that support search."""

    __protocol_id__ = "searchable"
    __required_fields__ = {}
    __optional_fields__ = {
        "search_text": StringField(
            required=False, metadata={"fulltext_index": True}
        ),
        "search_keywords": ListField(
            item_type=str, default=list, metadata={"index": True}
        ),
        "search_score": FloatField(required=False, min_value=0.0, max_value=1.0),
    }
    __behaviors__ = ["update_search_text", "add_keyword", "calculate_relevance"]

    @staticmethod
    def update_search_text(obj, *fields: str) -> None:
        """Update search text from specified fields."""
        parts = []
        for field in fields:
            if hasattr(obj, field):
                value = getattr(obj, field)
                if value:
                    parts.append(str(value))
        obj.search_text = " ".join(parts)

    @staticmethod
    def add_keyword(obj, keyword: str) -> None:
        """Add a search keyword."""
        if keyword not in obj.search_keywords:
            obj.search_keywords.append(keyword)

    @staticmethod
    def calculate_relevance(obj, query: str) -> float:
        """Calculate relevance score for a query."""
        query_lower = query.lower()
        text_lower = (obj.search_text or "").lower()

        if query_lower in text_lower:
            return 1.0

        # Check keywords
        for keyword in obj.search_keywords:
            if query_lower in keyword.lower():
                return 0.8

        return 0.0