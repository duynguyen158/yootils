import os
from functools import partial
from typing import Any

import pytest
from datamodel_code_generator import PythonVersion
from pydantic import ValidationError

from yootils.jsonschema.pydantic_utils import (
    Array,
    Boolean,
    Enum,
    Integer,
    Number,
    Object,
    String,
    convert_json_schema_to_pydantic_model,
    convert_json_schema_to_pydantic_model_async,
)

PartialObject = partial(Object, description="This is an object.")
PartialString = partial(String, description="This is a string.")
PartialNumber = partial(Number, description="This is a number.")
PartialInteger = partial(Integer, description="This is an integer.")
PartialBoolean = partial(Boolean, description="This is a boolean.")
PartialArray = partial(Array, description="This is an array.")
PartialEnum = partial(Enum, description="This is an enum.")

CONVERSION_TEST_PARAMETERS = (
    "object,validation_data",
    [
        # String (required)
        (
            PartialObject(
                properties={"exampleString": PartialString()},
                required={"exampleString"},
            ),
            [
                ({"exampleString": "foo"}, None),
                ({"exampleString": None}, ValidationError),
                ({"exampleString": 3}, ValidationError),
            ],
        ),
        # String (optional)
        (
            PartialObject(
                properties={"exampleString": PartialString()}, required=set()
            ),
            [({"exampleString": None}, None)],
        ),
        # String (enum)
        (
            PartialObject(
                properties={"exampleString": PartialEnum(enum={"foo", "bar"})},
                required={"exampleString"},
            ),
            [
                ({"exampleString": "foo"}, None),
                ({"exampleString": "bar"}, None),
                ({"exampleString": "baz"}, ValidationError),
                ({"exampleString": None}, ValidationError),
            ],
        ),
        # Number (required)
        (
            PartialObject(
                properties={"exampleNumber": PartialNumber()},
                required={"exampleNumber"},
            ),
            [
                ({"exampleNumber": 3}, None),
                ({"exampleNumber": 3.5}, None),
                ({"exampleNumber": None}, ValidationError),
                ({"exampleNumber": "foo"}, ValidationError),
            ],
        ),
        # Number (optional)
        (
            PartialObject(
                properties={"exampleNumber": PartialNumber()}, required=set()
            ),
            [({"exampleNumber": None}, None)],
        ),
        # Integer (required)
        (
            PartialObject(
                properties={"exampleInteger": PartialInteger()},
                required={"exampleInteger"},
            ),
            [
                ({"exampleInteger": 3}, None),
                ({"exampleInteger": 3.5}, ValidationError),
                ({"exampleInteger": None}, ValidationError),
                ({"exampleInteger": "foo"}, ValidationError),
            ],
        ),
        # Integer (optional)
        (
            PartialObject(
                properties={"exampleInteger": PartialInteger()}, required=set()
            ),
            [({"exampleInteger": None}, None)],
        ),
        # Boolean (required)
        (
            PartialObject(
                properties={"exampleBoolean": PartialBoolean()},
                required={"exampleBoolean"},
            ),
            [
                ({"exampleBoolean": True}, None),
                ({"exampleBoolean": None}, ValidationError),
                ({"exampleBoolean": "foo"}, ValidationError),
            ],
        ),
        # Boolean (optional)
        (
            PartialObject(
                properties={"exampleBoolean": PartialBoolean()}, required=set()
            ),
            [({"exampleBoolean": None}, None)],
        ),
        # Array (required)
        (
            PartialObject(
                properties={"exampleArray": PartialArray(items=PartialString())},
                required={"exampleArray"},
            ),
            [
                ({"exampleArray": ["foo", "bar"]}, None),
                ({"exampleArray": [2, "bar"]}, ValidationError),
                ({"exampleArray": None}, ValidationError),
                ({"exampleArray": "foo"}, ValidationError),
            ],
        ),
        # Array (optional)
        (
            PartialObject(
                properties={"exampleArray": PartialArray(items=PartialString())},
                required=set(),
            ),
            [
                ({"exampleArray": ["foo", "bar"]}, None),
                ({"exampleArray": [2, "bar"]}, ValidationError),
                ({"exampleArray": None}, None),
                ({"exampleArray": "foo"}, ValidationError),
            ],
        ),
        # Nested array
        (
            PartialObject(
                properties={
                    "exampleArray": PartialArray(
                        items=PartialArray(items=PartialString())
                    )
                },
                required=set(),
            ),
            [
                ({"exampleArray": [["foo", "bar"], ["baz", "qux"]]}, None),
                ({"exampleArray": [[2, "bar"], ["baz", "qux"]]}, ValidationError),
                ({"exampleArray": None}, None),
                ({"exampleArray": "foo"}, ValidationError),
            ],
        ),
        # Object within array
        (
            PartialObject(
                properties={
                    "exampleArray": PartialArray(
                        items=PartialObject(
                            properties={"foo": PartialString()}, required={"foo"}
                        )
                    )
                },
                required=set(),
            ),
            [
                ({"exampleArray": [{"foo": "bar"}, {"foo": "baz"}]}, None),
                ({"exampleArray": [{"foo": "bar"}, {"foo": 42}]}, ValidationError),
                ({"exampleArray": None}, None),
                ({"exampleArray": "foo"}, ValidationError),
            ],
        ),
        # Nested object
        (
            PartialObject(
                properties={
                    "exampleObject": PartialObject(
                        properties={
                            "exampleString": PartialString(),
                            "exampleInteger": PartialInteger(),
                        },
                        required={"exampleString", "exampleInteger"},
                    )
                },
                required={"exampleObject"},
            ),
            [
                (
                    {"exampleObject": {"exampleString": "foo", "exampleInteger": 42}},
                    None,
                ),
                (
                    {"exampleObject": {"exampleString": None, "exampleInteger": 42}},
                    ValidationError,
                ),
                (
                    {"exampleObject": {"exampleString": "foo", "exampleInteger": None}},
                    ValidationError,
                ),
                (
                    {"exampleObject": {"exampleString": None, "exampleInteger": None}},
                    ValidationError,
                ),
            ],
        ),
    ],
)


