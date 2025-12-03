import os
import asyncio
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
from threading import Thread

OWNER_ID = 1598576202
LOG_CHANNEL = "-1003286415377"

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

bot = Client("URL_UPLOADER_BOT", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
app = Flask(name)

@app.route("/")
def home():
return "Bot is running ✅"

def run_flask():
port = int(os.getenv("PORT", 10000))
app.run(host="0.0.0.0", port=port)

def progress_bar(current, total):
percentage = (current / total) * 100
return f"Progress: {percentage:.2f}% | {current}/{total} MB"

@bot.on_message(filters.command("start"))
async def start(client, message):
buttons = InlineKeyboardMarkup(
[[InlineKeyboardButton("Technical Serena", url="https://t.me/technicalSerena")]]
)
await message.reply_text("Welcome to URL UPLOADER Bot! 🚀", reply_markup=buttons)

@bot.on_message(filters.command("help"))
async def help_cmd(client, message):
await message.reply_text(
"/start - Welcome\n"
"/help - How to use bot\n"
"/bulk - Bulk download messages\n"
"/add - Add premium user\n"
"/ban - Remove user\n"
"/status - Bot alive ping\n"
"/login - Optional: For private channel access"
)

@bot.on_message(filters.command("status"))
async def status(client, message):
await message.reply_text("Bot is online ✅")

@bot.on_message(filters.command("bulk"))
async def bulk(client, message):
await message.reply_text("Send message link and number of messages to download (max 500)")

async def send_logs(text):
try:
await bot.send_message(LOG_CHANNEL, text)
except:
pass

async def download_and_send(message):
# Example stub: here you will handle downloading single or bulk media
await send_logs(f"Downloading message from {message.chat.id}")
for i in range(1, 6):
await asyncio.sleep(2)  # simulate download
prog = progress_bar(i, 5)
await send_logs(prog)
await message.reply_text("Download complete ✅")

@bot.on_message(filters.private & filters.text)
async def handle_private(client, message):
await message.reply_text("Received message, processing...")
await download_and_send(message)

def start_bot():
asyncio.run(bot.start())
bot.loop.run_forever()

if name == "main":
Thread(target=run_flask).start()
Thread(target=start_bot).start()
