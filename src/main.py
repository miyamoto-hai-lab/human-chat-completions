import webbrowser

import flet as ft

from __version__ import VERSION
from model.check_update import check_update_available
from view.chat import ChatView
from view.console import ConsoleView

GITHUB_REPOSITORY_URL = "https://github.com/miyamoto-hai-lab/human-chat-completions"


async def main(page: ft.Page):
    page.title = f"Human Chat Completions v{VERSION}"
    page.window.icon = "icon.png"

    # Theme Configuration
    page.theme = ft.Theme(
        color_scheme_seed="#086fad",
    )
    page.dark_theme = ft.Theme(
        color_scheme_seed="#086fad",
    )
    page.theme_mode = ft.ThemeMode.SYSTEM

    chat_view = ChatView(page)
    console_view = ConsoleView(page)

    # Layout Containers
    def handle_resize(e):
        """
        ウィンドウ幅によって Row (Side-by-Side) レイアウトと
        Column (Stacked) レイアウトを切り替える．
        """
        page.clean()

        if page.width > 1000:
            # Wide mode: Side-by-side
            page.add(
                ft.Row(
                    [
                        chat_view,
                        ft.VerticalDivider(width=1, color="outlineVariant"),
                        console_view,
                    ],
                    expand=True,
                    spacing=0,
                )
            )
        else:
            # Narrow mode: Stacked
            page.add(
                ft.Column(
                    [
                        ft.Container(
                            chat_view, height=600
                        ),  # Fixed height for chat in mobile view or flex
                        ft.Divider(height=1),
                        ft.Container(console_view, expand=True),
                    ],
                    expand=True,
                    scroll=ft.ScrollMode.AUTO,
                )
            )
        page.update()

    # Initial Layout
    page.on_resized = handle_resize

    # Trigger initial layout
    handle_resize(None)

    # Update available check
    update_available, current, latest = await check_update_available()
    if update_available:
        banner = ft.Banner(
            leading=ft.Icon(ft.Icons.NEW_RELEASES),
            content=ft.Text(
                f"新しいアップデートがあります！  {current} → {latest}",
                theme_style=ft.TextThemeStyle.TITLE_MEDIUM,
            ),
            actions=[
                ft.Button(
                    "GitHubからダウンロード",
                    on_click=lambda _: webbrowser.open_new_tab(
                        f"{GITHUB_REPOSITORY_URL}/releases/latest"
                    ),
                ),
                ft.Button("今回は無視", on_click=lambda e: e.page.close(banner)),
            ],
        )
        page.open(banner)
        page.update()


ft.app(target=main, assets_dir="assets")
