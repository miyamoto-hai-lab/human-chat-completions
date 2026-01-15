import sys
import os
import flet as ft
from unittest.mock import MagicMock

# Add src to python path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from view.chat import ChatView
from view.console import ConsoleView

def verify():
    # Mock Page
    page = MagicMock(spec=ft.Page)
    page.overlay = []
    
    # Initialize Views
    chat_view = ChatView(page)
    console_view = ConsoleView(page, chat_view)
    
    print("Initialized views")

    # 1. Simulate adding a message (existing logic)
    # _add_message should add to event_log AND messages_list
    chat_view._add_message("Hello", is_user=True)
    print("Added user message")
    
    # Check event_log
    if len(chat_view.event_log) == 1 and chat_view.event_log[0]["role"] == "user":
         print("SUCCESS: Message added to event_log")
    else:
         print(f"FAILURE: Message missing from event_log: {chat_view.event_log}")

    # Check UI
    if len(chat_view.messages_list.controls) == 1:
        print("SUCCESS: Message added to messages_list")
    else:
        print("FAILURE: Message missing from messages_list")


    # 2. Simulate clicking a draft card
    draft_content = "This is a draft response."
    print("Simulating draft selection...")
    chat_view.add_draft_log(draft_content)
    
    # Check event_log
    last_log = chat_view.event_log[-1]
    if last_log["role"] == "draft" and last_log["content"] == draft_content:
        print("SUCCESS: Draft log added to event_log")
    else:
        print("FAILURE: Draft log missing or incorrect")

    # Check UI (should NOT be in messages_list)
    if len(chat_view.messages_list.controls) == 1:
        print("SUCCESS: Draft log NOT added to messages_list")
    else:
        print("FAILURE: Draft log WAS added to messages_list (it shouldn't be)")

    # 3. Simulate Export
    print("Simulating export logic...")
    conversations = console_view.chat_view.event_log.copy()
    
    print("Exported conversations:", conversations)

    # Check if both are present in order
    if len(conversations) == 2:
        if conversations[0]["role"] == "user" and conversations[1]["role"] == "draft":
            print("SUCCESS: Export sequence correct")
        else:
            print("FAILURE: Export sequence incorrect")
    else:
         print("FAILURE: Incorrect number of exported items")

if __name__ == "__main__":
    verify()
