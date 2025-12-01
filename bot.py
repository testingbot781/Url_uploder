import os
import asyncio
import threading
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ───────────────────────────────────────────────
# FIXED CONSTANTS
# ───────────────────────────────────────────────
OWNER_ID = 1598576202
LOG_CHANNEL = -1003286415377

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ───────────────────────────────────────────────
# FLASK FOR RENDER
# ───────────────────────────────────────────────
app = Flask(__name__)

@app.route("/")
def home():
    return "🔥 Bot Live — Powered by Technical Serena"

# ───────────────────────────────────────────────
# PYROGRAM BOT CLIENT
# ───────────────────────────────────────────────
bot = Client(
    "TS_SaveBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True
)

# ───────────────────────────────────────────────
# COMMANDS
# ───────────────────────────────────────────────

@bot.on_message(filters.command("start"))
async def start_cmd(_, m):
    await m.reply(
        "👋 **Welcome to Technical Serena Bot**\n"
        "Public message link bhejo, bot download karega."
    )
    await bot.send_message(LOG_CHANNEL, f"Start used by {m.from_user.id}")

@bot.on_message(filters.command("help"))
async def help_cmd(_, m):
    await m.reply("📘 Send any PUBLIC post link to download.")


# Example message downloader
@bot.on_message(filters.regex("https://t.me/"))
async def download_msg(_, m):
    try:
        link = m.text.strip()
        parts = link.split("/")
        msg_id = int(parts[-1])
        chat = parts[-2]

        temp = await m.reply("⏳ Fetching...")

        msg = await bot.get_messages(chat, msg_id)
        if not msg:
            return await temp.edit("❌ Message Not Found.")

        file_path = await msg.download()
        await m.reply_document(file_path, caption="Done ✓")

        await temp.delete()
    except Exception as e:
        await bot.send_message(LOG_CHANNEL, f"ERROR: {e}")
        await m.reply("⚠️ Failed to fetch message.")


# ───────────────────────────────────────────────
# RUN PYROGRAM AND FLASK TOGETHER
# ───────────────────────────────────────────────

def start_bot():
    asyncio.run(bot.start())
    asyncio.get_event_loop().run_forever()

if __name__ == "__main__":
    # Pyrogram in thread
    threading.Thread(target=start_bot).start()

    # Flask main
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
