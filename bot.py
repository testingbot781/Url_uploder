import os
import time
import asyncio
import logging
from threading import Thread
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from motor.motor_asyncio import AsyncIOMotorClient
from flask import Flask

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
OWNER_ID = 1598576202
LOG_CHANNEL = -1003286415377
MONGO_URI = os.getenv("MONGO_URI")

logging.basicConfig(level=logging.INFO)

mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client["botdb"]
premium_collection = db["premium_users"]

app = Flask(name)

@app.route("/")
def home():
return "Bot is running ✅"

def run_web():
port = int(os.getenv("PORT", 10000))
app.run(host="0.0.0.0", port=port)

bot = Client("url_uploader_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

def progress_bar(current, total, start_time):
now = time.time()
elapsed = now - start_time
speed = current / elapsed if elapsed > 0 else 0
remaining = total - current
eta = remaining / speed if speed > 0 else 0
return f"Progress: {current}/{total} MB\nSpeed: {speed:.2f} MB/s\nETA: {int(eta)}s"

@bot.on_message(filters.command("start"))
async def start_cmd(c: Client, m: Message):
buttons = InlineKeyboardMarkup([[InlineKeyboardButton("💻 TECHNICAL SERENA", url="https://t.me/technicalSerena")]])
await m.reply("Welcome to URL UPLOADER Bot!", reply_markup=buttons)

@bot.on_message(filters.command("help"))
async def help_cmd(c: Client, m: Message):
text = """
/start - Welcome
/help - Commands info
/add_premium <user_id> - Add premium
/ban <user_id> - Remove user
/bulk - Bulk message download
/login - Optional session login
/status - Bot alive
"""
await m.reply(text)

@bot.on_message(filters.command("add_premium"))
async def add_premium(c: Client, m: Message):
if m.from_user.id != OWNER_ID:
return
if len(m.command) != 2:
await m.reply("Usage: /add_premium <user_id>")
return
user_id = int(m.command[1])
await premium_collection.update_one({"user_id": user_id}, {"$set": {"premium": True}}, upsert=True)
await m.reply(f"User {user_id} added as premium ✅")

@bot.on_message(filters.command("ban"))
async def ban_user(c: Client, m: Message):
if m.from_user.id != OWNER_ID:
return
if len(m.command) != 2:
await m.reply("Usage: /ban <user_id>")
return
user_id = int(m.command[1])
await premium_collection.delete_one({"user_id": user_id})
await m.reply(f"User {user_id} banned ❌")

@bot.on_message(filters.command("status"))
async def status(c: Client, m: Message):
await m.reply("Bot is alive and running ✅")

@bot.on_message(filters.command("login"))
async def login_cmd(c: Client, m: Message):
await m.reply("Login optional: only needed for private channel access.")

@bot.on_message(filters.command("bulk"))
async def bulk_download(c: Client, m: Message):
await m.reply("Bulk download starting...")
total_messages = 500  # example limit
start_time = time.time()
for i in range(1, total_messages + 1):
# simulate download
await asyncio.sleep(0.5)
prog = progress_bar(i, total_messages, start_time)
await m.reply(prog)
await m.reply("Bulk download completed ✅")

def start_bot():
bot.run()

if name == "main":
Thread(target=run_web).start()
Thread(target=start_bot).start()
