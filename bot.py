import os
import threading
import math
import time
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient

# ============================================
# CONFIG
# ============================================

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MONGO_DB = os.environ.get("MONGO_URI")
OWNER_ID = int(os.environ.get("OWNER_ID"))  # Your Telegram ID
LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL"))  # For Errors / Logs

client = MongoClient(MONGO_DB)
db = client['url_uploader']
users_db = db['users']
settings_db = db['settings']

# ============================================
# FLASK APP FOR RENDER
# ============================================

app = Flask(__name__)

@app.route("/")
def home():
    return "🔥 URL Upload Bot Running Successfully – Render Web Service Active!"

# ============================================
# BOT
# ============================================

bot = Client(
    "url-uploader-bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ============================================
# HELPERS
# ============================================

def get_user_settings(uid):
    data = settings_db.find_one({"user_id": uid})
    if not data:
        default = {
            "user_id": uid,
            "upload_channel": None
        }
        settings_db.insert_one(default)
        return default
    return data


def progress(current, total, message, start_time):
    now = time.time()
    diff = now - start_time
    speed = current / diff
    remaining = total - current
    eta = remaining / speed if speed != 0 else 0

    percent = current * 100 / total
    bar = "█" * int(percent / 5)

    try:
        message.edit(
            f"⬇ **Downloading...**\n"
            f"**Progress:** {percent:.2f}%\n"
            f"[{bar:<20}]\n"
            f"**Speed:** {human(speed)}/s\n"
            f"**ETA:** {human(eta)} "
        )
    except:
        pass


def human(size):
    power = 1024
    n = 0
    units = ["B", "KB", "MB", "GB", "TB"]
    while size > power:
        size /= power
        n += 1
    return f"{round(size, 2)} {units[n]}"


# ============================================
# COMMANDS
# ============================================

@bot.on_message(filters.command("start"))
async def start_cmd(_, m):
    user_id = m.from_user.id
    get_user_settings(user_id)

    await m.reply(
        "👋 **Welcome to Advanced URL Upload Bot**\n"
        "Send me any Direct Download URL.\n\n"
        "**Premium Features:**\n"
        "• Channel Upload\n"
        "• ETA + Speed\n"
        "• Logs\n"
        "• Admin Control\n\n"
        "**Menu:**",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⚙ Settings", callback_data="settings")],
            [InlineKeyboardButton("📞 Contact Owner", url=f"tg://user?id={OWNER_ID}")]
        ])
    )


@bot.on_callback_query(filters.regex("settings"))
async def settings_handler(_, q):
    user_id = q.from_user.id
    settings = get_user_settings(user_id)

    upload_ch = settings.get("upload_channel")

    await q.message.edit(
        f"⚙ **Settings Panel**\n\n"
        f"📤 Upload Channel: `{upload_ch}`\n\n"
        "**Options:**",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Set Upload Channel", callback_data="set_channel")],
            [InlineKeyboardButton("♻ Reset Settings", callback_data="reset")],
            [InlineKeyboardButton("⬅ Back", callback_data="back")]
        ])
    )


@bot.on_callback_query(filters.regex("reset"))
async def reset_handler(_, q):
    user_id = q.from_user.id
    settings_db.delete_one({"user_id": user_id})
    get_user_settings(user_id)

    await q.message.edit("✅ **Settings Reset Successfully**")


@bot.on_callback_query(filters.regex("back"))
async def back_handler(_, q):
    await start_cmd(_, q.message)


@bot.on_callback_query(filters.regex("set_channel"))
async def set_channel(_, q):
    await q.message.edit("📤 **Send me your Channel ID (with -100)**")


# ============================================
# ADMIN COMMANDS
# ============================================

@bot.on_message(filters.command("broadcast") & filters.user(OWNER_ID))
async def bc(_, m):
    text = m.text.split(" ", 1)[1]
    users = settings_db.find()

    count = 0
    for u in users:
        try:
            await bot.send_message(u['user_id'], text)
            count += 1
        except:
            pass

    await m.reply(f"📢 Broadcast completed to `{count}` users.")


# ============================================
# URL DOWNLOAD + UPLOAD SYSTEM
# ============================================

@bot.on_message(filters.text & ~filters.command(["start", "broadcast"]))
async def url_handler(_, m):
    uid = m.from_user.id
    text = m.text

    if not text.startswith("http"):
        return await m.reply("❌ Invalid URL!")

    settings = get_user_settings(uid)
    up_channel = settings.get("upload_channel")

    status = await m.reply("⏳ **Processing URL...**")

    try:
        start = time.time()
        out = await bot.download_media(text, progress=progress, progress_args=(status, start))

        await status.edit("📤 **Uploading to Telegram...**")

        if up_channel:
            sent = await bot.send_document(up_channel, out)
            await status.edit(f"✅ Uploaded to Channel\n\n🔗 Link: {sent.link}")
        else:
            await m.reply_document(out)

        await bot.send_message(LOG_CHANNEL, f"📥 Downloaded by {uid}\nURL: {text}")

    except Exception as e:
        await bot.send_message(LOG_CHANNEL, f"❌ Error: {e}")
        await status.edit("❌ Error while processing URL!")

# ============================================
# RUN BOTH IN PARALLEL (FLASK + BOT)
# ============================================

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


def run_bot():
    bot.run()


if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    threading.Thread(target=run_bot).start()
