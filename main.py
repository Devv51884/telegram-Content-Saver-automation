import threading
from pyrogram import idle

from bot import app
from app import run_web, set_runtime_state


def start_bot():
    print("🤖 Starting Code Devil Bot...")
    app.start()

    me = app.get_me()
    username = me.username if me else "unknown"

    print(f"✅ Bot Started as @{username}")
    set_runtime_state(True, username)

    idle()
    app.stop()


def start_web():
    run_web()


if __name__ == "__main__":
    print("🚀 Starting Code Devil Restricted Saver V9...")

    web_thread = threading.Thread(target=start_web, daemon=True)
    web_thread.start()

    start_bot()