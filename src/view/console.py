"""
メイン画面右側のレスポンス構築
"""
import json
from datetime import datetime
from os import getenv
from typing import TYPE_CHECKING, List

import flet as ft
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from model.copilot import Copilot
from view.settings import SettingsDialog

if TYPE_CHECKING:
    from view.chat import ChatView


class ConsoleView(ft.Container):
    def __init__(self, page: ft.Page, chat_view: "ChatView"):
        super().__init__(expand=True, padding=20)
        self.page = page
        self.chat_view = chat_view

        # Initialize settings dialog
        self.settings_dialog = SettingsDialog(page)

        # FilePicker for export
        self.file_picker = ft.FilePicker(on_result=self.on_save_result)
        self.page.overlay.append(self.file_picker)

        # 1. Export Button
        self.export_button = ft.ElevatedButton(
            "Export Chat Log",
            icon=ft.Icons.DOWNLOAD,
            bgcolor=ft.Colors.TEAL_400,
            color=ft.Colors.WHITE,
            on_click=self.export_chat_log,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=5),
            )
        )

        # 2. Controls & Mode Switch
        self.settings_button = ft.IconButton(
            ft.Icons.SETTINGS, 
            tooltip="Settings", 
            on_click=lambda e: self.settings_dialog.show()
        )

        self.theme_switch = ft.SegmentedButton(
            selected={ft.ThemeMode.SYSTEM.value},
            allow_multiple_selection=False,
            segments=[
                ft.Segment(
                    value=ft.ThemeMode.LIGHT.value,
                    label=ft.Text("Light Mode"),
                    icon=ft.Icon(ft.Icons.LIGHT_MODE),
                ),
                ft.Segment(
                    value=ft.ThemeMode.SYSTEM.value,
                    label=ft.Text("System Mode"),
                    icon=ft.Icon(ft.Icons.BRIGHTNESS_6),
                ),
                ft.Segment(
                    value=ft.ThemeMode.DARK.value,
                    label=ft.Text("Dark Mode"),
                    icon=ft.Icon(ft.Icons.DARK_MODE),
                ),
            ],
            show_selected_icon=False,
            on_change=self.set_theme,
            width=400, # Approximate width to match image
        )

        self.mode_segment = ft.SegmentedButton(
            selected={"manual"},
            allow_multiple_selection=False,
            segments=[
                ft.Segment(
                    value="manual",
                    label=ft.Text("Manual"),
                    icon=ft.Icon(ft.Icons.PERSON),
                ),
                ft.Segment(
                    value="llm_draft",
                    label=ft.Text("LLM Draft"),
                    icon=ft.Icon(ft.Icons.CHAT_BUBBLE_OUTLINE),
                ),
                ft.Segment(
                    value="full_llm",
                    label=ft.Text("Full LLM"),
                    icon=ft.Icon(ft.Icons.SMART_TOY),
                ),
            ],
            show_selected_icon=False,
            width=400, # Approximate width to match image
        )

        # 3. System Prompt
        self.system_prompt = ft.TextField(
            label="> Draft Generation Prompt (SYSTEM)",
            value="あなたは親切なAIアシスタントです。ユーザーの質問に対して、簡潔かつ丁寧に回答してください。",
            multiline=True,
            min_lines=3,
            max_lines=5,
            text_size=13,
            border_radius=5,
        )

        # 4. Drafts Area
        self.drafts_column = ft.Column(spacing=10)
        # Placeholder
        self.drafts_column.controls = [
            self._create_draft_card("1", "To be implemented"),
            self._create_draft_card("2", "To be implemented"),
            self._create_draft_card("3", "To be implemented"),
        ]
        
        self.regenerate_button = ft.TextButton(
            content=ft.Row([ft.Icon(ft.Icons.REFRESH, size=16), ft.Text("Regenerate")]),
            style=ft.ButtonStyle(color=ft.Colors.BLUE),
            on_click=self.regenerate_drafts
        )

        self.content = ft.Column(
            [
                self.export_button,
                ft.Text(f"Log file location: {getenv('FLET_APP_CONSOLE', 'unknown')}", color=ft.Colors.GREY_700),
                ft.Divider(color=ft.Colors.TRANSPARENT, height=10),

                ft.Row([ft.Text("Settings", weight=ft.FontWeight.BOLD), self.theme_switch, self.settings_button], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                
                ft.Row(
                    [
                        ft.Text("Response Mode", weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_700),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Container(self.mode_segment, padding=ft.padding.only(bottom=20)),

                self.system_prompt,
                
                ft.Row([ft.Icon(ft.Icons.ARROW_DOWNWARD, color=ft.Colors.GREY_400)], alignment=ft.MainAxisAlignment.CENTER),
                
                ft.Row(
                    [
                        ft.Text("COPILOT Draft Candidates", weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_700),
                        self.regenerate_button
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                ),
                
                self.drafts_column,
            ],
            scroll=ft.ScrollMode.AUTO, # Enable scrolling for console view
        )

    def _create_draft_card(self, index: str, text: str):
        def on_card_click(e):
            # Paste text into chat input
            self.chat_view.input_field.disabled = False
            self.chat_view.input_field.value = text
            self.chat_view.input_field.update()
            
            # Log the selected draft
            self.chat_view.add_draft_log(text)

            # Also enable send button if not already
            self.chat_view.send_button.disabled = False
            self.chat_view.send_button.bgcolor = ft.Colors.BLUE_600
            self.chat_view.send_button.update()

        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Text(index, size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_600),
                        bgcolor=ft.Colors.GREY_200,
                        padding=5,
                        border_radius=5,
                    ),
                    ft.Text(text, expand=True, size=13),
                ],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
            padding=10,
            border=ft.border.all(1, "outlineVariant"),
            border_radius=8,
            ink=True,
            on_click=on_card_click,
        )

    async def regenerate_drafts(self, e):
        # 1. Get Settings from Dialog Instance (In-Memory)
        provider = self.settings_dialog.provider_dropdown.value
        model_name = self.settings_dialog.model_field.value
        api_key = self.settings_dialog.api_key_field.value

        if not api_key:
            self.page.open(ft.SnackBar(content=ft.Text("Please set API Key in Settings first.")))
            return

        # 2. UI Loading State
        self.regenerate_button.disabled = True
        
        # Preserve structure, update text to Loading...
        for control in self.drafts_column.controls:
            if isinstance(control, ft.Container):
                 # Find text control in the row
                 # Container -> Row -> [IndexContainer, Text(expand=True)]
                 try:
                     text_control = control.content.controls[1]
                     text_control.value = "Generating..."
                 except:
                     pass
        self.page.update()

        try:
            # 3. Initialize Copilot
            copilot = Copilot(model_provider=provider, model_name=model_name, api_key=api_key)

            # 4. Extract History
            history = [
                SystemMessage(content=self.system_prompt.value)
            ]
            
            # Extract conversations from ChatView
            for control in self.chat_view.messages_list.controls:
                if not isinstance(control, ft.Row):
                    continue
                try:
                    bubble = control.controls[0]
                    content_text = bubble.content.value
                    is_user = (control.alignment == ft.MainAxisAlignment.START)
                    
                    if is_user:
                        history.append(HumanMessage(content=content_text))
                    else:
                        history.append(AIMessage(content=content_text))
                except Exception:
                    continue

            # 5. Generate Response
            result = await copilot.generate_response(
                instruction="ユーザーの直前の発言に対する返信候補を生成してください。",
                history=history
            )

            # 6. Update UI
            # Update existing cards instead of replacing to maintain structure if possible,
            # or just replace using _create_draft_card to be safe.
            self.drafts_column.controls = [
                self._create_draft_card("1", result.draft1),
                self._create_draft_card("2", result.draft2),
                self._create_draft_card("3", result.draft3),
            ]

        except Exception as ex:
            # Show error dialog
            error_dialog = ft.AlertDialog(
                title=ft.Text("Error"),
                content=ft.Text(f"返信候補の生成に失敗しました。\n\n詳細: {ex}"),
                actions=[
                    ft.TextButton("OK", on_click=lambda e: self.page.close(error_dialog))
                ],
            )
            self.page.open(error_dialog)
            
            # Reset to error state
            self.drafts_column.controls = [
                 self._create_draft_card("1", "Generation Failed"),
                 self._create_draft_card("2", "Generation Failed"),
                 self._create_draft_card("3", "Generation Failed"),
            ]
        finally:
            self.regenerate_button.disabled = False
            self.page.update()

    def set_theme(self, e):
        # This will be handled by the main app, but we need to expose the event or callback
        if e.control.page:
            e.control.page.theme_mode = e.control.selected.pop()
            e.control.page.update()

    def export_chat_log(self, e):
        now = datetime.now()
        filename = f"chatlog_{now.strftime('%Y-%m-%dT%H-%M-%S')}.json"
        self.file_picker.save_file(
            dialog_title="Save Chat Log",
            file_name=filename,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["json"]
        )

    def on_save_result(self, e: ft.FilePickerResultEvent):
        if not e.path:
            return

        conversations = self.chat_view.event_log.copy()

        export_data = {
            "savetime": datetime.now().isoformat(),
            "conversations": conversations
        }

        try:
            with open(e.path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=4, ensure_ascii=False)
            
            self.page.open(ft.SnackBar(content=ft.Text(f"Saved to {e.path}")))
        except Exception as ex:
            self.page.open(ft.SnackBar(content=ft.Text(f"Error saving file: {ex}")))

