import flet as ft

def main(page: ft.Page):
    lv = ft.ListView(expand=True, spacing=20, padding=20)
    page.add(lv)

    lv.controls.append(ft.Container(content=ft.Text("Message 1"), bgcolor="blue"))
    
    # Hidden item
    lv.controls.append(ft.Container(content=ft.Text("Hidden"), visible=False, bgcolor="red"))
    
    lv.controls.append(ft.Container(content=ft.Text("Message 2"), bgcolor="blue"))
    
    page.update()

ft.app(target=main)
