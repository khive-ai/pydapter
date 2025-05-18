import orjson as json
from pydantic import BaseModel, Field, field_validator

from .types import Embedding


class Embedable(BaseModel):
    """Embedable trait, contains embedding and content"""

    content: str | None = None
    embedding: Embedding = Field(default_factory=list)

    @property
    def n_dim(self) -> int:
        """Get the number of dimensions of the embedding."""
        return len(self.embedding)

    @field_validator("embedding", mode="before")
    def _parse_embedding(cls, value: list[float] | str | None) -> Embedding | None:
        if value is None:
            return []
        if isinstance(value, str):
            try:
                loaded = json.loads(value)
                return [float(x) for x in loaded]
            except Exception as e:
                raise ValueError("Invalid embedding string.") from e
        if isinstance(value, list):
            try:
                return [float(x) for x in value]
            except Exception as e:
                raise ValueError("Invalid embedding list.") from e
        raise ValueError("Invalid embedding type; must be list or JSON-encoded string.")

    def create_content(self):
        """override in child class to support custom content creation"""
        return self.content


def _parse_embedding_response(x):
    # parse openai response
    if (
        isinstance(x, BaseModel)
        and hasattr(x, "data")
        and len(x.data) > 0
        and hasattr(x.data[0], "embedding")
    ):
        return x.data[0].embedding

    if isinstance(x, list | tuple):
        if len(x) > 0 and all(isinstance(i, float) for i in x):
            return x
        if len(x) == 1 and isinstance(x[0], dict | BaseModel):
            return _parse_embedding_response(x[0])

    # parse dict response
    if isinstance(x, dict):
        # parse openai format response

        if "data" in x:
            data = x.get("data")
            if data is not None and len(data) > 0 and isinstance(data[0], dict):
                return _parse_embedding_response(data[0])

        # parse {"embedding": []} response
        if "embedding" in x:
            return _parse_embedding_response(x["embedding"])

    return x
