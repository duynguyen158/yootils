import typing
from collections.abc import Generator, Iterable, Iterator, Mapping, Sequence
from datetime import date, datetime, time
from decimal import Decimal
from functools import partial

import pytest
from google.cloud.bigquery import SchemaField, StandardSqlTypeNames
from pydantic import BaseModel, ConfigDict, Field, create_model

from yootils.google.bigquery.convert_pydantic_model_to_schema import (
    Mode,
    convert_pydantic_model_to_schema,
)

_Model = partial(
    create_model, "Model", __config__=ConfigDict(arbitrary_types_allowed=True)
)


@pytest.mark.parametrize(
    "model,expected",
    [
        # Standard fields
        (
            _Model(
                fieldBool=typing.Annotated[bool, Field(description="Boolean field")]
            ),
            [
                SchemaField(
                    "fieldBool",
                    StandardSqlTypeNames.BOOL,
                    mode=Mode.REQUIRED,
                    description="Boolean field",
                )
            ],
        ),
        (
            _Model(fieldInt=typing.Annotated[int, Field(description="Integer field")]),
            [
                SchemaField(
                    "fieldInt",
                    StandardSqlTypeNames.INT64,
                    mode=Mode.REQUIRED,
                    description="Integer field",
                )
            ],
        ),
        (
            _Model(
                fieldFloat=typing.Annotated[float, Field(description="Float field")]
            ),
            [
                SchemaField(
                    "fieldFloat",
                    StandardSqlTypeNames.FLOAT64,
                    mode=Mode.REQUIRED,
                    description="Float field",
                )
            ],
        ),
        (
            _Model(
                fieldDecimalDefault=typing.Annotated[
                    Decimal, Field(description="Default decimal field")
                ]
            ),
            [
                SchemaField(
                    "fieldDecimalDefault",
                    StandardSqlTypeNames.NUMERIC,
                    mode=Mode.REQUIRED,
                    description="Default decimal field",
                    precision=0,
                    scale=0,
                )
            ],
        ),
        (
            _Model(
                fieldDecimalSmall=typing.Annotated[
                    Decimal,
                    Field(
                        description="Small decimal field",
                        max_digits=38,
                        decimal_places=9,
                    ),
                ]
            ),
            [
                SchemaField(
                    "fieldDecimalSmall",
                    StandardSqlTypeNames.NUMERIC,
                    mode=Mode.REQUIRED,
                    description="Small decimal field",
                    precision=38,
                    scale=9,
                )
            ],
        ),
        (
            _Model(
                fieldDecimalLarge=typing.Annotated[
                    Decimal,
                    Field(
                        description="Large decimal field",
                        max_digits=76,
                        decimal_places=38,
                    ),
                ]
            ),
            [
                SchemaField(
                    "fieldDecimalLarge",
                    StandardSqlTypeNames.BIGNUMERIC,
                    mode=Mode.REQUIRED,
                    description="Large decimal field",
                    precision=76,
                    scale=38,
                )
            ],
        ),
        (
            _Model(
                fieldString=typing.Annotated[str, Field(description="String field")]
            ),
            [
                SchemaField(
                    "fieldString",
                    StandardSqlTypeNames.STRING,
                    mode=Mode.REQUIRED,
                    description="String field",
                )
            ],
        ),
        (
            _Model(
                fieldStringLimited=typing.Annotated[
                    str, Field(description="String field with limit", max_length=100)
                ]
            ),
            [
                SchemaField(
                    "fieldStringLimited",
                    StandardSqlTypeNames.STRING,
                    mode=Mode.REQUIRED,
                    description="String field with limit",
                    max_length=100,
                )
            ],
        ),
        (
            _Model(
                fieldBytes=typing.Annotated[bytes, Field(description="Bytes field")]
            ),
            [
                SchemaField(
                    "fieldBytes",
                    StandardSqlTypeNames.BYTES,
                    mode=Mode.REQUIRED,
                    description="Bytes field",
                )
            ],
        ),
        (
            _Model(
                fieldDateTime=typing.Annotated[
                    datetime, Field(description="DateTime field")
                ]
            ),
            [
                SchemaField(
                    "fieldDateTime",
                    StandardSqlTypeNames.TIMESTAMP,
                    mode=Mode.REQUIRED,
                    description="DateTime field",
                )
            ],
        ),
        (
            _Model(fieldDate=typing.Annotated[date, Field(description="Date field")]),
            [
                SchemaField(
                    "fieldDate",
                    StandardSqlTypeNames.DATE,
                    mode=Mode.REQUIRED,
                    description="Date field",
                )
            ],
        ),
        (
            _Model(fieldTime=typing.Annotated[time, Field(description="Time field")]),
            [
                SchemaField(
                    "fieldTime",
                    StandardSqlTypeNames.TIME,
                    mode=Mode.REQUIRED,
                    description="Time field",
                )
            ],
        ),
        (
            _Model(
                fieldDict=typing.Annotated[
                    dict[str, typing.Any], Field(description="Dictionary field")
                ]
            ),
            [
                SchemaField(
                    "fieldDict",
                    StandardSqlTypeNames.JSON,
                    mode=Mode.REQUIRED,
                    description="Dictionary field",
                )
            ],
        ),
        (
            _Model(
                fieldMapping=typing.Annotated[
                    Mapping[str, typing.Any], Field(description="Mapping field")
                ]
            ),
            [
                SchemaField(
                    "fieldMapping",
                    StandardSqlTypeNames.JSON,
                    mode=Mode.REQUIRED,
                    description="Mapping field",
                )
            ],
        ),
        (
            _Model(
                fieldNested=typing.Annotated[
                    create_model(
                        "InnerModel",
                        innerFieldString=(
                            typing.Annotated[
                                str, Field(description="Inner string field")
                            ],
                            ...,
                        ),
                    ),
                    Field(description="Nested model field"),
                ]
            ),
            [
                SchemaField(
                    "fieldNested",
                    StandardSqlTypeNames.STRUCT,
                    mode=Mode.REQUIRED,
                    description="Nested model field",
                    fields=[
                        SchemaField(
                            "innerFieldString",
                            StandardSqlTypeNames.STRING,
                            mode=Mode.REQUIRED,
                            description="Inner string field",
                        ),
                    ],
                )
            ],
        ),
        # Optional fields
        (
            _Model(
                fieldOptional1=typing.Annotated[
                    int | None, Field(description="Optional field 1")
                ]
            ),
            [
                SchemaField(
                    "fieldOptional1",
                    StandardSqlTypeNames.INT64,
                    mode=Mode.NULLABLE,
                    description="Optional field 1",
                )
            ],
        ),
        (
            _Model(
                fieldOptional2=typing.Annotated[
                    typing.Union[int, None], Field(description="Optional field 2")  # noqa: UP007
                ]
            ),
            [
                SchemaField(
                    "fieldOptional2",
                    StandardSqlTypeNames.INT64,
                    mode=Mode.NULLABLE,
                    description="Optional field 2",
                )
            ],
        ),
        (
            _Model(
                fieldOptional3=typing.Annotated[
                    typing.Optional[int], Field(description="Optional field 3")  # noqa: UP007
                ]
            ),
            [
                SchemaField(
                    "fieldOptional3",
                    StandardSqlTypeNames.INT64,
                    mode=Mode.NULLABLE,
                    description="Optional field 3",
                )
            ],
        ),
        # Repeated fields
        (
            _Model(
                fieldList1=typing.Annotated[
                    list[str], Field(description="List field 1")
                ]
            ),
            [
                SchemaField(
                    "fieldList1",
                    StandardSqlTypeNames.STRING,
                    mode=Mode.REPEATED,
                    description="List field 1",
                )
            ],
        ),
        (
            _Model(
                fieldList2=typing.Annotated[
                    typing.List[int], Field(description="List field 2")  # noqa: UP006
                ]
            ),
            [
                SchemaField(
                    "fieldList2",
                    StandardSqlTypeNames.INT64,
                    mode=Mode.REPEATED,
                    description="List field 2",
                )
            ],
        ),
        (
            _Model(
                fieldSet1=typing.Annotated[set[str], Field(description="Set field 1")]
            ),
            [
                SchemaField(
                    "fieldSet1",
                    StandardSqlTypeNames.STRING,
                    mode=Mode.REPEATED,
                    description="Set field 1",
                )
            ],
        ),
        (
            _Model(
                fieldSet2=typing.Annotated[
                    typing.Set[int], Field(description="Set field 2")  # noqa: UP006
                ]
            ),
            [
                SchemaField(
                    "fieldSet2",
                    StandardSqlTypeNames.INT64,
                    mode=Mode.REPEATED,
                    description="Set field 2",
                )
            ],
        ),
        (
            _Model(
                fieldIterable1=typing.Annotated[
                    Iterable[str], Field(description="Iterable field 1")
                ]
            ),
            [
                SchemaField(
                    "fieldIterable1",
                    StandardSqlTypeNames.STRING,
                    mode=Mode.REPEATED,
                    description="Iterable field 1",
                )
            ],
        ),
        (
            _Model(
                fieldIterable2=typing.Annotated[
                    typing.Iterable[int], Field(description="Iterable field 2")
                ]
            ),
            [
                SchemaField(
                    "fieldIterable2",
                    StandardSqlTypeNames.INT64,
                    mode=Mode.REPEATED,
                    description="Iterable field 2",
                )
            ],
        ),
        (
            _Model(
                fieldIterator1=typing.Annotated[
                    Iterator[int], Field(description="Iterator field 1")
                ]
            ),
            [
                SchemaField(
                    "fieldIterator1",
                    StandardSqlTypeNames.INT64,
                    mode=Mode.REPEATED,
                    description="Iterator field 1",
                )
            ],
        ),
        (
            _Model(
                fieldIterator2=typing.Annotated[
                    typing.Iterator[int], Field(description="Iterator field 2")
                ]
            ),
            [
                SchemaField(
                    "fieldIterator2",
                    StandardSqlTypeNames.INT64,
                    mode=Mode.REPEATED,
                    description="Iterator field 2",
                )
            ],
        ),
        (
            _Model(
                fieldGenerator1=typing.Annotated[
                    Generator[int], Field(description="Generator field 1")
                ]
            ),
            [
                SchemaField(
                    "fieldGenerator1",
                    StandardSqlTypeNames.INT64,
                    mode=Mode.REPEATED,
                    description="Generator field 1",
                )
            ],
        ),
        (
            _Model(
                fieldGenerator2=typing.Annotated[
                    Generator[int, None, None], Field(description="Generator field 2")
                ]
            ),
            [
                SchemaField(
                    "fieldGenerator2",
                    StandardSqlTypeNames.INT64,
                    mode=Mode.REPEATED,
                    description="Generator field 2",
                )
            ],
        ),
        (
            _Model(
                fieldGenerator3=typing.Annotated[
                    typing.Generator[int, None, None],
                    Field(description="Generator field 3"),
                ]
            ),
            [
                SchemaField(
                    "fieldGenerator3",
                    StandardSqlTypeNames.INT64,
                    mode=Mode.REPEATED,
                    description="Generator field 3",
                )
            ],
        ),
        (
            _Model(
                fieldSequence1=typing.Annotated[
                    Sequence[int], Field(description="Sequence field 1")
                ]
            ),
            [
                SchemaField(
                    "fieldSequence1",
                    StandardSqlTypeNames.INT64,
                    mode=Mode.REPEATED,
                    description="Sequence field 1",
                )
            ],
        ),
        (
            _Model(
                fieldSequence2=typing.Annotated[
                    typing.Sequence[int], Field(description="Sequence field 2")
                ]
            ),
            [
                SchemaField(
                    "fieldSequence2",
                    StandardSqlTypeNames.INT64,
                    mode=Mode.REPEATED,
                    description="Sequence field 2",
                )
            ],
        ),
        (
            _Model(
                fieldTuple1=typing.Annotated[
                    tuple[str, ...], Field(description="Tuple field 1")
                ]
            ),
            [
                SchemaField(
                    "fieldTuple1",
                    StandardSqlTypeNames.STRING,
                    mode=Mode.REPEATED,
                    description="Tuple field 1",
                )
            ],
        ),
    ],
)
def test_convert_pydantic_model_to_schema(
    model: type[BaseModel], expected: list[SchemaField]
) -> None:
    assert convert_pydantic_model_to_schema(model) == expected
