from pydantic import BaseModel, ConfigDict, field_serializer
from datetime import datetime
from typing import Any
from uuid import UUID

# Export configured BaseModel for tests and direct use
class BasePydapterModel(BaseModel):
    """Base model with standard configuration"""

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        extra="forbid",
    )
