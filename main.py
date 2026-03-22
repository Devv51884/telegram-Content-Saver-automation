import os
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

FORCE_SUB = os.getenv("FORCE_SUB", "").strip()
JOIN_LINK = os.getenv("JOIN_LINK", "").strip()

APP_NAME = "Code Devil Restricted Saver"
MAIN_CHANNEL = "https://t.me/Code_Devil"
UPDATES_CHANNEL = "https://t.me/Devil_Developee"
PLAYLIST_LINK = "https://t.me/addlist/wTBxgyESacMwMDA1"
WHATSAPP_CHANNEL = "https://whatsapp.com/channel/0029VaacxeOKWEKsD2KdqR0U"
YOUTUBE_CHANNEL = "https://www.youtube.com/@Code_Devil"

app = Client(
    "code_devil_v1",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True,
)


async def check_force_sub(client, message):
    if not FORCE_SUB:
        return False

    try:
        await client.get_chat_member(FORCE_SUB, message.from_user.id)
        return False
    except UserNotParticipant:
        buttons = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🔒 Pehle Channel Join Karo", url=JOIN_LINK or MAIN_CHANNEL)],
                [InlineKeyboardButton("✅ Join Kar Liya", callback_data="check_join_again")]
            ]
        )
        await message.reply_text(
            "❌ Bot use karne ke liye pehle required Telegram channel join karna zaroori hai.\n\n"
            "Channel join karne ke baad dubara /start bhejo.",
            reply_markup=buttons
        )
        return True
    except Exception as e:
        await message.reply_text(
            f"⚠️ Join check me issue aa gaya:\n{e}\n\n/start dubara bhejo."
        )
        return True


@app.on_callback_query(filters.regex("check_join_again"))
async def check_join_again(client, callback_query):
    try:
        blocked = await check_force_sub(client, callback_query.message)
        if not blocked:
            await callback_query.message.reply_text(
                "✅ Join verify ho gaya.\nAb /start bhejo aur bot use karo."
            )
        await callback_query.answer()
    except Exception:
        await callback_query.answer("Phir se /start bhejo.", show_alert=True)


@app.on_message(filters.private)
async def catch_all(client, message):
    print("MESSAGE RECEIVED =>", repr(message.text))

    text = (message.text or "").strip().lower()

    if text.startswith("/ping"):
        await message.reply_text("✅ Bot online hai aur sahi se reply kar raha hai.")
        return

    if text.startswith("/start"):
        blocked = await check_force_sub(client, message)
        if blocked:
            return

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Main Channel", url=MAIN_CHANNEL),
             InlineKeyboardButton("🛠 Updates", url=UPDATES_CHANNEL)],
            [InlineKeyboardButton("📚 Playlist", url=PLAYLIST_LINK),
             InlineKeyboardButton("▶️ YouTube", url=YOUTUBE_CHANNEL)],
            [InlineKeyboardButton("💬 WhatsApp", url=WHATSAPP_CHANNEL)],
        ])

        await message.reply_text(
            f"👋 Welcome to **{APP_NAME}**\n\n"
            "Ye Code Devil ka official restricted saver base bot hai.\n\n"
            "**Available Commands:**\n"
            "/start - Bot start karo\n"
            "/ping - Bot status check karo\n"
            "/help - Help guide dekho\n"
            "/plan - Future roadmap dekho\n"
            "/terms - Rules aur usage terms dekho\n\n"
            "Abhi ye V1 working base hai. Next versions me aur powerful features aayenge.",
            reply_markup=buttons,
            disable_web_page_preview=True
        )
        return

    if text.startswith("/help"):
        blocked = await check_force_sub(client, message)
        if blocked:
            return

        await message.reply_text(
            "📘 **Help Guide (Hinglish)**\n\n"
            "/start - Bot start karne ke liye\n"
            "/ping - Check karo bot online hai ya nahi\n"
            "/help - Ye help guide dekhne ke liye\n"
            "/plan - Aage ke versions me kya aayega dekhne ke liye\n"
            "/terms - Bot ke rules dekhne ke liye\n\n"
            "Agar bot ka reply na aaye to pehle check karo ki tumne required channel join kiya hai ya nahi."
        )
        return

    if text.startswith("/plan"):
        blocked = await check_force_sub(client, message)
        if blocked:
            return

        await message.reply_text(
            "🛣️ **Code Devil Bot Roadmap**\n\n"
            "✅ V1 - Working base bot\n"
            "🔜 V2 - Settings panel\n"
            "🔜 V3 - Admin controls\n"
            "🔜 V4 - Login/session system\n"
            "🔜 V5 - Batch processing\n"
            "🔜 V6 - Premium + advanced tools\n\n"
            "Hum step-by-step build karenge taki bot stable rahe."
        )
        return

    if text.startswith("/terms"):
        blocked = await check_force_sub(client, message)
        if blocked:
            return

        await message.reply_text(
            "📜 **Terms / Rules**\n\n"
            "1. Bot responsibly use karo.\n"
            "2. Required channel join compulsory ho sakta hai.\n"
            "3. Spam ya abuse mat karo.\n"
            "4. Future versions me usage limits add ho sakti hain.\n"
            "5. Code Devil community updates ke liye channels join rakho."
        )
        return

    blocked = await check_force_sub(client, message)
    if blocked:
        return

    await message.reply_text(
        "🤖 Mujhe ye commands bhejo:\n\n"
        "/start\n"
        "/ping\n"
        "/help\n"
        "/plan\n"
        "/terms"
    )


if __name__ == "__main__":
    print("Starting Code Devil Restricted Saver V1...")
    app.run()