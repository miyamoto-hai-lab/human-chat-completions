from __future__ import annotations

import time
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

# ==========================================
# Base Model with Ignore Extra
# ==========================================


class OpenAIBaseModel(BaseModel):
    """
    すべてのモデルの基底クラス。
    未知のフィールドが送られてきても無視する設定を適用します。
    """

    model_config = ConfigDict(extra="ignore")


# ==========================================
# Enums
# ==========================================


class ChatCompletionRole(str, Enum):
    system = "system"
    developer = "developer"
    user = "user"
    assistant = "assistant"
    tool = "tool"
    function = "function"


class FinishReason(str, Enum):
    stop = "stop"


# ==========================================
# Message Content Parts
# ==========================================


class ChatCompletionRequestMessageContentPartText(OpenAIBaseModel):
    type: Literal["text"] = "text"
    text: str = Field(..., description="The text content.")


class ImageUrl(OpenAIBaseModel):
    url: str = Field(
        ..., description="Either a URL of the image or the base64 encoded image data."
    )
    detail: Optional[Literal["auto", "low", "high"]] = Field(
        "auto", description="Specifies the detail level of the image."
    )


class ChatCompletionRequestMessageContentPartImage(OpenAIBaseModel):
    type: Literal["image_url"] = "image_url"
    image_url: ImageUrl = Field(..., description="The image URL details.")


class InputAudio(OpenAIBaseModel):
    data: str
    format: str


class ChatCompletionRequestMessageContentPartInputAudio(OpenAIBaseModel):
    type: Literal["input_audio"] = "input_audio"
    input_audio: InputAudio = Field(..., description="The audio content.")


ChatCompletionRequestMessageContentPart = Union[
    ChatCompletionRequestMessageContentPartText,
    ChatCompletionRequestMessageContentPartImage,
    ChatCompletionRequestMessageContentPartInputAudio,
]

# ==========================================
# Request Messages
# ==========================================


class ChatCompletionRequestSystemMessage(OpenAIBaseModel):
    role: Literal["system"] = "system"
    content: str = Field(..., description="The contents of the system message.")
    name: Optional[str] = Field(
        None, description="An optional name for the participant."
    )


class ChatCompletionRequestUserMessage(OpenAIBaseModel):
    role: Literal["user"] = "user"
    content: Union[str, List[ChatCompletionRequestMessageContentPart]] = Field(
        ..., description="The contents of the user message."
    )
    name: Optional[str] = Field(
        None, description="An optional name for the participant."
    )


class ChatCompletionRequestAssistantMessage(OpenAIBaseModel):
    role: Literal["assistant"] = "assistant"
    content: Optional[str] = Field(
        None, description="The contents of the assistant message."
    )
    name: Optional[str] = Field(
        None, description="An optional name for the participant."
    )


class ChatCompletionRequestToolMessage(OpenAIBaseModel):
    role: Literal["tool"] = "tool"
    content: str = Field(..., description="The contents of the tool message.")
    tool_call_id: str = Field(
        ..., description="Tool call that this message is responding to."
    )


class ChatCompletionRequestFunctionMessage(OpenAIBaseModel):
    role: Literal["function"] = "function"
    content: Optional[str] = Field(
        None, description="The contents of the function message."
    )
    name: str = Field(..., description="The name of the function to call.")


class ChatCompletionRequestDeveloperMessage(OpenAIBaseModel):
    """
    追加: Developer Role Message
    o1-previewなどでSystem Roleの代わりに使用されるロール。
    """

    role: Literal["developer"] = "developer"
    content: str = Field(..., description="The contents of the developer message.")
    name: Optional[str] = Field(
        None, description="An optional name for the participant."
    )


ChatCompletionRequestMessage = Union[
    ChatCompletionRequestSystemMessage,
    ChatCompletionRequestDeveloperMessage,
    ChatCompletionRequestUserMessage,
    ChatCompletionRequestAssistantMessage,
    ChatCompletionRequestToolMessage,
    ChatCompletionRequestFunctionMessage,
]

# ==========================================
# Request Model with Strict Validation
# ==========================================


class ResponseFormat(OpenAIBaseModel):
    type: Literal["text", "json_object", "json_schema"]
    json_schema: Optional[Dict[str, Any]] = None


