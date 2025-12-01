import os
import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import FastAPI
import uvicorn
from threading import Thread
import time

---------- ENV VARIABLES ----------

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
OWNER_ID = 1598576202
LOG_CHANNEL = -1003286415377
MONGO_URI = os.getenv("MONGO_URI")

---------- Logging ----------

logging.basicConfig(level=logging.INFO)

---------- Mongo ----------

mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client["botdb"]
premium_collection = db["premium_users"]

---------- FastAPI ----------

app = FastAPI()

@app.get("/")
async def root():
return {"status": "Bot is running ✅"}

def run_web():
uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))

---------- Pyrogram Client ----------

bot = Client("url_uploader_bot",
bot_token=BOT_TOKEN,
api_id=API_ID,
api_hash=API_HASH)

---------- Bot Commands ----------

@bot.on_message(filters.command("start"))
async def start_cmd(c: Client, m: Message):
buttons = InlineKeyboardMarkup(
[[InlineKeyboardButton("💻 TECHNICAL SERENA", url="https://t.me/technicalSerena")]]
)
await m.reply("Welcome to URL UPLOADER Bot!", reply_markup=buttons)

@bot.on_message(filters.command("help"))
async def help_cmd(c: Client, m: Message):
text = """
Commands available:

/start - Welcome message
/help - This message
/add_premium <user_id> - Add premium user
/ban <user_id> - Ban user
/bulk - Bulk message download
/login - Optional session login
/status - Bot alive ping
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

@bot.on_message(filters.command("bulk"))
async def bulk_download(c: Client, m: Message):
await m.reply("Bulk download feature is in progress...")

@bot.on_message(filters.command("login"))
async def login_cmd(c: Client, m: Message):
await m.reply("Login is optional and only for private channel access.")

---------- Run Bot ----------

def start_bot():
bot.run()

if name == "main":
Thread(target=run_web).start()
Thread(target=start_bot).start()
