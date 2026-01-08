"""
設定画面
"""
import flet as ft

class SettingsDialog(ft.AlertDialog):
    def __init__(self, page: ft.Page):
        self.main_page = page
        
        # Initialize with defaults (will be updated in show())
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
        self.main_page.client_storage.set("llm_provider", self.provider_dropdown.value)
        self.main_page.client_storage.set("llm_model", self.model_field.value)
        self.main_page.client_storage.set("llm_api_key", self.api_key_field.value)
        self.main_page.close(self)
        self.main_page.open(ft.SnackBar(content=ft.Text("Settings saved!")))

    def load_settings(self):
        try:
            val_provider = self.main_page.client_storage.get("llm_provider")
            val_model = self.main_page.client_storage.get("llm_model")
            val_api_key = self.main_page.client_storage.get("llm_api_key")
            
            if val_provider:
                self.provider_dropdown.value = val_provider
            if val_model:
                self.model_field.value = val_model
            if val_api_key:
                self.api_key_field.value = val_api_key
        except Exception:
            # Fallback if storage not ready or fails
            pass

    def show(self):
        self.load_settings()
        self.main_page.open(self)