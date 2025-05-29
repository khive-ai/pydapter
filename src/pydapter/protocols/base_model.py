from pydantic import BaseModel, ConfigDict


# Export configured BaseModel for tests and direct use
class BasePydapterModel(BaseModel):
    """Base model with standard configuration"""

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        extra="forbid",
    )
