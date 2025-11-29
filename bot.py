import os
import time
import math
import asyncio
import requests
import traceback
from pymongo import MongoClient
from flask import Flask
from threading import Thread
from pyrogram import Client, filters
from pyrogram.types import Message

# --------------------------
#        ENV VARIABLES
# --------------------------
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
FORCE_SUB = os.getenv("FORCE_SUB")  # channel username
OWNER_ID = int(os.getenv("OWNER_ID"))
LOG_CHANNEL = int(os.getenv("LOG_CHANNEL"))
MONGO_URI = os.getenv("MONGO_URI")

# --------------------------
#      MONGODB CONNECT
# --------------------------
mongo = MongoClient(MONGO_URI)
db = mongo["tg_bot"]
users_col = db["users"]
ban_col = db["banned"]
caption_col = db["caption"]

# --------------------------
#         FLASK
# --------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Running Successfully!"

def run_flask():
    app.run(host="0.0.0.0", port=10000)

Thread(target=run_flask).start()

# --------------------------
#   BOT CLIENT START
# --------------------------
bot = Client(
    "DownloaderBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)


# --------------------------
#   PROGRESS BAR FUNCTION
# --------------------------
async def progress_bar(current, total, message: Message, start_time):
    now = time.time()
    diff = now - start_time
    if diff == 0:
        diff = 1

    percentage = current * 100 / total
    speed = current / diff
    eta = int((total - current) / speed)

    bar_length = 20
    filled = int(bar_length * percentage / 100)
    bar = "█" * filled + "░" * (bar_length - filled)

    text = (
        f"**Uploading…**\n"
        f"{bar} `{percentage:.1f}%`\n"
        f"**Speed:** {speed/1024/1024:.2f} MB/s\n"
        f"**Uploaded:** {current/1024/1024:.2f} MB / {total/1024/1024:.2f} MB\n"
        f"**ETA:** {eta}s"
    )

    try:
        await message.edit(text)
    except:
        pass


# --------------------------
#   STREAMABLE / DIRECT DL
# --------------------------
def download_file(url, file_path):
    r = requests.get(url, stream=True)
    total = int(r.headers.get("content-length", 0))

    with open(file_path, "wb") as f:
        downloaded = 0
        for chunk in r.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
    return file_path


# --------------------------
#        FORCE SUB
# --------------------------
async def check_force(chat_id):
    try:
        member = await bot.get_chat_member(FORCE_SUB, chat_id)
        return member.status not in ["kicked", "left"]
    except:
        return False


# --------------------------
#         COMMANDS
# --------------------------

@bot.on_message(filters.command("start"))
async def start(_, m: Message):
    user_id = m.from_user.id

    if ban_col.find_one({"user_id": user_id}):
        return await m.reply("❌ You are banned from using this bot.")

    if not await check_force(user_id):
        return await m.reply(
            f"⚠ Join @{FORCE_SUB} to use this bot."
        )

    if not users_col.find_one({"user_id": user_id}):
        users_col.insert_one({"user_id": user_id})

    await bot.send_message(LOG_CHANNEL, f"✅ New User → {user_id}")

    await m.reply("Welcome! Send Streamable or direct link.")


@bot.on_message(filters.command("add"))
async def add_user(_, m: Message):
    if m.from_user.id != OWNER_ID:
        return

    try:
        uid = int(m.text.split(" ")[1])
        ban_col.delete_one({"user_id": uid})
        users_col.insert_one({"user_id": uid})
        await m.reply(f"✅ User {uid} added.")
    except:
        await m.reply("❌ Invalid user id.")


@bot.on_message(filters.command("remove"))
async def remove_user(_, m: Message):
    if m.from_user.id != OWNER_ID:
        return

    try:
        uid = int(m.text.split(" ")[1])
        ban_col.insert_one({"user_id": uid})
        await m.reply(f"❌ User {uid} banned.")
    except:
        await m.reply("❌ Invalid user id.")


@bot.on_message(filters.command("caption"))
async def set_caption(_, m: Message):
    user_id = m.from_user.id

    if user_id != OWNER_ID:
        return await m.reply("❌ Only owner can set caption.")

    text = m.text.split(" ", 1)[1]
    caption_col.update_one({}, {"$set": {"text": text}}, upsert=True)
    await m.reply("✅ Caption updated.")


@bot.on_message(filters.command("users"))
async def users_list(_, m):
    if m.from_user.id != OWNER_ID:
        return
    total = users_col.count_documents({})
    await m.reply(f"Total Users: {total}")


@bot.on_message(filters.command("banned"))
async def banned_list(_, m):
    if m.from_user.id != OWNER_ID:
        return
    total = ban_col.count_documents({})
    await m.reply(f"Banned Users: {total}")


# --------------------------
#   MAIN DOWNLOAD HANDLER
# --------------------------
@bot.on_message(filters.text & ~filters.command([]))
async def process_link(_, m: Message):
    user_id = m.from_user.id

    if ban_col.find_one({"user_id": user_id}):
        return await m.reply("❌ You are banned.")

    if not await check_force(user_id):
        return await m.reply(
            f"⚠ Join @{FORCE_SUB} to use this bot."
        )

    url = m.text.strip()
    msg = await m.reply("🔄 Processing…")

    try:
        file_path = f"{user_id}_video.mp4"
        download_file(url, file_path)

        caption_doc = caption_col.find_one({})
        cap = caption_doc["text"] if caption_doc else ""

        start_t = time.time()

        await bot.send_video(
            m.chat.id,
            video=file_path,
            caption=cap,
            progress=progress_bar,
            progress_args=(msg, start_t)
        )

        os.remove(file_path)
        await msg.delete()

        await bot.send_message(LOG_CHANNEL, f"🎬 Uploaded for {user_id}")

    except Exception as e:
        await msg.edit(f"❌ Error:\n{e}")
        traceback.print_exc()


bot.run()