@pytest.fixture(scope="module")
def target_python_version() -> PythonVersion:
    return PythonVersion(os.environ["PYTHON_MAJOR_MINOR_VERSION"])


class TestEnum:
    def test_reject_empty_enum(self) -> None:
        with pytest.raises(ValidationError):
            PartialEnum(enum=set())


class TestObject:
    def test_reject_nonexistent_required_keys(self) -> None:
        with pytest.raises(
            ValueError,
            match="Required keys must be a subset of keys defined in properties",
        ):
            PartialObject(properties={"foo": PartialString()}, required={"bar"})


@pytest.mark.parametrize(*CONVERSION_TEST_PARAMETERS)
def test_convert_json_schema_to_pydantic_model(
    object: Object,
    target_python_version: PythonVersion,
    validation_data: list[tuple[dict[str, Any], type[Exception] | None]],
) -> None:
    with convert_json_schema_to_pydantic_model(
        object, target_python_version=target_python_version
    ) as model:
        for data, exception in validation_data:
            if exception is not None:
                with pytest.raises(exception):
                    model.model_validate(data)
            else:
                model.model_validate(data)


@pytest.mark.parametrize(*CONVERSION_TEST_PARAMETERS)
@pytest.mark.asyncio
async def test_convert_json_schema_to_pydantic_model_async(
    object: Object,
    target_python_version: PythonVersion,
    validation_data: list[tuple[dict[str, Any], type[Exception] | None]],
) -> None:
    async with convert_json_schema_to_pydantic_model_async(
        object, target_python_version=target_python_version
    ) as model:
        for data, exception in validation_data:
            if exception is not None:
                with pytest.raises(exception):
                    model.model_validate(data)
            else:
                model.model_validate(data)
