from __future__ import annotations

import sys
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager
from enum import StrEnum
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated, Literal, Self, cast
from uuid import uuid4

from anyio import TemporaryDirectory as AsyncTemporaryDirectory
from asyncer import asyncify
from datamodel_code_generator import (
    DataModelType,
    InputFileType,
    PythonVersion,
    generate,
)
from pydantic import BaseModel, Field, model_validator


class Type(StrEnum):
    # Primitive types
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    # Advanced types
    OBJECT = "object"
    ARRAY = "array"


class _BaseSchema(BaseModel):
    description: Annotated[str, Field(min_length=1)]


class String(_BaseSchema):
    """
    Pydantic model representing a JSON Schema string.
    """

    type: Annotated[Literal[Type.STRING], Field(default=Type.STRING)]


class Enum(String):
    """
    Pydantic model representing a JSON Schema enum, based on the string type.
    """

    enum: Annotated[set[str], Field(min_length=1)]


class Number(_BaseSchema):
    """
    Pydantic model representing a JSON Schema number.
    """

    type: Annotated[Literal[Type.NUMBER], Field(default=Type.NUMBER)]


class Integer(_BaseSchema):
    """
    Pydantic model representing a JSON Schema integer.
    """

    type: Annotated[Literal[Type.INTEGER], Field(default=Type.INTEGER)]


class Boolean(_BaseSchema):
    """
    Pydantic model representing a JSON Schema boolean.
    """

    type: Annotated[Literal[Type.BOOLEAN], Field(default=Type.BOOLEAN)]


class Object(_BaseSchema):
    """
    Pydantic model representing a JSON Schema object.
    """

    type: Annotated[Literal[Type.OBJECT], Field(default=Type.OBJECT)]
    properties: dict[
        str,
        String | Number | Integer | Boolean | Enum | Object | Array,
    ]
    required: set[str]

    @model_validator(mode="after")
    def check_required_keys_exist(self) -> Self:
        if not self.required.issubset(self.properties.keys()):
            raise ValueError(
                f"Required keys must be a subset of keys defined in properties. Required keys are {[*self.required]}; property keys are {[*self.properties.keys()]}"
            )
        return self


class Array(_BaseSchema):
    """
    Pydantic model representing a JSON Schema array.
    """

    type: Annotated[Literal[Type.ARRAY], Field(default=Type.ARRAY)]
    items: String | Number | Integer | Boolean | Enum | Object | Array


@contextmanager
def convert_json_schema_to_pydantic_model(
    object: Object, *, target_python_version: PythonVersion
) -> Generator[type[BaseModel]]:
    """
    Converts a JSON schema object into its Pydantic representation. This is useful while building language model-based applications which accept an arbitrary JSON representing the user's desired output structure.

    See corresponding tests in the `tests` directory for example usage.

    Args:
        object (Object): The JSON Schema object to convert. This should be an instance of the custom `Object` Pydantic model defined in this module, typically constructed to describe the desired schema for your data.
        target_python_version (PythonVersion): The Python version to target for the generated Pydantic model source code. Use values from `datamodel_code_generator.PythonVersion` (such as `PythonVersion.PY_311`) according to your environment.

    Returns:
        Generator[type[BaseModel]]: A context manager with the created Pydantic representation.
    """
    json_schema = object.model_dump_json(by_alias=True)

    with TemporaryDirectory() as temp_dir:
        # Create temporary destination for generated Python module containing the Pydantic model to generate
        temp_dir_path = Path(temp_dir)
        module_name = f"temp_pydantic_model_{uuid4().hex}"  # UUID to make sure no collision within sys.modules (see below)
        model_file = temp_dir_path / f"{module_name}.py"

        # Generate the Pydantic model from the JSON Schema object
        generate(
            json_schema,
            input_file_type=InputFileType.JsonSchema,
            output=model_file,
            output_model_type=DataModelType.PydanticV2BaseModel,
            target_python_version=target_python_version,
        )

        # Import the generated model
        spec = spec_from_file_location(module_name, model_file)
        if spec is None:  # pragma: no cover
            raise ValueError(
                "Spec for temporary module containing generated Pydantic model should not be None. Re-check how this function converts a JSON Schema to a Pydantic model."
            )
        if spec.loader is None:  # pragma: no cover
            raise ValueError(
                "Spec loader for temporary module containing generated Pydantic model should not be None. Re-check how this function converts a JSON Schema to a Pydantic model."
            )
        module = module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # Return the Pydantic model
        yield cast(type[BaseModel], module.Model)

        # Remove module from system when done. It will be deleted when the tempdir context exits
        sys.modules.pop(module_name)


@asynccontextmanager
async def convert_json_schema_to_pydantic_model_async(
    object: Object, *, target_python_version: PythonVersion
) -> AsyncGenerator[type[BaseModel]]:
    """
    Converts a JSON schema object into its Pydantic representation, async-style. This is useful while building language model-based applications which accept an arbitrary JSON representing the user's desired output structure.

    See corresponding tests in the `tests` directory for example usage.

    Args:
        object (Object): The JSON Schema object to convert. This should be an instance of the custom `Object` Pydantic model defined in this module, typically constructed to describe the desired schema for your data.
        target_python_version (PythonVersion): The Python version to target for the generated Pydantic model source code. Use values from `datamodel_code_generator.PythonVersion` (such as `PythonVersion.PY_311`) according to your environment.

    Returns:
        AsyncGenerator[type[BaseModel]]: An asynchronous context manager with the created Pydantic representation.
    """
    json_schema = object.model_dump_json(by_alias=True)

    async with AsyncTemporaryDirectory() as temp_dir:
        # Create temporary destination for generated Python module containing the Pydantic model to generate
        temp_dir_path = Path(temp_dir)
        module_name = f"temp_pydantic_model_{uuid4().hex}"  # UUID to make sure no collision within sys.modules (see below)
        model_file = temp_dir_path / f"{module_name}.py"

        # Generate the Pydantic model from the JSON Schema object
        await asyncify(generate)(
            json_schema,
            input_file_type=InputFileType.JsonSchema,
            output=model_file,
            output_model_type=DataModelType.PydanticV2BaseModel,
            target_python_version=target_python_version,
        )

        # Import the generated model
        spec = spec_from_file_location(module_name, model_file)
        if spec is None:  # pragma: no cover
            raise ValueError(
                "Spec for temporary module containing generated Pydantic model should not be None. Re-check how this function converts a JSON Schema to a Pydantic model."
            )
        if spec.loader is None:  # pragma: no cover
            raise ValueError(
                "Spec loader for temporary module containing generated Pydantic model should not be None. Re-check how this function converts a JSON Schema to a Pydantic model."
            )
        module = module_from_spec(spec)
        sys.modules[module_name] = module
        await asyncify(spec.loader.exec_module)(module)

        # Return the Pydantic model
        yield cast(type[BaseModel], module.Model)

        # Remove module from system when done. It will be deleted when the tempdir context exits
        sys.modules.pop(module_name)
