import typing
from collections import OrderedDict
from collections.abc import Generator, Iterable, Iterator, Mapping, Sequence, Set
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
    "model,exception",
    [
        (
            _Model(
                fieldUnion1=typing.Annotated[
                    int | str | None, Field(description="Union field 1")
                ]
            ),
            ValueError(
                "Pydantic model field type cannot be a union of more than one non-NoneType type; got int | str for field fieldUnion1"
            ),
        ),
        (
            _Model(
                fieldUnion2=typing.Annotated[
                    typing.Union[int, str, None], Field(description="Union field 2")  # noqa: UP007
                ]
            ),
            ValueError(
                r"Pydantic model field type cannot be a union of more than one non-NoneType type; got typing.Union\[int, str, NoneType\] for field fieldUnion2"
            ),
        ),
        (
            _Model(
                fieldList1=typing.Annotated[
                    list, Field(description="List field 1")  # pyright: ignore[reportMissingTypeArgument]
                ]
            ),
            NotImplementedError("Unsupported field type: <class 'list'>"),
        ),
        (
            _Model(
                fieldList2=typing.Annotated[
                    list[int | str], Field(description="List field 2")
                ]
            ),
            ValueError(
                "Pydantic model field type cannot contain a union of more than one non-NoneType type; got int | str for field fieldList2"
            ),
        ),
        (
            _Model(
                fieldDecimal1=typing.Annotated[
                    Decimal, Field(description="Decimal field 1", max_digits=78)
                ]
            ),
            ValueError(
                "Precision and scale values are out of range. Maximum precision possible for Decimal is 76 and maximum scale is 38. Got precision=78 and scale=0"
            ),
        ),
        (
            _Model(
                fieldDecimal2=typing.Annotated[
                    Decimal, Field(description="Decimal field 2", decimal_places=39)
                ]
            ),
            ValueError(
                "Precision and scale values are out of range. Maximum precision possible for Decimal is 76 and maximum scale is 38. Got precision=0 and scale=39"
            ),
        ),
        (
            _Model(
                fieldUnsupported=typing.Annotated[
                    Exception, Field(description="Unsupported field")
                ]
            ),
            NotImplementedError("Unsupported field type: <class 'Exception'>"),
        ),
    ],
)
def test_convert_pydantic_model_to_schema_failed(
    model: type[BaseModel], exception: Exception
) -> None:
    with pytest.raises(type(exception), match=str(exception)):
        convert_pydantic_model_to_schema(model)


