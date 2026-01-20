"""
メイン画面左側のユーザとのチャット部分
"""

import asyncio
import socket
from contextlib import closing

import flet as ft

from model.api_model import (
    ChatCompletionRequestAssistantMessage,
    ChatCompletionRequestDeveloperMessage,
    ChatCompletionRequestMessage,
    ChatCompletionRequestSystemMessage,
    ChatCompletionRequestUserMessage,
)
from model.api_server import FastAPIServer


class ChatView(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__(expand=True)
        self.event_log = []
        self.synced_message_count = 0
        self.port_field = ft.TextField(
            value="8000",
            label="PORT",
            width=100,
            text_size=12,
            height=40,
            content_padding=ft.padding.symmetric(horizontal=10, vertical=0),
        )
        self.listen_button = ft.ElevatedButton(
            "STOPPED",
            bgcolor=ft.Colors.RED_400,
            color=ft.Colors.WHITE,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=5),
            ),
            on_click=self.toggle_server,
        )

        self.messages_list = ft.ListView(
            expand=True,
            spacing=10,
            padding=20,
            auto_scroll=True,
        )

        self.api_server = None

        self.input_field = ft.TextField(
            hint_text="メッセージが来たらここへ入力...",
            expand=True,
            multiline=True,
            min_lines=1,
            max_lines=5,
            border_radius=10,
            filled=True,
            disabled=True,
        )

        def send_message(e):
            if self.input_field.value.strip() == "":
                return
            self._add_message(self.input_field.value, is_user=False, is_response=True)
            self.input_field.value = ""
            self.input_field.hint_text = "メッセージが来たらここへ入力..."
            self.input_field.disabled = True
            self.send_button.disabled = True
            self.send_button.bgcolor=ft.Colors.GREY_400
            self.input_field.update()
            self.send_button.update()

        self.send_button = ft.IconButton(
            icon=ft.Icons.SEND_ROUNDED,
            icon_color=ft.Colors.WHITE,
            bgcolor=ft.Colors.GREY_400,
            tooltip="Ctrl+Enterで送信",
            on_click=send_message,
            disabled=True,
        )

        self.filter_system_prompt = False

        def toggle_filter(e):
            self.filter_system_prompt = e.control.value
            
        self.filter_button = ft.Switch(
            label="システムメッセージを非表示",
            value=self.filter_system_prompt,
            on_change=toggle_filter,
        )

        def keyboard_event(e):
            if e.ctrl and e.key == "Enter":
                send_message(e)
        page.on_keyboard_event = keyboard_event
        self.local_ip = self.get_local_ip()
        self.pending_future = None

        self.content = ft.Column(
            [
                # Top Bar
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Row(
                                [
                                    ft.Text(
                                        f"{self.local_ip}:",
                                        style=ft.TextStyle(size=12),
                                    ),
                                    self.port_field,
                                    self.listen_button,
                                ],
                                spacing=10,
                            ),
                            ft.VerticalDivider(),
                            ft.Row(
                                [
                                    self.filter_button,
                                ],
                                spacing=10,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_AROUND,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=ft.padding.symmetric(horizontal=10, vertical=5),
                    border=ft.border.only(bottom=ft.BorderSide(1, "outlineVariant")),
                ),
                # Messages Area
                ft.Container(
                    content=self.messages_list,
                    expand=True,
                    bgcolor="surfaceVariant",  # Slightly different background for chat area
                ),
                # Input Area
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [self.input_field, self.send_button],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                vertical_alignment=ft.CrossAxisAlignment.END,
                            ),
                        ],
                        spacing=2,
                    ),
                    padding=ft.padding.all(10),
                    border=ft.border.only(top=ft.BorderSide(1, "outlineVariant")),
                ),
            ],
            spacing=0,
        )
    
    def set_message(self, messages: list[dict]):
        # UIを再構築する（ログは消さない）
        self.messages_list.controls.clear()
        for message in messages:
            self._render_bubble(message["content"], message["role"] != "assistant")
        self.messages_list.update()

    def add_draft_log(self, content: str):
        """
        ログ保存用に、画面には表示しないドラフト選択履歴を追加する
        """
        self.event_log.append({"role": "draft", "content": content})

    def _render_bubble(self, message: str, is_user: bool = False):
        alignment = (
            ft.MainAxisAlignment.END
            if not is_user
            else ft.MainAxisAlignment.START
        )
        bubble_color = (
            ft.Colors.BLUE_600 if not is_user else ft.Colors.WHITE
        )
        text_color = ft.Colors.WHITE if not is_user else ft.Colors.BLACK

        # Simple bubble implementation for now
        bubble = ft.Container(
            content=ft.Text(message, color=text_color, selectable=True),
            bgcolor=bubble_color,
            border_radius=10,
            padding=10,
            on_click=lambda e: self.copy_to_clipboard(message),
        )

        row = ft.Row(
            [bubble],
            alignment=alignment,
        )
        self.messages_list.controls.append(row)

    def _add_message(self, message: str, is_user: bool = False, is_response = False):
        # 内部ログに追加
        role = "user" if is_user else "assistant"
        self.event_log.append({"role": role, "content": message})
        self.synced_message_count += 1

        self._render_bubble(message, is_user)

        if is_response:
            self.messages_list.update()
            if self.pending_future is not None and not self.pending_future.done():
                self.pending_future.set_result(message)

    def get_local_ip(self):
        """
        外部サーバーに接続を試みることにより、使用中のローカルIPアドレスを取得する
        """
        try:
            # UDPソケットを使用し、外部に出るためのルーティング情報を得る
            with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except socket.error:
            # エラー時はデフォルトとして localhost を返す
            return "127.0.0.1"
    
    async def on_message_received(self, messages: list[ChatCompletionRequestMessage]):
        messages_json = []
        for message in messages:
            if not message.content:
                continue
            if isinstance(message, ChatCompletionRequestSystemMessage) or isinstance(message, ChatCompletionRequestDeveloperMessage):
                if self.filter_system_prompt:
                    continue
                messages_json.append(message.model_dump())
            elif isinstance(message, ChatCompletionRequestUserMessage):
                if isinstance(message.content, str):
                    messages_json.append(message.model_dump())
                else:
                    continue # TODO: PartMessageを処理する
            elif isinstance(message, ChatCompletionRequestAssistantMessage):
                messages_json.append(message.model_dump())
            else:
                continue
        
        # event_logとmessages_jsonを同期させる
        # event_logには 'draft' ロールが含まれるが、messages_jsonには含まれない
        # 先頭から順にマッチングさせ、差異があれば更新、足りなければ追記する

        log_idx = 0
        msg_idx = 0
        
        while msg_idx < len(messages_json):
            # log_idxが範囲外なら、残りはすべて新規追加
            if log_idx >= len(self.event_log):
                self.event_log.append(messages_json[msg_idx])
                msg_idx += 1
                log_idx += 1
                continue
            
            # draftはスキップ
            if self.event_log[log_idx].get("role") == "draft":
                log_idx += 1
                continue

            # 既存メッセージの更新
            # メッセージの内容が更新されている可能性があるため、上書きする
            self.event_log[log_idx] = messages_json[msg_idx]
            msg_idx += 1
            log_idx += 1
        
        self.synced_message_count = len(messages_json)

        self.set_message(messages_json)
        self.pending_future = asyncio.get_running_loop().create_future()
        self.input_field.disabled = False
        self.input_field.hint_text = "レスポンスメッセージを入力..."
        self.send_button.disabled = False
        self.send_button.bgcolor=ft.Colors.BLUE_600
        self.input_field.update()
        self.send_button.update()
        result = await self.pending_future
        return result
        
    def toggle_server(self, e: ft.ControlEvent):
        if self.listen_button.text == "STOPPED":
            self.listen_button.text = "RUNNING"
            self.listen_button.bgcolor = ft.Colors.GREEN_400
            self.listen_button.disabled = True
            self.port_field.disabled = True
            self.listen_button.update()
            self.port_field.update()
            self.api_server = FastAPIServer(
                host="0.0.0.0",
                port=int(self.port_field.value),
                log_level="info",
                on_message_received=self.on_message_received,
            )
            self.api_server.start()
            self.listen_button.disabled = False
            self.listen_button.update()
        else:
            self.listen_button.text = "STOPPED"
            self.listen_button.bgcolor = ft.Colors.RED_400
            self.listen_button.disabled = True
            self.listen_button.update()
            if self.api_server:
                self.api_server.stop()
            self.port_field.disabled = False
            self.listen_button.disabled = False
            self.listen_button.update()
            self.port_field.update()

    def copy_to_clipboard(self, text: str):
        self.page.set_clipboard(text)
        self.page.open(ft.SnackBar(content=ft.Text("テキストをコピーしました")))