class CreateChatCompletionRequest(OpenAIBaseModel):
    messages: List[ChatCompletionRequestMessage] = Field(
        ..., description="A list of messages comprising the conversation so far."
    )
    model: str = Field(..., description="ID of the model to use.")
    stream: Optional[bool] = Field(
        False, description="If set, partial message deltas will be sent."
    )
    user: Optional[str] = Field(
        None, description="A unique identifier representing your end-user."
    )

    # バリデーション対象のパラメータ（これらは明示的に定義しないとextra='ignore'で消えてしまいチェックできない）
    store: Optional[bool] = Field(
        False, description="Whether or not to store the output."
    )
    modalities: Optional[List[str]] = Field(None, description="Output types.")
    response_format: Optional[ResponseFormat] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    logprobs: Optional[bool] = Field(
        False, description="Whether to return log probabilities."
    )
    top_logprobs: Optional[int] = Field(
        None, description="Number of most likely tokens to return."
    )
    n: Optional[int] = Field(1, description="How many choices to generate.")

    @model_validator(mode="after")
    def validate_capabilities(self) -> CreateChatCompletionRequest:
        """
        Human Backendの制約に基づき、サポート外の機能を要求された場合にエラーを返す。
        """

        # 1. Output Modalities Check
        if self.modalities:
            for modality in self.modalities:
                if modality != "text":
                    raise ValueError(
                        f"Human Chat Completions API does not support output modality '{modality}'. Only 'text' is supported."
                    )

        # 2. Store Check
        if self.store:
            raise ValueError(
                "Human Chat Completions API does not support 'store=True'. Conversations are not persisted."
            )

        # 3. Response Format Check
        if self.response_format and self.response_format.type in [
            "json_object",
            "json_schema",
        ]:
            raise ValueError(
                f"Human Chat Completions API does not support response_format '{self.response_format.type}'. Only 'text' is supported."
            )

        # 4. Tool Choice Check
        if self.tool_choice:
            if isinstance(self.tool_choice, str) and self.tool_choice == "required":
                raise ValueError(
                    "Human Chat Completions API does not support tool_choice 'required'."
                )
            if (
                isinstance(self.tool_choice, dict)
                and self.tool_choice.get("type") == "function"
            ):
                raise ValueError(
                    "Human Chat Completions API does not support specific tool selection."
                )

        # 5. Input Audio Check
        for msg in self.messages:
            if isinstance(msg, ChatCompletionRequestUserMessage) and isinstance(
                msg.content, list
            ):
                for part in msg.content:
                    if getattr(part, "type", "") == "input_audio":
                        raise ValueError(
                            "Human Chat Completions API does not support input audio messages."
                        )

        # 6. Logprobs Check (重要: クライアントクラッシュ防止)
        if self.logprobs or self.top_logprobs:
            raise ValueError(
                "Human Chat Completions API does not support 'logprobs'. Humans cannot calculate token probabilities."
            )

        # 7. N (Choices) Check (重要: 人間負荷防止)
        if self.n is not None and self.n > 1:
            raise ValueError(
                "Human Chat Completions API does not support 'n > 1'. Humans can only provide a single response."
            )

        return self


# ==========================================
# Usage Models
# ==========================================


class CompletionTokensDetails(OpenAIBaseModel):
    reasoning_tokens: int = Field(
        0, description="Tokens generated by the model for reasoning."
    )
    audio_tokens: int = Field(
        0, description="Audio input tokens generated by the model."
    )
    accepted_prediction_tokens: int = Field(
        0,
        description="When using Predicted Outputs, the number of tokens in the prediction that appeared in the completion.",
    )
    rejected_prediction_tokens: int = Field(
        0,
        description="When using Predicted Outputs, the number of tokens in the prediction that did not appear in the completion.",
    )


class PromptTokensDetails(OpenAIBaseModel):
    audio_tokens: int = Field(
        0, description="Audio input tokens present in the prompt."
    )
    cached_tokens: int = Field(0, description="Cached tokens present in the prompt.")


class CompletionUsage(OpenAIBaseModel):
    completion_tokens: int = Field(
        0, description="Number of tokens in the generated completion."
    )
    prompt_tokens: int = Field(0, description="Number of tokens in the prompt.")
    total_tokens: int = Field(
        0,
        description="Total number of tokens used in the request (prompt + completion).",
    )
    completion_tokens_details: CompletionTokensDetails = Field(
        default_factory=CompletionTokensDetails,
        description="Breakdown of tokens generated in a completion.",
    )
    prompt_tokens_details: PromptTokensDetails = Field(
        default_factory=PromptTokensDetails,
        description="Breakdown of tokens used in a prompt.",
    )


# ==========================================
# Response Models (Non-Streaming)
# ==========================================


