import os
import time
import asyncio
from threading import Thread
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient

# =============================================================
# BASIC FIXED CONFIG
# =============================================================

OWNER_ID = 1598576202
LOG_CHANNEL = -1003286415377

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URL = os.getenv("MONGO_URL")  # You will fill on Render

# =============================================================
# FLASK KEEP-ALIVE
# =============================================================

app = Flask(__name__)

@app.route("/")
def home():
    return "Technical Serena - URL Uploader Bot Running"


# =============================================================
# TELEGRAM BOT
# =============================================================

bot = Client(
    "TECHNICAL_SERENA_URL_UPLOADER",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

# =============================================================
# MONGO DB SETUP
# =============================================================

mongo = MongoClient(MONGO_URL)
db = mongo["SERENA_UPLOADER"]

users_db = db["users"]
settings_db = db["settings"]
stats_db = db["stats"]


# =============================================================
# MONGO HELPERS
# =============================================================

def add_user(uid):
    if not users_db.find_one({"_id": uid}):
        users_db.insert_one({"_id": uid, "premium": False})


def authorize(uid):
    return users_db.find_one({"_id": uid, "premium": True})


def ban_user(uid):
    users_db.update_one({"_id": uid}, {"$set": {"banned": True}}, upsert=True)


def is_banned(uid):
    data = users_db.find_one({"_id": uid})
    return data and data.get("banned") is True


def set_caption(uid, caption):
    settings_db.update_one({"_id": uid}, {"$set": {"caption": caption}}, upsert=True)


def get_caption(uid):
    data = settings_db.find_one({"_id": uid})
    return data.get("caption") if data else None


def reset_settings(uid):
    settings_db.delete_one({"_id": uid})


# =============================================================
# CHECK AUTH
# =============================================================

async def check_permission(message):
    uid = message.from_user.id

    if uid == OWNER_ID:
        return True

    if is_banned(uid):
        await message.reply("⛔ You are banned from using this bot.")
        return False

    if not authorize(uid):
        await message.reply("❌ Access Denied.\nAsk Admin for Premium Access.")
        return False

    return True


# =============================================================
# START
# =============================================================

@bot.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    add_user(message.from_user.id)

    await message.reply(
        f"👋 Welcome to **URL UPLOADER BOT**\nBrand: **TECHNICAL SERENA**\n"
        f"Use /help to see commands."
    )

    try:
        await bot.send_message(
            LOG_CHANNEL,
            f"NEW USER STARTED:\nName: {message.from_user.first_name}\nID: `{message.from_user.id}`"
        )
    except:
        pass


# =============================================================
# HELP
# =============================================================

@bot.on_message(filters.command("help"))
async def help_cmd(client, message):
    await message.reply(
        "**User Commands:**\n"
        "/start – Check bot alive\n"
        "/help – Commands list\n"
        "/ping – Bot latency\n"
        "/id – Show your Telegram ID\n"
        "/caption <text> – Auto numbered captions\n"
        "/bulk – Bulk Downloader\n\n"
        "**Settings:**\n"
        "/settings – Replace, Remove Words, Reset\n\n"
        "**Admin:**\n"
        "/add <user_id> – Give premium access\n"
        "/remove <user_id> – Ban user"
    )


# =============================================================
# ADMIN — ADD PREMIUM USER
# =============================================================

@bot.on_message(filters.command("add"))
async def add_premium(client, message):
    if message.from_user.id != OWNER_ID:
        return await message.reply("❌ Only owner can use this.")

    if len(message.command) < 2:
        return await message.reply("Usage: /add <user_id>")

    uid = int(message.command[1])
    users_db.update_one({"_id": uid}, {"$set": {"premium": True}}, upsert=True)

    await message.reply(f"✅ `{uid}` is now PREMIUM user.")
    await bot.send_message(LOG_CHANNEL, f"PREMIUM ADDED: `{uid}`")


# =============================================================
# ADMIN — REMOVE / BAN USER
# =============================================================

@bot.on_message(filters.command("remove"))
async def remove_user(client, message):
    if message.from_user.id != OWNER_ID:
        return await message.reply("❌ Only owner can use this.")

    if len(message.command) < 2:
        return await message.reply("Usage: /remove <user_id>")

    uid = int(message.command[1])
    ban_user(uid)

    await message.reply(f"⛔ `{uid}` is banned.")
    await bot.send_message(LOG_CHANNEL, f"BANNED: `{uid}`")


# =============================================================
# CAPTION GENERATOR
# =============================================================

@bot.on_message(filters.command("caption"))
async def caption_cmd(client, message):
    if not await check_permission(message):
        return

    if len(message.command) < 2:
        return await message.reply("Usage: /caption <text>")

    text = " ".join(message.command[1:])

    result = ""
    for i in range(1, 51):  # 001–050
        result += f"{i:03d} - {text}\n"

    await message.reply(result)


# =============================================================
# SETTINGS MENU
# =============================================================

@bot.on_message(filters.command("settings"))
async def settings_cmd(client, message):
    if not await check_permission(message):
        return

    btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("Replace Word", callback_data="replace_word")],
        [InlineKeyboardButton("Remove Word", callback_data="remove_word")],
        [InlineKeyboardButton("Reset Settings", callback_data="reset_settings")],
        [InlineKeyboardButton("Stats", callback_data="stats")]
    ])

    await message.reply("⚙ **Settings Menu:**", reply_markup=btn)


# =============================================================
# CALLBACK HANDLERS
# =============================================================

@bot.on_callback_query()
async def cb_handler(client, query):
    uid = query.from_user.id

    if query.data == "reset_settings":
        reset_settings(uid)
        return await query.message.edit("🔄 Settings Reset Successfully.")

    if query.data == "stats":
        total_users = users_db.count_documents({})
        banned = users_db.count_documents({"banned": True})
        premium = users_db.count_documents({"premium": True})

        await query.message.edit(
            f"📊 **Bot Stats**\n\n"
            f"Total Users: {total_users}\n"
            f"Premium Users: {premium}\n"
            f"Banned: {banned}"
        )


# =============================================================
# BULK DOWNLOAD COMMAND (NEXT UPGRADE FRAMEWORK)
# =============================================================

@bot.on_message(filters.command("bulk"))
async def bulk_cmd(client, message):
    if not await check_permission(message):
        return

    await message.reply(
        "📥 **Bulk Mode Activated**\n"
        "Send multiple URLs line-by-line.\n"
        "When done, send `/done`."
    )


# =============================================================
# RUN BOT + FLASK
# =============================================================

if __name__ == "__main__":
    Thread(
        target=lambda: app.run(
            host="0.0.0.0",
            port=int(os.getenv("PORT", 10000)),
            debug=False
        )
    ).start()

    bot.run()
