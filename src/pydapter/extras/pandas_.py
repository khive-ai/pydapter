"""
DataFrame & Series adapters (require `pandas`).
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from ..core import Adapter
from ..exceptions import ParseError, ValidationError
from ..utils import T, adapt_dump, adapt_from


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
        cls,
        subj_cls: type[T],
        obj: pd.DataFrame,
        /,
        *,
        many: bool = True,
        adapt_meth: str = "model_validate",
        adapt_kw: dict | None = None,
        **kw: Any,
    ) -> T | list[T]:
        """
        Convert DataFrame to Pydantic model instances.

        Args:
            subj_cls: The Pydantic model class to instantiate
            obj: The pandas DataFrame to convert
            many: If True, convert all rows; if False, convert only first row
            adapt_meth: Method name to call on subj_cls (default: "model_validate")
            **kw: Additional arguments passed to the adaptation method

        Returns:
            List of model instances if many=True, single instance if many=False

        Raises:
            ValidationError: If DataFrame conversion fails
            ParseError: If unexpected errors occur
        """
        try:
            if obj.empty:
                return [] if many else None

            if many:
                return [
                    adapt_from(subj_cls, r, adapt_meth, adapt_kw)
                    for r in obj.to_dict(orient="records")
                ]
            return adapt_from(subj_cls, obj.iloc[0].to_dict(), adapt_meth, adapt_kw)
        except IndexError as e:
            raise ValidationError.from_adapter(
                cls,
                "DataFrame has no rows to convert",
                dataframe_shape=obj.shape,
                cause=e,
            )
        except Exception as e:
            raise ParseError.from_adapter(
                cls,
                "Error converting DataFrame to models",
                dataframe_shape=obj.shape,
                cause=e,
            )

    @classmethod
    def to_obj(
        cls,
        subj: T | list[T],
        /,
        *,
        many: bool = True,
        adapt_meth: str = "model_dump",
        adapt_kw: dict | None = None,
        **kw: Any,
    ) -> pd.DataFrame:
        """
        Convert Pydantic model instances to pandas DataFrame.

        Args:
            subj: Single model instance or list of instances
            many: If True, handle as multiple instances
            adapt_meth: Method name to call on model instances (default: "model_dump")
            **kw: Additional arguments passed to DataFrame constructor

        Returns:
            pandas DataFrame with model data

        Raises:
            ValidationError: If model conversion fails
            ParseError: If DataFrame creation fails
        """
        try:
            items = subj if isinstance(subj, list) else [subj]
            if not items:
                return pd.DataFrame()

            return pd.DataFrame(
                [adapt_dump(i, adapt_meth, adapt_kw) for i in items], **kw
            )
        except Exception as e:
            raise ParseError.from_adapter(
                cls,
                "Error converting models to DataFrame",
                item_count=len(items) if "items" in locals() else 0,
                cause=e,
            )


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
        cls,
        subj_cls: type[T],
        obj: pd.Series,
        /,
        *,
        many: bool = False,
        adapt_meth: str = "model_validate",
        adapt_kw: dict | None = None,
        **kw: Any,
    ) -> T:
        """
        Convert pandas Series to Pydantic model instance.

        Args:
            subj_cls: The Pydantic model class to instantiate
            obj: The pandas Series to convert
            many: Must be False (Series only supports single records)
            adapt_meth: Method name to call on subj_cls (default: "model_validate")
            **kw: Additional arguments passed to the adaptation method

        Returns:
            Single model instance

        Raises:
            ValidationError: If many=True is specified or conversion fails
            ParseError: If unexpected errors occur
        """
        try:
            if many:
                raise ValidationError.from_adapter(
                    cls, "SeriesAdapter supports single records only"
                )

            if obj.empty:
                raise ValidationError.from_adapter(
                    cls, "Cannot convert empty Series to model"
                )

            return adapt_from(subj_cls, obj.to_dict(), adapt_meth, adapt_kw)
        except Exception as e:
            raise ParseError.from_adapter(
                cls, "Error converting Series to model", series_length=len(obj), cause=e
            )

    @classmethod
    def to_obj(
        cls,
        subj: T | list[T],
        /,
        *,
        many: bool = False,
        adapt_meth: str = "model_dump",
        adapt_kw: dict | None = None,
        **kw: Any,
    ) -> pd.Series:
        """
        Convert Pydantic model instance to pandas Series.

        Args:
            subj: Single model instance (not a list)
            many: Must be False (Series only supports single records)
            adapt_meth: Method name to call on model instance (default: "model_dump")
            **kw: Additional arguments passed to Series constructor

        Returns:
            pandas Series with model data

        Raises:
            ValidationError: If many=True or list is provided
            ParseError: If Series creation fails
        """
        try:
            if many or isinstance(subj, list):
                raise ValidationError.from_adapter(
                    cls, "SeriesAdapter supports single records only"
                )

            return pd.Series(adapt_dump(subj, adapt_meth, adapt_kw), **kw)
        except Exception as e:
            raise ParseError.from_adapter(
                cls, "Error converting model to Series", cause=e
            )
