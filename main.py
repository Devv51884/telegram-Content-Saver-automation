import os
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

FORCE_SUB = os.getenv("FORCE_SUB", "").strip()
JOIN_LINK = os.getenv("JOIN_LINK", "").strip()

APP_NAME = "Code Devil Restricted Saver"

app = Client(
    "code_devil_v1_test",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True,
)


async def check_force_sub(client, message):
    if not FORCE_SUB:
        return False

    try:
        member = await client.get_chat_member(FORCE_SUB, message.from_user.id)
        return False
    except Exception:
        buttons = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔒 Join Required Channel", url=JOIN_LINK)]]
        )
        await message.reply_text(
            "Bot use karne ke liye pehle required channel join karo, phir /start bhejo.",
            reply_markup=buttons
        )
        return True


@app.on_message(filters.private)
async def catch_all(client, message):
    print("MESSAGE RECEIVED =>", repr(message.text))

    text = (message.text or "").strip().lower()

    if text.startswith("/ping"):
        await message.reply_text("✅ Bot online hai aur reply kar raha hai.")
        return

    if text.startswith("/start"):
        blocked = await check_force_sub(client, message)
        if blocked:
            return

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Channel", url="https://t.me/Code_Devil")],
            [InlineKeyboardButton("🛠 Updates", url="https://t.me/Devil_Developee")],
            [InlineKeyboardButton("▶️ YouTube", url="https://www.youtube.com/@Code_Devil")],
        ])

        await message.reply_text(
            f"👋 Welcome to {APP_NAME}\n\n"
            "Bot ab working hai.\n\n"
            "Commands:\n"
            "/start\n"
            "/ping\n"
            "/help\n"
            "/plan\n"
            "/terms",
            reply_markup=buttons
        )
        return

    if text.startswith("/help"):
        await message.reply_text(
            "📘 Help Guide\n\n"
            "/start - bot start karo\n"
            "/ping - bot status check\n"
            "/plan - roadmap dekho\n"
            "/terms - rules dekho"
        )
        return

    if text.startswith("/plan"):
        await message.reply_text(
            "🛣️ V1 abhi base working bot hai.\n"
            "Next versions me settings, login, batch, admin panel add hoga."
        )
        return

    if text.startswith("/terms"):
        await message.reply_text(
            "📜 Rules:\n"
            "Bot responsibly use karo.\n"
            "Required channel join compulsory ho sakta hai."
        )
        return

    await message.reply_text(
        "Mujhe command bhejo:\n/start\n/ping\n/help"
    )


if __name__ == "__main__":
    print("Starting Code Devil single-file test bot...")
    app.run()