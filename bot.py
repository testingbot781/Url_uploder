import os
import time
from threading import Thread
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import Message

# ============================================
# *********  BASIC CONFIG  *********
# ============================================

OWNER_ID = 1598576202
LOG_CHANNEL = -1003286415377   # Your Log Channel Fixed

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ============================================
# *********  FLASK KEEPALIVE  *********
# ============================================

app = Flask(__name__)

@app.route("/")
def home():
    return "Technical Serena URL Uploader Bot is Running!"

# ============================================
# *********  BOT CLIENT  *********
# ============================================

bot = Client(
    "TechnicalSerena_UrlUploader",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=50,
    in_memory=True
)

# ============================================
# *********  LOAD LOCAL USER LISTS  *********
# ============================================

def load_list(file):
    if not os.path.exists(file):
        open(file, "w").close()
    with open(file, "r") as f:
        return set(line.strip() for line in f if line.strip())

def save_list(file, data):
    with open(file, "w") as f:
        for x in data:
            f.write(f"{x}\n")

allowed_users = load_list("allowed_users.txt")
banned_users = load_list("banned_users.txt")

# ============================================
# *********  CHECK USER PERMISSION  *********
# ============================================

async def check_user(message: Message):
    uid = str(message.from_user.id)

    if uid in banned_users:
        await message.reply("❌ You are banned from using this bot.")
        return False

    if uid not in allowed_users and message.from_user.id != OWNER_ID:
        await message.reply("⛔ You are not authorized.\nAsk Admin for access.")
        return False

    return True


# ============================================
# *********  START COMMAND  *********
# ============================================

@bot.on_message(filters.command("start"))
async def start_cmd(client, message):
    await message.reply(
        f"👋 Welcome to **URL UPLOADER BOT**\nBrand: **TECHNICAL SERENA**\n"
        f"Use /help to see available commands."
    )

    # Log
    try:
        await bot.send_message(
            LOG_CHANNEL,
            f"🆕 New User Started Bot\n\n"
            f"Name: {message.from_user.first_name}\n"
            f"User ID: `{message.from_user.id}`"
        )
    except:
        pass


# ============================================
# *********  HELP COMMAND  *********
# ============================================

@bot.on_message(filters.command("help"))
async def help_cmd(client, message):
    if not await check_user(message):
        return

    await message.reply(
        "**Commands List:**\n"
        "/start - Start Bot\n"
        "/help - Show this message\n"
        "/ping - Check speed\n"
        "/id - Show your ID\n"
        "/caption <text> - Auto numbered captions\n\n"
        "**Admin:**\n"
        "/add <user_id>\n"
        "/remove <user_id>"
    )


# ============================================
# *********  PING COMMAND  *********
# ============================================

@bot.on_message(filters.command("ping"))
async def ping_cmd(client, message):
    if not await check_user(message):
        return

    t1 = time.time()
    m = await message.reply("⏳ Pinging...")
    t2 = time.time()
    await m.edit(f"🏓 Pong: `{int((t2 - t1) * 1000)} ms`")


# ============================================
# *********  ID COMMAND  *********
# ============================================

@bot.on_message(filters.command("id"))
async def id_cmd(client, message):
    await message.reply(f"Your Telegram ID: `{message.from_user.id}`")


# ============================================
# *********  ADD USER COMMAND  *********
# ============================================

@bot.on_message(filters.command("add"))
async def add_user(client, message):
    if message.from_user.id != OWNER_ID:
        return await message.reply("❌ Only owner can add users.")

    if len(message.command) < 2:
        return await message.reply("Usage: /add <user_id>")

    uid = message.command[1]
    allowed_users.add(uid)
    save_list("allowed_users.txt", allowed_users)

    await message.reply(f"✅ User `{uid}` added successfully.")

    # Log
    await bot.send_message(
        LOG_CHANNEL,
        f"➕ **User Added**\nAdded ID: `{uid}`"
    )


# ============================================
# *********  REMOVE / BAN USER  *********
# ============================================

@bot.on_message(filters.command("remove"))
async def remove_user(client, message):
    if message.from_user.id != OWNER_ID:
        return await message.reply("❌ Only owner can remove users.")

    if len(message.command) < 2:
        return await message.reply("Usage: /remove <user_id>")

    uid = message.command[1]
    banned_users.add(uid)
    save_list("banned_users.txt", banned_users)

    await message.reply(f"❌ User `{uid}` banned successfully.")

    # Log
    await bot.send_message(
        LOG_CHANNEL,
        f"⛔ **User Banned**\nBanned ID: `{uid}`"
    )


# ============================================
# *********  CAPTION GENERATOR  *********
# ============================================

@bot.on_message(filters.command("caption"))
async def caption_cmd(client, message):
    if not await check_user(message):
        return

    if len(message.command) < 2:
        return await message.reply("Usage: /caption <your caption>")

    text = " ".join(message.command[1:])

    result = ""
    for i in range(1, 20 + 1):  # 001–020
        result += f"{i:03d} - {text}\n"

    await message.reply(result)


# ============================================
# *********  RUN BOT + WEB APP  *********
# ============================================

if __name__ == "__main__":
    Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)), debug=False)).start()
    bot.run()
