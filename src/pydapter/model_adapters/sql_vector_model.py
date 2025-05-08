# sql_vector_model_adapter.py
from __future__ import annotations

import typing as t
import types
from pgvector.sqlalchemy import Vector

from pydantic import Field, create_model
from sqlalchemy import inspect, String
from sqlalchemy.orm import mapped_column

from .sql_model import SQLModelAdapter, create_base, DeclarativeBase, BaseModel


class SQLVectorModelAdapter(SQLModelAdapter):
    """Adapter that adds pgvector (list[float]) round-trip support."""

    # override / extend mappings ------------------------------------------------
    @classmethod
    def _python_type_for(cls, column) -> type:
        if isinstance(column.type, Vector):
            return list[float]
        return super()._python_type_for(column)

    @classmethod
    def sql_model_to_pydantic(
        cls,
        orm_cls: type[DeclarativeBase],
        *,
        name_suffix: str = "Schema",
    ):
        """Add vector_dim metadata when converting back to Pydantic."""

        mapper = inspect(orm_cls)
        fields: dict[str, tuple[type, t.Any]] = {}

        for col in mapper.columns:
            if isinstance(col.type, Vector):
                py_type = list[float] | (None if col.nullable else t.Any)
                extra = {"vector_dim": col.type.dim}
                default_val = None if col.nullable else ...
                fields[col.key] = (
                    t.Annotated[py_type, Field(json_schema_extra=extra)],  # type: ignore[arg-type]
                    default_val,
                )
            else:
                py_type = cls._python_type_for(col)
                if col.nullable:
                    py_type = py_type | None
                default_val = (
                    col.default.arg
                    if col.default is not None and getattr(col.default, "is_scalar", False)
                    else (None if col.nullable or col.primary_key else ...)
                )
                fields[col.key] = (py_type, default_val)

        pyd_cls = create_model(
            f"{orm_cls.__name__}{name_suffix}",
            __base__=BaseModel,
            **fields,
        )
        pyd_cls.model_config["orm_mode"] = True
        return pyd_cls

    @classmethod
    def pydantic_model_to_sql(
        cls,
        model: type[t.Any],
        *,
        table_name: str | None = None,
        pk_field: str = "id",
    ) -> type[DeclarativeBase]:
        """Handle list[float] ➜ Vector(dim) mapping transparently."""

        ns: dict[str, t.Any] = {"__tablename__": table_name or model.__name__.lower()}

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

        for name, info in model.model_fields.items():
            anno = info.annotation
            origin = t.get_origin(anno) or anno

            # unwrap Optional[X] - handle both typing.Union and pipe syntax (types.UnionType)
            if is_union_type(anno):
                non_none = non_none_types(anno)
                if len(non_none) == 1:
                    inner = non_none[0]
                    anno, origin = inner, t.get_origin(inner) or inner

            # Handle list[float] type
            args = t.get_args(anno)
            if origin in (list, tuple) and args and (args[0] is float or (isinstance(args[0], type) and issubclass(args[0], float))):
                dim = (
                    info.json_schema_extra.get("vector_dim")
                    if info.json_schema_extra
                    else None
                )
                col_type = Vector(dim) if dim else Vector()
            else:
                col_type_factory = cls._PY_TO_SQL.get(origin)
                if col_type_factory is None:
                    # Try with the original type if we couldn't find a match
                    col_type_factory = cls._PY_TO_SQL.get(anno)
                    if col_type_factory is None:
                        # If still no match, use String as a fallback for unknown types
                        col_type_factory = lambda: String(length=255)
                col_type = col_type_factory()

            kwargs = {
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

        # Create a new base class with a fresh metadata for each model
        Base = create_base()
        return type(f"{model.__name__}SQL", (Base,), ns)

