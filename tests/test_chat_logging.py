from src.model.api_model import (
    ChatCompletionRequestAssistantMessage,
    ChatCompletionRequestSystemMessage,
    ChatCompletionRequestUserMessage,
)
from src.model.chat_logging import ChatMessage, chat_logger


def test_chatlogger():
    chat_logger.clear_chats()
    listener_called_count = 0

    def listener(_, __, ___):
        nonlocal listener_called_count
        listener_called_count += 1

    chat_logger.add_on_message_recieved_listener(listener)
    initial_message = [
        ChatCompletionRequestSystemMessage(
            content="あなたはアシスタントボットです．", name=None
        ),
        ChatCompletionRequestUserMessage(content="こんにちは！", name=None),
    ]
    chat_logger.on_message_recieved("", "", initial_message)
    chat_logger.add_message(
        0,
        ChatMessage(
            ChatCompletionRequestAssistantMessage(
                content="どうもこんにちは！", name=None
            )
        ),
    )
    assert listener_called_count == 2


def test_chat_route():
    chat_logger.clear_chats()
    initial_request = [
        ChatCompletionRequestSystemMessage(
            content="あなたはアシスタントボットです．", name=None
        ),
        ChatCompletionRequestUserMessage(content="こんにちは！", name=None),
    ]
    chat_logger.on_message_recieved("", "", initial_request)
    chat_logger.add_message(
        0,
        ChatMessage(
            ChatCompletionRequestAssistantMessage(
                content="どうもこんにちは！", name=None
            )
        ),
    )
    interrupted_request = [
        ChatCompletionRequestSystemMessage(
            content="この会話のタイトルをつけてください．", name=None
        )
    ]
    chat_logger.on_message_recieved("", "", interrupted_request)
    second_request = [
        ChatCompletionRequestSystemMessage(
            content="あなたはアシスタントボットです．", name=None
        ),
        ChatCompletionRequestUserMessage(content="こんにちは！", name=None),
        ChatCompletionRequestUserMessage(content="どうも！", name=None),
    ]
    chat_logger.on_message_recieved("", "", second_request)
    interrupted_request = [
        ChatCompletionRequestSystemMessage(
            content="この会話のタイトルをつけてください．", name=None
        )
    ]
    chat_logger.on_message_recieved("", "", interrupted_request)
    third_request = [
        ChatCompletionRequestSystemMessage(
            content="あなたはアシスタントボットです．", name=None
        ),
        ChatCompletionRequestUserMessage(content="こんにちは！", name=None),
        ChatCompletionRequestUserMessage(content="どうも！", name=None),
        ChatCompletionRequestUserMessage(content="自己紹介してください", name=None),
    ]
    chat_logger.on_message_recieved("", "", third_request)
    assert len(chat_logger.chats) == 3
