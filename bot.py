import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
from threading import Thread

# CONSTANTS
OWNER_ID = 1598576202
LOG_CHANNEL = "-1003286415377"

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# PYROGRAM BOT
bot = Client(
    "URL_UPLOADER_BOT",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# FLASK SERVER
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot running on Render ✅"

def run_flask():
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)

# BACKGROUND TASK (LOGS)
async def send_logs(text):
    try:
        await bot.send_message(LOG_CHANNEL, text)
    except:
        pass

# PROGRESS
def progress_bar(c, t):
    p = (c / t) * 100
    return f"{p:.2f}% | {c}/{t} MB"

# COMMANDS
@bot.on_message(filters.command("start"))
async def start_cmd(client, message):
    btn = InlineKeyboardMarkup([[InlineKeyboardButton("Channel", url="https://t.me/technicalSerena")]])
    await message.reply_text("Welcome to URL Uploader Bot 🚀", reply_markup=btn)

@bot.on_message(filters.command("help"))
async def help_cmd(client, message):
    await message.reply_text("/start\n/help\n/status\n/bulk")

@bot.on_message(filters.command("status"))
async def status_cmd(client, message):
    await message.reply_text("Bot is active 🔥")

@bot.on_message(filters.private & filters.text)
async def handle(client, message):
    await message.reply_text("Processing your request… ⏳")
    await send_logs("Download started")
    for i in range(1, 6):
        await asyncio.sleep(1)
        await send_logs(progress_bar(i, 5))
    await message.reply_text("Completed ✅")

# MAIN ASYNC RUNNER
async def main():
    # Start Flask in background
    Thread(target=run_flask).start()

    # Start Pyrogram properly with asyncio
    await bot.start()
    print("Bot Started Successfully")

    # Keep bot alive
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
