from collections.abc import Iterable, Mapping
from datetime import date, datetime, time
from decimal import Decimal
from enum import StrEnum
from functools import partial, reduce
from types import NoneType, UnionType
from typing import Union, cast, get_args, get_origin

from annotated_types import MaxLen
from google.cloud.bigquery import SchemaField, StandardSqlTypeNames
from google.cloud.bigquery.schema import (
    _DEFAULT_VALUE,  # pyright: ignore[reportPrivateUsage]
)
from pydantic import BaseModel
from pydantic._internal._fields import PydanticMetadata


class Mode(StrEnum):
    REQUIRED = "REQUIRED"
    NULLABLE = "NULLABLE"
    REPEATED = "REPEATED"


def convert_pydantic_model_to_schema(model: type[BaseModel]) -> list[SchemaField]:
    """
    Converts a Pydantic model representing a row in a BigQuery table to a list of SchemaField objects. Feature parity is not guaranteed, so use with caution.

    Args:
        model (BaseModel): The Pydantic model to convert.

    Returns:
        list[SchemaField]: A list of SchemaField objects representing the fields of the model, ready to be used in a BigQuery table.
    """
    schema: list[SchemaField] = []

    for field_name, field in model.model_fields.items():
        field_type = field.annotation
        mode: Mode = Mode.REQUIRED

        if (
            field_type is None
        ):  # pragma: no cover # Remove pragma: no cover once seeing this error in the wild
            raise NotImplementedError(
                f"Pydantic model field type of None is not supported. Got None for field {field_name}. Typically this should never be reached; if you're the developer of this library, please add a test case!"
            )

        # Try to strip None from union type and set mode to NULLABLE if None is indeed present
        if get_origin(field_type) in {UnionType, Union}:
            # Can use set here because X | int | int, for example, is the same as X | int
            union_type_args = set(get_args(field_type))
            if NoneType in union_type_args:
                mode = Mode.NULLABLE
            match list(union_type_args - {NoneType}):
                case [main_type]:
                    # Reassign field_type to be, e.g., X from X | None after setting mode to NULLABLE
                    field_type = main_type
                case _:
                    raise ValueError(
                        f"Pydantic model field type cannot be a union of more than one non-NoneType type; got {field_type} for field {field_name}"
                    )

        origin = get_origin(field_type)
        # Try to strip field type from list, set, or Iterable and set mode to REPEATED
        # Use __mro__ so that if the type is a subclass of Iterable, e.g., Generator, it's still counted. Except for Mapping, which should be treated as a struct type instead of REPEATED
        if (
            origin is not None
            and set(origin.__mro__).intersection(
                {tuple, list, set, frozenset, Iterable}
            )
            and not issubclass(origin, Mapping)
        ):
            mode = Mode.REPEATED
            # Use list here instead of set because Generator[int, None, int] is not the same as Generator[int]
            iterable_type_args = list(get_args(field_type))
            # Reassign field_type to be, e.g., X from list[X] after setting mode to REPEATED
            # iterable_type_args[0] will always exist, since if the type annotation is list instead of list[X], origin would be none, this code block would be skipped, and we'll go straight to  NotImplementedError: Unsupported field type: <class 'list'>. Even better, this usually would be caught by any half-decent IDE
            field_type = iterable_type_args[0]
            # Check if inside is a Union type with None. If so, strip None from it, same as above
            if get_origin(field_type) in {UnionType, Union}:
                union_type_args = set(get_args(field_type))
                match list(union_type_args - {NoneType}):
                    case [main_type]:
                        field_type = main_type
                    case _:
                        raise ValueError(
                            f"Pydantic model field type cannot contain a union of more than one non-NoneType type; got {field_type} for field {field_name}"
                        )

        _SchemaField = partial(
            SchemaField,
            name=field_name,
            description=field.description or _DEFAULT_VALUE,
            mode=mode,
        )

        field_metadata = field.metadata
        field_pydantic_metadata = reduce(
            lambda acc, obj: {**acc, **obj.__dict__},
            [obj for obj in field_metadata if isinstance(obj, PydanticMetadata)],
            dict(),
        )

        # Get origin again
        origin = get_origin(field_type)

        # Infer BigQuery field type from field_type and origin
        if origin is not None and issubclass(origin, dict | Mapping):
            field_schema = _SchemaField(field_type=StandardSqlTypeNames.JSON)

        elif issubclass(field_type, BaseModel):
            # Recursively convert the inner model to schema for the struct field
            field_schema = _SchemaField(
                field_type=StandardSqlTypeNames.STRUCT,
                fields=convert_pydantic_model_to_schema(field_type),
            )

        elif issubclass(field_type, bool):
            field_schema = _SchemaField(field_type=StandardSqlTypeNames.BOOL)

        elif issubclass(field_type, int):
            field_schema = _SchemaField(field_type=StandardSqlTypeNames.INT64)

        elif issubclass(field_type, float):
            field_schema = _SchemaField(field_type=StandardSqlTypeNames.FLOAT64)

        elif issubclass(field_type, Decimal):
            precision = cast(int, field_pydantic_metadata.get("max_digits", 0))
            scale = cast(int, field_pydantic_metadata.get("decimal_places", 0))
            if precision <= 38 and scale <= 9:
                field_schema = _SchemaField(
                    field_type=StandardSqlTypeNames.NUMERIC,
                    precision=precision,
                    scale=scale,
                )
            elif precision <= 76 and scale <= 38:
                field_schema = _SchemaField(
                    field_type=StandardSqlTypeNames.BIGNUMERIC,
                    precision=precision,
                    scale=scale,
                )
            else:
                raise ValueError(
                    f"Precision and scale values are out of range. Maximum precision possible for Decimal is 76 and maximum scale is 38. Got precision={precision} and scale={scale}"
                )

        elif issubclass(field_type, str):
            max_length = _DEFAULT_VALUE
            for metadata in field_metadata:
                if isinstance(metadata, MaxLen):
                    max_length = metadata.max_length
            field_schema = _SchemaField(
                field_type=StandardSqlTypeNames.STRING, max_length=max_length
            )

        elif issubclass(field_type, bytes):
            field_schema = _SchemaField(field_type=StandardSqlTypeNames.BYTES)

        elif issubclass(field_type, datetime):
            field_schema = _SchemaField(field_type=StandardSqlTypeNames.TIMESTAMP)

        elif issubclass(field_type, date):
            field_schema = _SchemaField(field_type=StandardSqlTypeNames.DATE)

        elif issubclass(field_type, time):
            field_schema = _SchemaField(field_type=StandardSqlTypeNames.TIME)

        else:
            raise NotImplementedError(f"Unsupported field type: {field_type}")

        schema.append(field_schema)

    return schema
