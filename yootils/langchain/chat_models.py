from collections.abc import Mapping, Sequence
from typing import Annotated, Any, Literal, TypeVar, cast, overload

from langchain.chat_models import init_chat_model
from langchain_community.callbacks.openai_info import (
    OpenAICallbackHandler,  # works with Google models, too
)
from langchain_core.callbacks.base import BaseCallbackManager
from langchain_core.language_models import LanguageModelInput
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableConfig
from pydantic import BaseModel, Field

_O = TypeVar("_O", bound=BaseModel)


class Output(BaseModel):
    content: Annotated[str, Field(description="Your response")]


class NoResult(Exception):
    pass


@overload
async def invoke_chat_model(
    model_id: str,
    prompt: str
    | Sequence[tuple[Literal["system", "human", "ai"], str | list[dict[str, str]]]]
    | ChatPromptTemplate,
    *,
    model_provider: str | None = None,
    configurable_fields: Literal["any"] | list[str] | tuple[str, ...] | None = None,
    config_prefix: str | None = None,
    model_kwargs: Mapping[str, Any] = dict(),
    output_structure: type[_O] = Output,
    output_structure_kwargs: Mapping[str, Any] = dict(),
    prompt_inputs: Mapping[str, Any] = dict(),
    use_default_callback_handler: Literal[True] = True,
    invoke_config: RunnableConfig | None = None,
    invoke_kwargs: Mapping[str, Any] = dict(),
) -> tuple[_O, OpenAICallbackHandler]: ...


@overload
async def invoke_chat_model(
    model_id: str,
    prompt: str
    | Sequence[tuple[Literal["system", "human", "ai"], str | list[dict[str, str]]]]
    | ChatPromptTemplate,
    *,
    model_provider: str | None = None,
    configurable_fields: Literal["any"] | list[str] | tuple[str, ...] | None = None,
    config_prefix: str | None = None,
    model_kwargs: Mapping[str, Any] = dict(),
    output_structure: type[_O] = Output,
    output_structure_kwargs: Mapping[str, Any] = dict(),
    prompt_inputs: Mapping[str, Any] = dict(),
    use_default_callback_handler: Literal[False] = False,
    invoke_config: RunnableConfig | None = None,
    invoke_kwargs: Mapping[str, Any] = dict(),
) -> _O: ...


async def invoke_chat_model(
    model_id: str,
    prompt: str
    | Sequence[tuple[Literal["system", "human", "ai"], str | list[dict[str, str]]]]
    | ChatPromptTemplate,
    *,
    model_provider: str | None = None,
    configurable_fields: Literal["any"] | list[str] | tuple[str, ...] | None = None,
    config_prefix: str | None = None,
    model_kwargs: Mapping[str, Any] = dict(),
    output_structure: type[_O] = Output,
    output_structure_kwargs: Mapping[str, Any] = dict(),
    prompt_inputs: Mapping[str, Any] = dict(),
    use_default_callback_handler: bool = True,
    invoke_config: RunnableConfig | None = None,
    invoke_kwargs: Mapping[str, Any] = dict(),
) -> _O | tuple[_O, OpenAICallbackHandler]:
    """
    Asynchronously calls an LLM in a single invocation with minimal requirements -- a model ID to use and a prompt.

    Make sure you've installed the appropriate LangChain package for the model provider you're using, e.g., `pip install langchain-google-vertexai` to access Google's Gemini models.

    Args:
        model_id (str): ID of the model to use, e.g., "gemini-2.0-flash-001".
        prompt (str | Sequence[tuple[Literal["system", "human", "ai"], str | list[dict[str, str]]]] | ChatPromptTemplate): The prompt to use. Can either be a string, a sequence of tuples fit to feed into `langchain.chat_models.ChatPromptTemplate`, or a `langchain.chat_models.ChatPromptTemplate` instance.
        model_provider (str | None): Model provider as required by `langchain.chat_models.init_chat_model`. Defaults to None.
        configurable_fields (Literal["any"] | list[str] | tuple[str, ...] | None): Configurable fields for the model, as required by `langchain.chat_models.init_chat_model`. Defaults to None.
        config_prefix (str | None): Configuration prefix for the model, as required by `langchain.chat_models.init_chat_model`. Defaults to None.
        model_kwargs (Mapping[str, Any]): Keyword arguments to pass `langchain.chat_models.init_chat_model`. Defaults to an empty dictionary. This would be, for example, the place to specify the desired model temperature and max output tokens.
        output_structure (type[_O]): Structure of the output. Defaults to Output.
        output_structure_kwargs (Mapping[str, Any]): Keyword arguments for the output structure. Defaults to an empty dictionary. This would be, for example, the place to specify the output structure method such as `json_mode`.
        prompt_inputs (Mapping[str, Any]): Inputs for the prompt during a LangChain `ainvoke` chain call, if the prompt is a LangChain template holding `{}` references to variables. Defaults to an empty dictionary.
        use_default_callback_handler (bool): Whether to use the default callback handler returned by this function. Defaults to True.
        invoke_config (RunnableConfig | None): Configuration for the LangChain `ainvoke` chain call. Defaults to None. This would, for example, contain LangChain callback handlers you'd like to pass to the model, in which case it's probably a good idea to set `use_default_callback_handler` to `False`.
        invoke_kwargs (Mapping[str, Any]): Keyword arguments for the invocation. Defaults to an empty dictionary.

    Returns:
        _O | tuple[_O, OpenAICallbackHandler]: Model output. If `use_default_callback_handler` is `True`, the output is a tuple containing the model output and the default callback handler. If `use_default_callback_handler` is `False`, the output is just the model output.

    Raises:
        NoResult: If the model call doesn't return anything, which typically happens when using a model with not enough max output tokens specified.
    """
    llm = cast(
        Runnable[LanguageModelInput, _O | None],
        init_chat_model(
            model=model_id,
            model_provider=model_provider,
            configurable_fields=configurable_fields,
            config_prefix=config_prefix,
            **model_kwargs,
        ).with_structured_output(output_structure, **output_structure_kwargs),
    )

    if isinstance(prompt, str):
        _prompt = ChatPromptTemplate([("human", prompt)])
    elif isinstance(prompt, Sequence):
        _prompt = ChatPromptTemplate(prompt)
    else:
        _prompt = prompt

    chain = _prompt | llm
    default_callback_handler = OpenAICallbackHandler()

    if use_default_callback_handler:
        if invoke_config is None:
            _invoke_config = RunnableConfig(callbacks=[default_callback_handler])
        elif (callbacks := invoke_config.get("callbacks")) is None:
            _invoke_config = RunnableConfig(
                {**invoke_config, "callbacks": [default_callback_handler]}
            )
        elif isinstance(callbacks, BaseCallbackManager):
            _invoke_config = RunnableConfig(
                {
                    **invoke_config,
                    "callbacks": callbacks.merge(
                        BaseCallbackManager(handlers=[default_callback_handler])
                    ),
                }
            )
        else:
            _invoke_config = RunnableConfig(
                {**invoke_config, "callbacks": [*callbacks, default_callback_handler]}
            )
    else:
        _invoke_config = invoke_config

    output = await chain.ainvoke({**prompt_inputs}, _invoke_config, **invoke_kwargs)

    if output is None:
        raise NoResult(
            "Chain output is None. This is likely due to using a model with not enough output tokens. Try using a different model or increasing the output token limit."
        )

    if use_default_callback_handler:
        return output, default_callback_handler

    return output
