# Create protocol mixin classes
class AuditableMixin:
    """Mixin for audit functionality"""

    def mark_updated_by(self, user_id: str):
        """Mark entity as updated by user"""
        self.updated_by = user_id
        self.version += 1
        if hasattr(self, "update_timestamp"):
            self.update_timestamp()
