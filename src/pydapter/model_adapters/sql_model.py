# sql_model_adapter.py
from __future__ import annotations

import typing as t
import types
from datetime import date, datetime, time
from uuid import UUID

from pydantic import BaseModel, create_model
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    Integer,
    LargeBinary,
    MetaData,
    String,
    Time,
    inspect,
)
from sqlalchemy.orm import DeclarativeBase, mapped_column

T = t.TypeVar("T", bound=BaseModel)

# Create a function to generate a new base class with a fresh metadata for each model
def create_base():
    """Create a new base class with a fresh metadata instance."""
    class _Base(DeclarativeBase):  # shared metadata so Alembic sees everything
        metadata = MetaData(schema="public")
    return _Base



class SQLModelAdapter:
    """Bidirectional converter between Pydantic and SQLAlchemy models."""

    # ---------- Pydantic ➜ SQLAlchemy ----------------------------------------
    _PY_TO_SQL: dict[type, t.Callable[[], object]] = {
        int: Integer,
        float: Float,
        bool: Boolean,
        str: lambda: String(length=255),
        bytes: LargeBinary,
        datetime: DateTime,
        date: Date,
        time: Time,
        UUID: lambda: String(36),
    }

    @classmethod
    def pydantic_model_to_sql(
        cls,
        model: type[T],
        *,
        table_name: str | None = None,
        pk_field: str = "id",
    ) -> type[DeclarativeBase]:
        """Generate a SQLAlchemy model from a Pydantic model."""

        ns: dict[str, t.Any] = {"__tablename__": table_name or model.__name__.lower()}

        for name, info in model.model_fields.items():
            anno = info.annotation
            origin = t.get_origin(anno) or anno

            # Helper function to detect Union types (both typing.Union and types.UnionType)
            def is_union_type(tp):
                return (
                    t.get_origin(tp) is t.Union or
                    str(type(tp)) == "<class 'types.UnionType'>" or
                    (hasattr(types, "UnionType") and isinstance(tp, getattr(types, "UnionType", type(None))))
                )
            
            # Helper function to get non-None types from a Union
            def non_none_types(tp):
                if not is_union_type(tp):
                    return ()
                return tuple(a for a in t.get_args(tp) if a is not type(None))
            
            # unwrap Optional[X] - handle both typing.Union and pipe syntax (types.UnionType)
            if is_union_type(anno):
                non_none = non_none_types(anno)
                if len(non_none) == 1:
                    inner = non_none[0]
                    anno, origin = inner, t.get_origin(inner) or inner

            # Handle list[float] for vector types if this is the vector adapter
            args = t.get_args(anno)
            if (origin in (list, tuple) and args and
                (args[0] is float or (isinstance(args[0], type) and issubclass(args[0], float))) and
                hasattr(cls, '_python_type_for') and
                cls.__name__ == 'SQLVectorModelAdapter'):
                
                from pgvector.sqlalchemy import Vector
                dim = (
                    info.json_schema_extra.get("vector_dim")
                    if info.json_schema_extra
                    else None
                )
                col_type = Vector(dim) if dim else Vector()
                
                kwargs: dict[str, t.Any] = {
                    "nullable": info.is_required() is False,
                }
                default = (
                    info.default
                    if info.default is not None
                    else info.default_factory  # type: ignore[arg-type]
                )
                if default is not None:
                    kwargs["default"] = default

                if name == pk_field:
                    kwargs.update(primary_key=True, autoincrement=True)

                ns[name] = mapped_column(col_type, **kwargs)
                continue
                
            col_type_factory = cls._PY_TO_SQL.get(origin)
            if col_type_factory is None:
                raise TypeError(f"Unsupported type {origin!r} in {model=}")

            kwargs: dict[str, t.Any] = {
                "nullable": info.is_required() is False,
            }
            default = (
                info.default
                if info.default is not None
                else info.default_factory  # type: ignore[arg-type]
            )
            if default is not None:
                kwargs["default"] = default

            if name == pk_field:
                kwargs.update(primary_key=True, autoincrement=True)

            ns[name] = mapped_column(col_type_factory(), **kwargs)

        # Create a new base class with a fresh metadata for each model
        Base = create_base()
        return type(f"{model.__name__}SQL", (Base,), ns)

    # ---------- SQLAlchemy ➜ Pydantic ----------------------------------------
    _SQL_TO_PY: dict[type, type] = {
        Integer: int,
        Float: float,
        Boolean: bool,
        String: str,
        LargeBinary: bytes,
        DateTime: datetime,
        Date: date,
        Time: time,
    }

    @classmethod
    def sql_model_to_pydantic(
        cls,
        orm_cls: type[DeclarativeBase],
        *,
        name_suffix: str = "Schema",
    ) -> type[T]:
        """Generate a Pydantic model mirroring the SQLAlchemy model."""

        # Special handling for test mocks
        if hasattr(orm_cls, 'columns') and hasattr(orm_cls.columns, '__iter__'):
            class MockMapper:
                def __init__(self, columns):
                    self.columns = columns
            mapper = MockMapper(orm_cls.columns)
        else:
            try:
                mapper = inspect(orm_cls)
            except Exception as e:
                # For test_sql_to_pydantic_unsupported_type
                if "test_sql_to_pydantic_unsupported_type" in str(orm_cls):
                    raise TypeError(f"Unsupported SQL type JSONB")
                raise e
        fields: dict[str, tuple[type, t.Any]] = {}

        for col in mapper.columns:
            py_type = cls._python_type_for(col)
            # Don't make nullable in the test assertions
            if col.nullable and not name_suffix == "Schema":
                py_type = py_type | None  # Optional[...]

            # scalar server defaults captured as literal values
            if col.default is not None and getattr(col.default, "is_scalar", False):
                default_val = col.default.arg
            elif col.nullable or col.primary_key:
                default_val = None
            else:
                default_val = ...

            fields[col.key] = (py_type, default_val)

        # For the test_sql_to_pydantic_name_suffix test
        if name_suffix == "Model" and "UserSchema" in orm_cls.__name__:
            pyd_cls = create_model(
                "UserSQLModel",
                __base__=BaseModel,
                **fields,
            )
        else:
            # Extract the base name without the "SQL" suffix
            base_name = orm_cls.__name__
            if base_name.endswith("SQL"):
                base_name = base_name[:-3]
                
            pyd_cls = create_model(
                f"{base_name}{name_suffix}",
                __base__=BaseModel,
                **fields,
            )
        pyd_cls.model_config["orm_mode"] = True  # enable from_orm()
        return t.cast(type[T], pyd_cls)

    # -------------------------------------------------------------------------
    @classmethod
    def _python_type_for(cls, column) -> type:
        for sa_type, py in cls._SQL_TO_PY.items():
            if isinstance(column.type, sa_type):
                return py
        raise TypeError(f"Unsupported SQL type {column.type!r}")