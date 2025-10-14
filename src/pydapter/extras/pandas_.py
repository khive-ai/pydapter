"""
DataFrame & Series adapters (require `pandas`).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

import pandas as pd
from pydantic import BaseModel, ValidationError

from ..core import Adapter, AdapterBase, dispatch_adapt_meth
from ..exceptions import PydapterError, ResourceError
from ..exceptions import ValidationError as AdapterValidationError

T = TypeVar("T", bound=BaseModel)


class DataFrameAdapter(AdapterBase, Adapter[T]):
    """
    Adapter for converting between Pydantic models and pandas DataFrames.

    This adapter handles pandas DataFrame objects, providing methods to:
    - Convert DataFrame rows to Pydantic model instances
    - Convert Pydantic models to DataFrame rows
    - Handle both single records and multiple records

    Attributes:
        adapter_key: The key identifier for this adapter type ("pd.DataFrame")
        obj_key: Legacy key identifier (for backward compatibility)

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

    adapter_key = "pd.DataFrame"
    obj_key = "pd.DataFrame"  # Backward compatibility

    # -------- Helper Methods --------

    @classmethod
    def _validate_dataframe_structure(
        cls, df: pd.DataFrame, many: bool, required_columns: list[str] | None = None
    ) -> None:
        """
        Validate DataFrame structure before processing.

        Args:
            df: DataFrame to validate
            many: Whether processing multiple or single records
            required_columns: Optional list of required column names

        Raises:
            ResourceError: If DataFrame is empty when many=False
            AdapterValidationError: If DataFrame has missing required columns
        """
        try:
            # Check for empty DataFrame
            if df.empty:
                if many:
                    # Empty DataFrame is acceptable for many=True (returns empty list)
                    return
                # Empty DataFrame with many=False is an error
                raise ResourceError(
                    "Cannot convert empty DataFrame to single model instance (many=False)",
                    resource="DataFrame",
                )

            # Validate required columns if specified
            if required_columns:
                missing_cols = set(required_columns) - set(df.columns)
                if missing_cols:
                    raise AdapterValidationError(
                        f"DataFrame is missing required columns: {sorted(missing_cols)}",
                        data={"columns": list(df.columns), "required": required_columns},
                    )

        except (ResourceError, AdapterValidationError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Safety net for unexpected errors
            cls._handle_error(e, "validation", data={"columns": list(df.columns)})

    @classmethod
    def _convert_dataframe_to_records(cls, df: pd.DataFrame, many: bool) -> list[dict] | dict:
        """
        Convert DataFrame to dictionary records with error handling.

        Args:
            df: DataFrame to convert
            many: Whether to return all records or just the first

        Returns:
            List of dictionaries if many=True, single dictionary if many=False

        Raises:
            AdapterValidationError: If conversion fails
        """
        try:
            if many:
                return df.to_dict(orient="records")
            return df.iloc[0].to_dict()
        except IndexError as e:
            # This should not happen due to _validate_dataframe_structure, but safety net
            cls._handle_error(
                e,
                "resource",
                resource="DataFrame",
                message="Cannot access first row of empty DataFrame",
            )
        except Exception as e:
            cls._handle_error(e, "validation", data={"shape": df.shape})

    @classmethod
    def _validate_and_convert_models(
        cls,
        subj_cls: type[T],
        records: list[dict] | dict,
        many: bool,
        adapt_meth: str | Callable,
        adapt_kw: dict | None,
        validation_errors: tuple[type[Exception], ...],
    ) -> T | list[T]:
        """
        Convert dictionary records to model instances with validation.

        Args:
            subj_cls: Target model class
            records: Dictionary records to convert
            many: Whether processing multiple or single records
            adapt_meth: Adaptation method name or callable
            adapt_kw: Keyword arguments for adaptation method
            validation_errors: Tuple of expected validation error types

        Returns:
            Single model instance or list of model instances

        Raises:
            AdapterValidationError: If validation fails
        """
        try:
            if many:
                return [dispatch_adapt_meth(adapt_meth, r, adapt_kw, subj_cls) for r in records]
            return dispatch_adapt_meth(adapt_meth, records, adapt_kw, subj_cls)
        except validation_errors as e:
            cls._handle_error(
                e,
                "validation",
                data=records[0] if many and isinstance(records, list) else records,
                errors=e.errors() if hasattr(e, "errors") else None,
            )

    @classmethod
    def _models_to_dataframe(
        cls,
        items: list[T],
        adapt_meth: str | Callable,
        adapt_kw: dict | None,
        **kw,
    ) -> pd.DataFrame:
        """
        Convert model instances to DataFrame with error handling.

        Args:
            items: List of model instances
            adapt_meth: Adaptation method name or callable
            adapt_kw: Keyword arguments for adaptation method
            **kw: Additional keyword arguments for DataFrame constructor

        Returns:
            pandas DataFrame

        Raises:
            AdapterValidationError: If conversion fails
        """
        try:
            records = [dispatch_adapt_meth(adapt_meth, i, adapt_kw, type(i)) for i in items]
            return pd.DataFrame(records, **kw)
        except Exception as e:
            cls._handle_error(e, "validation", data={"item_count": len(items)})

    # -------- Protocol Methods --------

    @classmethod
    def from_obj(
        cls,
        subj_cls: type[T],
        obj: pd.DataFrame,
        /,
        *,
        many: bool = True,
        adapt_meth: str | Callable = "model_validate",
        adapt_kw: dict | None = None,
        validation_errors: tuple[type[Exception], ...] = (ValidationError,),
        required_columns: list[str] | None = None,
        **kw: Any,
    ) -> T | list[T]:
        """
        Convert DataFrame to Pydantic model instances.

        Args:
            subj_cls: The Pydantic model class to instantiate
            obj: The pandas DataFrame to convert
            many: If True, convert all rows; if False, convert only first row
            adapt_meth: Method name or callable to use for adaptation
            adapt_kw: Keyword arguments for adaptation method
            validation_errors: Tuple of expected validation error types
            required_columns: Optional list of required column names to validate
            **kw: Additional arguments (currently unused)

        Returns:
            List of model instances if many=True, single instance if many=False

        Raises:
            ResourceError: If DataFrame is empty when many=False
            AdapterValidationError: If DataFrame has missing required columns or validation fails
        """
        try:
            # Validate DataFrame structure
            cls._validate_dataframe_structure(obj, many, required_columns)

            # Handle empty DataFrame with many=True
            if obj.empty and many:
                return []

            # Convert DataFrame to dictionary records
            records = cls._convert_dataframe_to_records(obj, many)

            # Convert records to model instances
            return cls._validate_and_convert_models(
                subj_cls, records, many, adapt_meth, adapt_kw, validation_errors
            )

        except PydapterError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Safety net for unexpected errors
            cls._handle_error(e, "validation", unexpected=True)

    @classmethod
    def to_obj(
        cls,
        subj: T | list[T],
        /,
        *,
        many: bool = True,
        adapt_meth: str | Callable = "model_dump",
        adapt_kw: dict | None = None,
        **kw: Any,
    ) -> pd.DataFrame:
        """
        Convert Pydantic model instances to pandas DataFrame.

        Args:
            subj: Single model instance or list of instances
            many: If True, handle as multiple instances
            adapt_meth: Method name or callable to use for adaptation
            adapt_kw: Keyword arguments for adaptation method
            **kw: Additional arguments passed to DataFrame constructor

        Returns:
            pandas DataFrame with model data

        Raises:
            AdapterValidationError: If conversion fails
        """
        try:
            # Normalize to list
            items = subj if isinstance(subj, list) else [subj]

            # Convert models to DataFrame using helper
            return cls._models_to_dataframe(items, adapt_meth, adapt_kw, **kw)

        except PydapterError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Safety net for unexpected errors
            cls._handle_error(e, "validation", unexpected=True)


class SeriesAdapter(AdapterBase, Adapter[T]):
    """
    Adapter for converting between Pydantic models and pandas Series.

    This adapter handles pandas Series objects, providing methods to:
    - Convert Series to a single Pydantic model instance
    - Convert Pydantic model to Series
    - Only supports single records (many=False)

    Attributes:
        adapter_key: The key identifier for this adapter type ("pd.Series")
        obj_key: Legacy key identifier (for backward compatibility)

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

    adapter_key = "pd.Series"
    obj_key = "pd.Series"  # Backward compatibility

    @classmethod
    def from_obj(
        cls,
        subj_cls: type[T],
        obj: pd.Series,
        /,
        *,
        many: bool = False,
        adapt_meth: str | Callable = "model_validate",
        adapt_kw: dict | None = None,
        validation_errors: tuple[type[Exception], ...] = (ValidationError,),
        **kw: Any,
    ) -> T:
        """
        Convert pandas Series to Pydantic model instance.

        Args:
            subj_cls: The Pydantic model class to instantiate
            obj: The pandas Series to convert
            many: Must be False (Series only supports single records)
            adapt_meth: Method name or callable to use for adaptation
            adapt_kw: Keyword arguments for adaptation method
            validation_errors: Tuple of expected validation error types
            **kw: Additional arguments passed to the Series.to_dict() method

        Returns:
            Single model instance

        Raises:
            AdapterValidationError: If many=True is specified or validation fails
        """
        try:
            if many:
                raise AdapterValidationError(
                    "SeriesAdapter supports single records only (many=False)"
                )

            # Convert Series to dict and create model using dispatch_adapt_meth
            data = obj.to_dict(**kw)
            return dispatch_adapt_meth(adapt_meth, data, adapt_kw or {}, subj_cls)

        except validation_errors as e:
            cls._handle_error(
                e,
                "validation",
                data=data if "data" in locals() else None,
                errors=e.errors() if hasattr(e, "errors") else None,
            )
        except PydapterError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Safety net for unexpected errors
            cls._handle_error(e, "validation", unexpected=True)

    @classmethod
    def to_obj(
        cls,
        subj: T | list[T],
        /,
        *,
        many: bool = False,
        adapt_meth: str | Callable = "model_dump",
        adapt_kw: dict | None = None,
        **kw: Any,
    ) -> pd.Series:
        """
        Convert Pydantic model instance to pandas Series.

        Args:
            subj: Single model instance (list not supported)
            many: Must be False (Series only supports single records)
            adapt_meth: Method name or callable to use for adaptation
            adapt_kw: Keyword arguments for adaptation method
            **kw: Additional arguments passed to Series constructor

        Returns:
            pandas Series with model data

        Raises:
            AdapterValidationError: If many=True is specified or list provided
        """
        try:
            if many or isinstance(subj, list):
                raise AdapterValidationError(
                    "SeriesAdapter supports single records only (many=False)"
                )

            # Convert model to dict using dispatch_adapt_meth and create Series
            data = dispatch_adapt_meth(adapt_meth, subj, adapt_kw or {}, type(subj))
            return pd.Series(data, **kw)

        except PydapterError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Safety net for unexpected errors
            cls._handle_error(e, "validation", unexpected=True)
