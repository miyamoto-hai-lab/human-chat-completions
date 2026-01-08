"""
設定画面
"""
import flet as ft

class SettingsDialog(ft.AlertDialog):
    def __init__(self, page: ft.Page):
        self.main_page = page
        
        # Initialize with default values
        self.provider_dropdown = ft.Dropdown(
            label="Provider",
            value="openai",
            options=[
                ft.dropdown.Option("openai", "OpenAI"),
                ft.dropdown.Option("google_genai", "Google Gemini"),
                ft.dropdown.Option("anthropic", "Anthropic"),
            ],
            width=200,
        )

        self.model_field = ft.TextField(
            label="Model Name",
            value="gpt-4o",
            hint_text="e.g. gpt-4o, gemini-1.5-pro",
            expand=True,
        )

        self.api_key_field = ft.TextField(
            label="API Key",
            value="",
            password=True,
            can_reveal_password=True,
            expand=True,
        )

        super().__init__(
            title=ft.Text("Settings"),
            content=ft.Column(
                [
                    ft.Text("LLM Configuration", weight=ft.FontWeight.BOLD),
                    self.provider_dropdown,
                    self.model_field,
                    self.api_key_field,
                ],
                tight=True,
                width=400,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=self.close_dialog),
                ft.ElevatedButton("Save", on_click=self.save_settings),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    def close_dialog(self, e):
        self.main_page.close(self)

    def save_settings(self, e):
        # Settings are kept in memory (in control values)
        self.main_page.close(self)
        self.main_page.open(ft.SnackBar(content=ft.Text("Settings saved!")))

    def show(self):
        self.main_page.open(self)