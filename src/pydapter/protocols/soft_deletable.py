from datetime import datetime, timezone


class SoftDeletableMixin:
    """Mixin for soft delete functionality"""

    def soft_delete(self):
        """Mark entity as deleted"""
        self.deleted_at = datetime.now(timezone.utc)
        self.is_deleted = True

    def restore(self):
        """Restore soft-deleted entity"""
        self.deleted_at = None
        self.is_deleted = False