class ChatCompletionResponseMessage(OpenAIBaseModel):
    role: Literal["assistant"] = "assistant"
    content: Optional[str] = Field(None, description="The contents of the message.")
    refusal: Optional[str] = Field(
        None, description="The refusal message generated by the model."
    )  # クライアント互換用


class ChatCompletionChoice(OpenAIBaseModel):
    index: int = Field(
        ..., description="The index of the choice in the list of choices."
    )
    message: ChatCompletionResponseMessage = Field(
        ..., description="A chat completion message generated by the model."
    )
    finish_reason: FinishReason = Field(
        ..., description="The reason the model stopped generating tokens."
    )
    logprobs: Optional[Any] = Field(
        None, description="Log probability information."
    )  # クライアント互換用: 常にNoneだがフィールドは存在させる


class CreateChatCompletionResponse(OpenAIBaseModel):
    id: str = Field(..., description="A unique identifier for the chat completion.")
    choices: List[ChatCompletionChoice] = Field(
        ..., description="A list of chat completion choices."
    )
    created: int = Field(
        default_factory=lambda: int(time.time()),
        description="The Unix timestamp (in seconds) of when the chat completion was created.",
    )
    model: str = Field(..., description="The model used for the chat completion.")
    system_fingerprint: Optional[str] = Field(
        "fp_human_backend", description="Backend configuration fingerprint."
    )  # クライアント互換用: ダミー値推奨
    object: Literal["chat.completion"] = Field(
        "chat.completion",
        description="The object type, which is always `chat.completion`.",
    )
    usage: CompletionUsage = Field(
        default_factory=CompletionUsage,
        description="Usage statistics for the completion request.",
    )


# ==========================================
# Response Models (Streaming / Chunk)
# ==========================================


class ChatCompletionStreamResponseDelta(OpenAIBaseModel):
    role: Optional[Literal["assistant"]] = Field(
        None, description="The role of the author of this message."
    )
    content: Optional[str] = Field(None, description="The contents of the message.")
    refusal: Optional[str] = Field(
        None, description="The refusal message."
    )  # クライアント互換用


class ChatCompletionStreamChoice(OpenAIBaseModel):
    index: int = Field(
        ..., description="The index of the choice in the list of choices."
    )
    delta: ChatCompletionStreamResponseDelta = Field(
        ...,
        description="A chat completion delta generated by streamed model responses.",
    )
    finish_reason: Optional[FinishReason] = Field(
        None, description="The reason the model stopped generating tokens."
    )
    logprobs: Optional[Any] = Field(
        None, description="Log probability information."
    )  # クライアント互換用


class ChatCompletionChunk(OpenAIBaseModel):
    id: str = Field(..., description="A unique identifier for the chat completion.")
    choices: List[ChatCompletionStreamChoice] = Field(
        ..., description="A list of chat completion choices."
    )
    created: int = Field(
        default_factory=lambda: int(time.time()),
        description="The Unix timestamp (in seconds) of when the chat completion was created.",
    )
    model: str = Field(..., description="The model used for the chat completion.")
    system_fingerprint: Optional[str] = Field(
        "fp_human_backend", description="Backend configuration fingerprint."
    )  # クライアント互換用
    object: Literal["chat.completion.chunk"] = Field(
        "chat.completion.chunk",
        description="The object type, which is always `chat.completion.chunk`.",
    )
    usage: Optional[CompletionUsage] = Field(
        None, description="Optional usage for the final chunk."
    )


# ==========================================
# Model List Response
# ==========================================


class Model(OpenAIBaseModel):
    id: str = Field(
        ...,
        description="The model identifier, which can be referenced in the API endpoints.",
    )
    created: int = Field(
        default_factory=lambda: int(time.time()),
        description="The Unix timestamp (in seconds) when the model was created.",
    )
    object: Literal["model"] = "model"
    owned_by: str = Field(..., description="The organization that owns the model.")

    def __hash__(self):
        return hash(self.id)


class ListModelsResponse(OpenAIBaseModel):
    object: Literal["list"] = "list"
    data: List[Model] = Field(..., description="List of models.")


# ==========================================
# Ollama Compatibility Models (Added)
# ==========================================


class OllamaModelDetails(OpenAIBaseModel):
    format: str = "gguf"
    family: str = "human"
    families: Optional[List[str]] = None
    parameter_size: str = "1000B"
    quantization_level: str = "Q4_0"


class OllamaModel(OpenAIBaseModel):
    name: str
    model: str
    modified_at: str
    size: int = 0
    digest: str = "sha256:dummy_digest_for_human_backend"
    details: OllamaModelDetails


class OllamaListModelsResponse(OpenAIBaseModel):
    models: List[OllamaModel]
