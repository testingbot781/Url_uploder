import os
import asyncio
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
from threading import Thread

# CONSTANTS
OWNER_ID = 1598576202
LOG_CHANNEL = "-1003286415377"

# ENVIRONMENT VARIABLES (Render se aayengi)
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
    return "Bot is running ✅"

# Start Flask
def run_flask():
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)

# Progress Bar Helper
def progress_bar(current, total):
    percentage = (current / total) * 100
    return f"Progress: {percentage:.2f}% | {current}/{total} MB"

# START COMMAND
@bot.on_message(filters.command("start"))
async def start_cmd(client, message):
    btn = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Technical Serena", url="https://t.me/technicalSerena")]]
    )
    await message.reply_text(
        "Welcome to URL Uploader Bot 🚀",
        reply_markup=btn
    )

# HELP
@bot.on_message(filters.command("help"))
async def help_cmd(client, message):
    await message.reply_text(
        "/start - Welcome\n"
        "/help - Commands list\n"
        "/bulk - Bulk download\n"
        "/status - Check bot status\n"
    )

# STATUS
@bot.on_message(filters.command("status"))
async def status_cmd(client, message):
    await message.reply_text("Bot is online 🔥")

# BULK
@bot.on_message(filters.command("bulk"))
async def bulk_cmd(client, message):
    await message.reply_text("Send link + number of messages to download.")

# LOGGING
async def send_logs(text):
    try:
        await bot.send_message(LOG_CHANNEL, text)
    except:
        pass

# Download Simulator
async def fake_download(message):
    await send_logs("Download started...")
    for i in range(1, 6):
        await asyncio.sleep(1)
        await send_logs(progress_bar(i, 5))
    await message.reply_text("Download complete ✅")

# Handle Private Messages
@bot.on_message(filters.private & filters.text)
async def handle_private(client, message):
    await message.reply_text("Processing... ⏳")
    await fake_download(message)

# Start Pyrogram Bot
def start_bot():
    bot.run()

# MAIN
if __name__ == "__main__":
    Thread(target=run_flask).start()
    Thread(target=start_bot).start()
