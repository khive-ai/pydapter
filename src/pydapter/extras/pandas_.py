"""
DataFrame & Series adapters (require `pandas`).
"""

from __future__ import annotations

from typing import Any, TypeVar

import pandas as pd
from pydantic import BaseModel

from ..core import Adapter

T = TypeVar("T", bound=BaseModel)


class DataFrameAdapter(Adapter[T]):
    """
    Adapter for converting between Pydantic models and pandas DataFrames.

    This adapter handles pandas DataFrame objects, providing methods to:
    - Convert DataFrame rows to Pydantic model instances
    - Convert Pydantic models to DataFrame rows
    - Handle both single records and multiple records

    Attributes:
        obj_key: The key identifier for this adapter type ("pd.DataFrame")

    Example:
        ```python
        import pandas as pd
        from pydantic import BaseModel
        from pydapter.extras.pandas_ import DataFrameAdapter

        class Person(BaseModel):
            name: str
            age: int

        # Create DataFrame
        df = pd.DataFrame([
            {"name": "John", "age": 30},
            {"name": "Jane", "age": 25}
        ])

        # Convert to Pydantic models
        people = DataFrameAdapter.from_obj(Person, df, many=True)

        # Convert back to DataFrame
        df_output = DataFrameAdapter.to_obj(people, many=True)
        ```
    """

    obj_key = "pd.DataFrame"

    @classmethod
    def from_obj(
        cls, subj_cls: type[T], obj: pd.DataFrame, /, *, many: bool = True, **kw: Any
    ) -> T | list[T]:
        """
        Convert DataFrame to Pydantic model instances.

        Args:
            subj_cls: The Pydantic model class to instantiate
            obj: The pandas DataFrame to convert
            many: If True, convert all rows; if False, convert only first row
            **kw: Additional arguments passed to model_validate

        Returns:
            List of model instances if many=True, single instance if many=False
        """
        if many:
            return [subj_cls.model_validate(r) for r in obj.to_dict(orient="records")]
        return subj_cls.model_validate(obj.iloc[0].to_dict(), **kw)

    @classmethod
    def to_obj(
        cls, subj: T | list[T], /, *, many: bool = True, **kw: Any
    ) -> pd.DataFrame:
        """
        Convert Pydantic model instances to pandas DataFrame.

        Args:
            subj: Single model instance or list of instances
            many: If True, handle as multiple instances
            **kw: Additional arguments passed to DataFrame constructor

        Returns:
            pandas DataFrame with model data
        """
        items = subj if isinstance(subj, list) else [subj]
        return pd.DataFrame([i.model_dump() for i in items], **kw)


class SeriesAdapter(Adapter[T]):
    """
    Adapter for converting between Pydantic models and pandas Series.

    This adapter handles pandas Series objects, providing methods to:
    - Convert Series to a single Pydantic model instance
    - Convert Pydantic model to Series
    - Only supports single records (many=False)

    Attributes:
        obj_key: The key identifier for this adapter type ("pd.Series")

    Example:
        ```python
        import pandas as pd
        from pydantic import BaseModel
        from pydapter.extras.pandas_ import SeriesAdapter

        class Person(BaseModel):
            name: str
            age: int

        # Create Series
        series = pd.Series({"name": "John", "age": 30})

        # Convert to Pydantic model
        person = SeriesAdapter.from_obj(Person, series)

        # Convert back to Series
        series_output = SeriesAdapter.to_obj(person)
        ```
    """

    obj_key = "pd.Series"

    @classmethod
    def from_obj(
        cls, subj_cls: type[T], obj: pd.Series, /, *, many: bool = False, **kw: Any
    ) -> T:
        """
        Convert pandas Series to Pydantic model instance.

        Args:
            subj_cls: The Pydantic model class to instantiate
            obj: The pandas Series to convert
            many: Must be False (Series only supports single records)
            **kw: Additional arguments passed to model_validate

        Returns:
            Single model instance

        Raises:
            ValueError: If many=True is specified
        """
        if many:
            raise ValueError("SeriesAdapter supports single records only.")
        return subj_cls.model_validate(obj.to_dict(), **kw)

    @classmethod
    def to_obj(
        cls, subj: T | list[T], /, *, many: bool = False, **kw: Any
    ) -> pd.Series:
        if many or isinstance(subj, list):
            raise ValueError("SeriesAdapter supports single records only.")
        return pd.Series(subj.model_dump(), **kw)