@pytest.mark.parametrize(
    "model,expected",
    [
        # Without annotation
        (
            _Model(fieldBool=(bool, Field(description="Boolean field"))),
            [
                SchemaField(
                    "fieldBool",
                    StandardSqlTypeNames.BOOL,
                    mode=Mode.REQUIRED,
                    description="Boolean field",
                )
            ],
        ),
        # Without description
        (
            _Model(fieldBool=bool),
            [
                SchemaField(
                    "fieldBool",
                    StandardSqlTypeNames.BOOL,
                    mode=Mode.REQUIRED,
                )
            ],
        ),
        # With annotation
        # Multiple fields
        (
            _Model(
                fieldBool=bool,
                fieldInt=typing.Annotated[int, Field(description="Integer field")],
            ),
            [
                SchemaField(
                    "fieldBool",
                    StandardSqlTypeNames.BOOL,
                    mode=Mode.REQUIRED,
                ),
                SchemaField(
                    "fieldInt",
                    StandardSqlTypeNames.INT64,
                    mode=Mode.REQUIRED,
                    description="Integer field",
                ),
            ],
        ),
        # Single type, standard fields
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
                fieldStringEnum=typing.Annotated[
                    Mode, Field(description="String enum field")
                ]
            ),
            [
                SchemaField(
                    "fieldStringEnum",
                    StandardSqlTypeNames.STRING,
                    mode=Mode.REQUIRED,
                    description="String enum field",
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
                fieldDict1=typing.Annotated[
                    dict[str, typing.Any], Field(description="Dictionary field 1")
                ]
            ),
            [
                SchemaField(
                    "fieldDict1",
                    StandardSqlTypeNames.JSON,
                    mode=Mode.REQUIRED,
                    description="Dictionary field 1",
                )
            ],
        ),
        (
            _Model(
                fieldDict2=typing.Annotated[
                    typing.Dict[str, typing.Any],  # noqa: UP006
                    Field(description="Dictionary field 2"),
                ]
            ),
            [
                SchemaField(
                    "fieldDict2",
                    StandardSqlTypeNames.JSON,
                    mode=Mode.REQUIRED,
                    description="Dictionary field 2",
                )
            ],
        ),
        (
            _Model(
                fieldOrderedDict1=typing.Annotated[
                    OrderedDict[str, typing.Any],
                    Field(description="Ordered dictionary field 1"),
                ]
            ),
            [
                SchemaField(
                    "fieldOrderedDict1",
                    StandardSqlTypeNames.JSON,
                    mode=Mode.REQUIRED,
                    description="Ordered dictionary field 1",
                )
            ],
        ),
        (
            _Model(
                fieldOrderedDict2=typing.Annotated[
                    typing.OrderedDict[str, typing.Any],
                    Field(description="Ordered dictionary field 2"),
                ]
            ),
            [
                SchemaField(
                    "fieldOrderedDict2",
                    StandardSqlTypeNames.JSON,
                    mode=Mode.REQUIRED,
                    description="Ordered dictionary field 2",
                )
            ],
        ),
        (
            _Model(
                fieldMapping1=typing.Annotated[
                    Mapping[str, typing.Any], Field(description="Mapping field 1")
                ]
            ),
            [
                SchemaField(
                    "fieldMapping1",
                    StandardSqlTypeNames.JSON,
                    mode=Mode.REQUIRED,
                    description="Mapping field 1",
                )
            ],
        ),
        (
            _Model(
                fieldMapping2=typing.Annotated[
                    typing.Mapping[str, typing.Any],
                    Field(description="Mapping field 2"),
                ]
            ),
            [
                SchemaField(
                    "fieldMapping2",
                    StandardSqlTypeNames.JSON,
                    mode=Mode.REQUIRED,
                    description="Mapping field 2",
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
        (
            _Model(
                fieldTuple2=typing.Annotated[
                    typing.Tuple[str, ...], Field(description="Tuple field 2")  # noqa: UP006
                ]
            ),
            [
                SchemaField(
                    "fieldTuple2",
                    StandardSqlTypeNames.STRING,
                    mode=Mode.REPEATED,
                    description="Tuple field 2",
                )
            ],
        ),
        (
            _Model(
                fieldTuple3=typing.Annotated[
                    tuple[str | None, ...], Field(description="Tuple field 3")
                ]
            ),
            [
                SchemaField(
                    "fieldTuple3",
                    StandardSqlTypeNames.STRING,
                    mode=Mode.REPEATED,
                    description="Tuple field 3",
                )
            ],
        ),
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
                fieldFrozenSet1=typing.Annotated[
                    frozenset[str], Field(description="Frozen set field 1")
                ]
            ),
            [
                SchemaField(
                    "fieldFrozenSet1",
                    StandardSqlTypeNames.STRING,
                    mode=Mode.REPEATED,
                    description="Frozen set field 1",
                )
            ],
        ),
        (
            _Model(
                fieldFrozenSet2=typing.Annotated[
                    typing.FrozenSet[str], Field(description="Frozen set field 2")  # noqa: UP006
                ]
            ),
            [
                SchemaField(
                    "fieldFrozenSet2",
                    StandardSqlTypeNames.STRING,
                    mode=Mode.REPEATED,
                    description="Frozen set field 2",
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
                fieldAbstractSet1=typing.Annotated[
                    typing.AbstractSet[int], Field(description="Abstract set field 1")
                ]
            ),
            [
                SchemaField(
                    "fieldAbstractSet1",
                    StandardSqlTypeNames.INT64,
                    mode=Mode.REPEATED,
                    description="Abstract set field 1",
                )
            ],
        ),
        (
            _Model(
                fieldAbstractSet2=typing.Annotated[
                    Set[int], Field(description="Abstract set field 2")
                ]
            ),
            [
                SchemaField(
                    "fieldAbstractSet2",
                    StandardSqlTypeNames.INT64,
                    mode=Mode.REPEATED,
                    description="Abstract set field 2",
                )
            ],
        ),
    ],
)
def test_convert_pydantic_model_to_schema(
    model: type[BaseModel], expected: list[SchemaField]
) -> None:
    assert convert_pydantic_model_to_schema(model) == expected
