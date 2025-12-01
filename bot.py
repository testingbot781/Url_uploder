import os
import asyncio
import time
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ───────────────────────────────────────────────
# FIXED CONSTANTS
# ───────────────────────────────────────────────
OWNER_ID = 1598576202
LOG_CHANNEL = -1003286415377

# Render ENV
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ───────────────────────────────────────────────
# FLASK FOR RENDER
# ───────────────────────────────────────────────
app = Flask(__name__)

@app.route("/")
def home():
    return "🔥 Bot Live — Powered by Technical Serena"

# ───────────────────────────────────────────────
# PYROGRAM BOT CLIENT
# ───────────────────────────────────────────────
bot = Client(
    "TS_UploadBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True
)

# ───────────────────────────────────────────────
# USER STORAGE
# ───────────────────────────────────────────────
upload_method = {}     # pyro / tele
replace_words = {}     # { uid: {"old":"new"} }
remove_words = {}      # { uid: ["hi","tum"] }
user_caption = {}      # caption pattern
bulk_state = {}        # bulk process steps

# ───────────────────────────────────────────────
# HELPERS
# ───────────────────────────────────────────────
def filter_text(text, uid):
    if uid in replace_words:
        for old, new in replace_words[uid].items():
            text = text.replace(old, new)
    if uid in remove_words:
        for w in remove_words[uid]:
            text = text.replace(w, "")
    return text

def progress_bar(done, total):
    try:
        percent = int((done / total) * 100)
        filled = int(percent / 10)
        bar = "█" * filled + "░" * (10 - filled)
        return f"[{bar}] {percent}%"
    except:
        return "..."

# ───────────────────────────────────────────────
# COMMANDS
# ───────────────────────────────────────────────

@bot.on_message(filters.command("start"))
async def start_cmd(_, m):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
        [InlineKeyboardButton("📥 Bulk Help", callback_data="bulk_help")]
    ])
    await m.reply(
        "👋 Welcome to **TECHNICAL SERENA - Save Content Bot**\n\n"
        "Send any PUBLIC message link to download.",
        reply_markup=kb
    )
    await bot.send_message(LOG_CHANNEL, f"🟢 START — {m.from_user.id}")


@bot.on_message(filters.command("help"))
async def help_cmd(_, m):
    await m.reply(
        "📘 **How to Use This Bot**:\n\n"
        "• Send PUBLIC message link\n"
        "• Bot downloads & sends to you\n"
        "• /bulk — Download multiple messages\n"
        "• /caption — Set custom caption\n"
        "• /adduser ID — Allow user\n"
        "• /removeuser ID — Ban user\n"
        "• /status — Check bot health"
    )


# ───────────────────────────────────────────────
# SETTINGS PANEL
# ───────────────────────────────────────────────

@bot.on_callback_query(filters.regex("settings"))
async def settings(_, q):
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Pyrogram", callback_data="set_pyro"),
            InlineKeyboardButton("Telethon", callback_data="set_tele")
        ],
        [
            InlineKeyboardButton("Replace Word", callback_data="rw"),
            InlineKeyboardButton("Remove Word", callback_data="rm")
        ],
        [
            InlineKeyboardButton("Reset", callback_data="reset"),
            InlineKeyboardButton("Status", callback_data="status")
        ]
    ])
    await q.message.edit("⚙️ **Settings Panel**", reply_markup=kb)


@bot.on_callback_query(filters.regex("set_pyro"))
async def set_pyro(_, q):
    upload_method[q.from_user.id] = "pyro"
    await q.answer("Pyrogram Selected ✓")


@bot.on_callback_query(filters.regex("set_tele"))
async def set_tele(_, q):
    upload_method[q.from_user.id] = "tele"
    await q.answer("Telethon Selected ✓")


@bot.on_callback_query(filters.regex("status"))
async def st(_, q):
    await q.answer("Bot Running Smoothly ✓")


# ───────────────────────────────────────────────
# BULK DOWNLOAD FLOW
# ───────────────────────────────────────────────

@bot.on_callback_query(filters.regex("bulk_help"))
async def bh(_, q):
    await q.message.edit(
        "📥 **Bulk Guide**:\n"
        "1. Use command `/bulk`\n"
        "2. Send a message link\n"
        "3. Bot will ask for count (max 500)"
    )


@bot.on_message(filters.command("bulk"))
async def bulk_start(_, m):
    bulk_state[m.from_user.id] = {"step": 1}
    await m.reply("📩 **Step 1:** Send message link.")


# ───────────────────────────────────────────────
# CAPTION SET
# ───────────────────────────────────────────────

@bot.on_message(filters.command("caption"))
async def caption_cmd(_, m):
    try:
        pattern = m.text.split(" ", 1)[1]
        user_caption[m.from_user.id] = pattern
        await m.reply("Caption pattern saved ✓\nExample: 001 Serena")
    except:
        await m.reply("Use: /caption 001 <YourCaption>")


# ───────────────────────────────────────────────
# DOWNLOAD HANDLER (PUBLIC MESSAGES)
# ───────────────────────────────────────────────

@bot.on_message(filters.regex("https://t.me/"))
async def get_msg(_, m):
    link = m.text.strip()

    try:
        await m.reply("⏳ Fetching message…")

        parts = link.split("/")
        msg_id = int(parts[-1])

        chat = "/".join(parts[:-1]).replace("https://t.me/", "")

        msg = await bot.get_messages(chat, msg_id)

        if not msg:
            return await m.reply("❌ Message not found")

        temp = await m.reply("⬇️ Downloading…")

        path = await msg.download(
            progress=async_progress,
            progress_args=(temp, msg)
        )

        caption = user_caption.get(m.from_user.id, "")
        caption = filter_text(caption, m.from_user.id)

        await bot.send_document(
            m.from_user.id,
            path,
            caption=caption
        )

        await bot.send_message(LOG_CHANNEL, f"✔️ Sent to {m.from_user.id}")

        await temp.delete()

    except Exception as e:
        await bot.send_message(LOG_CHANNEL, f"❌ ERROR: {e}")
        await m.reply("⚠️ Failed to download.")


# ───────────────────────────────────────────────
# PROGRESS FUNCTION
# ───────────────────────────────────────────────

async def async_progress(current, total, message, msg):
    bar = progress_bar(current, total)
    speed = f"{current/1024/1024:.2f} MB/s"
    await message.edit(
        f"⬇️ Downloading…\n"
        f"{bar}\n"
        f"{current/1024/1024:.2f} MB / {total/1024/1024:.2f} MB\n"
        f"⚡ Speed: {speed}"
    )


# ───────────────────────────────────────────────
# RUN BOT + FLASK
# ───────────────────────────────────────────────

async def main():
    await bot.start()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
