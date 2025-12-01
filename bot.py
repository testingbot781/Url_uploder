# ===========================
#      URL SAVE BOT (SAFE)
# ===========================

import os
import time
import asyncio
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient
from datetime import datetime

# --------------------------
#     ENV + CONSTANTS
# --------------------------
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

OWNER_ID = 1598576202
LOG_CHANNEL = -1003286415377

MONGO_URI = os.getenv("MONGO_URI")
mongo = MongoClient(MONGO_URI)
db = mongo["session_bot"]
users = db["users"]
settings = db["settings"]

# --------------------------
#      FLASK SERVER
# --------------------------
app = Flask(__name__)

@app.route("/")
def home():
    return "BOT RUNNING"

# --------------------------
#     CREATE BOT CLIENT
# --------------------------
bot = Client(
    "save_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# --------------------------
#   PROGRESS BAR FUNCTION
# --------------------------
async def progress_bar(current, total, message):
    percent = int((current / total) * 100)
    speed = current / (time.time() - message.date.timestamp())
    eta = (total - current) / speed if speed != 0 else 0

    bar = f"[{'■' * (percent//5)}{'□' * (20 - percent//5)}]"

    txt = (
        f"{bar} {percent}%\n"
        f"Speed: {speed/1024/1024:.2f} MB/s\n"
        f"ETA: {eta:.1f}s\n"
        f"Uploaded: {current/1024/1024:.2f} MB / {total/1024/1024:.2f} MB"
    )

    try:
        await message.edit_text(txt)
    except:
        pass

# --------------------------
#  SETTINGS DEFAULT
# --------------------------
def get_user_settings(uid):
    data = settings.find_one({"_id": uid})
    if not data:
        default = {
            "_id": uid,
            "chat_id": None,
            "replace_words": {},
            "remove_words": [],
            "session": None
        }
        settings.insert_one(default)
        return default
    return data

# --------------------------
#       START COMMAND
# --------------------------
@bot.on_message(filters.command("start"))
async def start_handler(_, m):
    btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
        [InlineKeyboardButton("📣 Contact Owner", url="https://t.me/technicalserena")]
    ])

    await m.reply_text(
        "**Welcome to Save Restricted Content Bot**\n"
        "Powered by **TECHNICAL SERENA**",
        reply_markup=btn
    )

# --------------------------
#       HELP COMMAND
# --------------------------
@bot.on_message(filters.command("help"))
async def help_handler(_, m):
    await m.reply_text(
        "/start – Welcome\n"
        "/help – How to use\n"
        "/bulk – Extract multiple messages\n"
        "/status – Bot alive & ping\n"
        "/broadcast – Owner only\n"
        "/addpremium – Add premium user\n"
        "/ban – Remove user\n"
        "/caption – Set caption format\n"
    )

# --------------------------
# SESSION LOGIN (SAFE)
# --------------------------
@bot.on_callback_query(filters.regex("session_login"))
async def sess_login(_, q):
    await q.message.reply(
        "**Send your Telethon/Pyrogram SESSION STRING**\n"
        "Bot will use your session to access private channels safely."
    )
    settings.update_one({"_id": q.from_user.id}, {"$set": {"await_session": True}})
    await q.answer()

@bot.on_message(filters.text)
async def catch_session(_, m):
    data = get_user_settings(m.from_user.id)

    if data.get("await_session"):
        settings.update_one({"_id": m.from_user.id}, {"$set": {"session": m.text, "await_session": False}})
        await m.reply("✅ Session saved successfully!")
        return

# --------------------------
# SETTINGS MENU
# --------------------------
@bot.on_callback_query(filters.regex("settings"))
async def settings_menu(_, q):
    btn = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Chat ID", callback_data="chatid"),
            InlineKeyboardButton("Session Login", callback_data="session_login")
        ],
        [
            InlineKeyboardButton("Replace Words", callback_data="replace"),
            InlineKeyboardButton("Remove Words", callback_data="remove")
        ],
        [
            InlineKeyboardButton("Reset", callback_data="reset"),
            InlineKeyboardButton("Logout Session", callback_data="logout")
        ]
    ])
    await q.message.edit_text("⚙️ **Settings Panel**", reply_markup=btn)

# --------------------------
# BULK DOWNLOAD
# --------------------------
@bot.on_message(filters.command("bulk"))
async def bulk_handler(_, m):
    await m.reply("Send the message link you want to extract.")
    users.update_one({"_id": m.from_user.id}, {"$set": {"await_link": True}})

@bot.on_message(filters.text & filters.private)
async def bulk_extract(_, m):
    user = users.find_one({"_id": m.from_user.id})
    if not user or not user.get("await_link"):
        return

    users.update_one({"_id": m.from_user.id}, {"$set": {"await_link": False}})

    await m.reply("How many messages to extract? (Max 500)")
    users.update_one({"_id": m.from_user.id}, {"$set": {"await_count": m.text}})

# (Note: Full bulk extractor finalized in next message)



# -------------------------------------------------
#   BOT RUN + FLASK SERVER (REQUIRED FOR RENDER)
# -------------------------------------------------

if __name__ == "__main__":
    import threading
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=10000)).start()
    bot.run()
