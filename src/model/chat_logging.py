import json
from datetime import datetime
from typing import Any, Callable, Optional

from __version__ import VERSION
from model.api_model import (
    ChatCompletionRequestMessage,
)
from model.attachments import attachment_manager


class ChatMessage:
    def __init__(
        self,
        request_message: ChatCompletionRequestMessage,
        created_at: Optional[datetime] = None,
    ):
        self.created_at = created_at
        self.request_message = request_message

    @property
    def role(self):
        return self.request_message.role

    @property
    def content(self):
        return self.request_message.content

    async def to_dict(
        self,
        include_bytes: bool = False,
        include_base64: bool = False,
        serialize_datetime: bool = False,
    ) -> dict[str, Any]:
        d: dict[str, Any] = {
            "created_at": self.created_at
        } | await self._convert_content_to_dict(include_bytes, include_base64)
        if serialize_datetime and d["created_at"]:
            d["created_at"] = d["created_at"].astimezone().isoformat()
        return d

    async def _convert_content_to_dict(
        self,
        include_bytes: bool,
        include_base64: bool,
    ) -> dict[str, Any]:
        if isinstance(self.request_message.content, str):
            text = self.request_message.content
            parts = [{"type": "text", "text": text}]
        elif isinstance(self.request_message.content, list):
            texts = []
            parts = []
            for part in self.request_message.content:
                if part.type == "text":
                    texts.append(part.text)
                    parts.append({"type": "text", "text": texts})
                elif part.type == "image":
                    texts.append("[Image]")
                    part_dict = {"type": "image", "url": part.url}
                    if include_bytes:
                        part_dict["data"], _ = await attachment_manager.get_bytes(
                            part.url
                        )
                    if include_base64:
                        base64_data, content_type = await attachment_manager.get_base64(
                            part.url
                        )
                        part_dict["base64"] = (
                            f"data:{content_type};base64,{base64_data}"
                        )
                    parts.append(part_dict)
                else:
                    # Audioには非対応
                    pass
            text = "\n".join(texts)
        else:
            # その他のタイプには非対応
            text = str(self.request_message.content)
            parts = [{"type": "unknown", "content": text}]
        return {
            "role": self.request_message.role,
            "text": text,
            "parts": parts,
        }

    def __eq__(self, value: Any, /) -> bool:
        if isinstance(value, ChatMessage):
            return (
                self.request_message.role == value.role
                and self.request_message.content == value.content
            )
        if isinstance(value, ChatCompletionRequestMessage):
            return (
                self.request_message.role == value.role
                and self.request_message.content == value.content
            )
        else:
            raise ValueError(f"Unsupported type {type(value)}")

    def __hash__(self) -> int:
        return hash((self.request_message.role, self.request_message.content))

    def __repr__(self) -> str:
        return f"ChatMessage(role: '{self.role}', content: '{self.content}'))"


class ChatLogger:
    MATCH_MESSAGES_THRESHOLD = 3

    def __init__(self):
        self.listening_address = ""
        self.model = ""
        self.apikey = ""
        self.chats = []
        # {
        #     "created_at": datetime.now(),
        #     "messages": [],
        #     "latest_request_time": datetime.now(),
        # }
        self._on_message_recieved_listeners = {
            "user": set(),
            "assistant": set(),
            "system": set(),
            "developer": set(),
        }
        self.last_accessed_chat_index = 0

    def add_on_message_recieved_listener(
        self,
        listener: Callable[[str, list[ChatMessage], dict[str, tuple]], None],
        roles: set[str] = {"user", "assistant", "system", "developer"},
    ):
        for role in roles:
            if role not in self._on_message_recieved_listeners:
                raise ValueError(f"Invalid role {role}")
            self._on_message_recieved_listeners[role].add(listener)

    def on_message_recieved(
        self, apikey: str, model: str, messages: list[ChatCompletionRequestMessage]
    ):
        req_messages = [ChatMessage(message) for message in messages]
        chat_index = self._find_chat_index(req_messages)
        if chat_index is None:
            self.chats.append(
                {
                    "created_at": datetime.now(),
                    "messages": req_messages,
                    "latest_request_time": datetime.now(),
                }
            )
            diff = {"added": tuple(range(len(req_messages)))}
            chat_index = len(self.chats) - 1
        else:
            chat = self.chats[chat_index]
            chat["latest_request_time"] = datetime.now()
            diff = self._diff_messages(req_messages, chat["messages"])
            for i in diff["edited"]:
                chat["messages"][i] = req_messages[i]
            for i in diff.get("added", []):
                req_messages[i].created_at = datetime.now()
                chat["messages"].append(req_messages[i])
        for listener_func in self._on_message_recieved_listeners[req_messages[-1].role]:
            listener_func(chat_index, self.chats[chat_index]["messages"], diff)
        self.last_accessed_chat_index = chat_index

    def add_message(self, chat_index: int, message: ChatMessage):
        original_length = len(self.chats[chat_index]["messages"])
        self.chats[chat_index]["messages"].append(message)
        for listener_func in self._on_message_recieved_listeners[message.role]:
            listener_func(
                chat_index,
                self.chats[chat_index]["messages"],
                {"added": (original_length,)},
            )
        self.last_accessed_chat_index = chat_index

    def clear_chats(self):
        self.chats.clear()

    async def export(
        self,
        chat_index: int,
        filename: str,
        comment: Optional[str] = None,
        include_base64: bool = False,
    ):
        chat = [
            await message.to_dict(
                include_bytes=False,
                include_base64=include_base64,
                serialize_datetime=True,
            )
            for message in self.chats[chat_index]["messages"]
        ]
        if self.chats[chat_index]["latest_request_time"]:
            latest_request_time = (
                self.chats[chat_index]["latest_request_time"].astimezone().isoformat()
            )
        else:
            latest_request_time = None
        data = {
            "exported_at": datetime.now().astimezone().isoformat(),
            "app_version": VERSION,
            "request": {
                "latest_request_time": latest_request_time,
                "listening_address": self.listening_address,
                "model": self.model,
                "apikey": self.apikey,
            },
            "messages": chat,
            "settings": {},  # 将来的に実装
        }
        if comment:
            data = {"comment": comment} | data  # コメントを最初に追加
        with open(filename, "w", encoding="UTF-8") as export_file:
            json.dump(data, export_file, ensure_ascii=False)

    def _find_chat_index(self, messages: list[ChatMessage]):
        if len(messages) <= 1:
            messages_history = tuple(messages)
        else:
            messages_history = tuple(messages[:-1])
        messages_hash = hash(messages_history[: self.MATCH_MESSAGES_THRESHOLD])
        for i, chat in enumerate(self.chats):
            if messages_hash == hash(
                tuple(chat["messages"][: self.MATCH_MESSAGES_THRESHOLD])
            ):
                return i
        return None

    def _diff_messages(self, target: list[ChatMessage], from_: list[ChatMessage]):
        nochange = []
        edited = []
        for i, (target_message, to_message) in enumerate(zip(target, from_)):
            if target_message == to_message:
                nochange.append(i)
            else:
                edited.append(i)
        diff = {"nochange": tuple(nochange), "edited": (edited)}
        if i < max(len(target), len(from_)) - 1:
            if len(target) < len(from_):
                diff["deleted"] = tuple(range(4, len(from_) - 1))
            else:
                diff["added"] = tuple(range(4, len(from_) - 1))
        return diff


chat_logger = ChatLogger()
