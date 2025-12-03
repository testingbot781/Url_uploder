import os
import asyncio
import math
import time
import shutil
import requests
from urllib.parse import urlparse
from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message,
)
from motor.motor_asyncio import AsyncIOMotorClient

# ---------- CONFIG (Owner & Logs fixed) ----------
OWNER_ID = 1598576202
LOG_CHANNEL = -1003286415377

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URL = os.getenv("MONGO_URL")

# ---------- DB ----------
mongo = AsyncIOMotorClient(MONGO_URL)
db = mongo["url_uploader"]
users_col = db["users"]           # { user_id, banned:bool, premium:bool }
settings_col = db["settings"]     # single doc with { owner_channel_id:..., admin_contact:... }
stats_col = db["stats"]           # usage stats

# ---------- BOT ----------
bot = Client("url_uploader_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ---------- Helpers ----------
def is_url(text: str):
    if not text:
        return False
    try:
        u = urlparse(text.strip())
        return u.scheme in ("http", "https")
    except:
        return False

async def is_banned(user_id: int):
    r = await users_col.find_one({"user_id": user_id})
    return bool(r and r.get("banned"))

async def is_premium(user_id: int):
    if user_id == OWNER_ID:
        return True
    r = await users_col.find_one({"user_id": user_id})
    return bool(r and r.get("premium"))

async def add_premium(user_id: int):
    await users_col.update_one({"user_id": user_id}, {"$set": {"premium": True}}, upsert=True)

async def remove_premium(user_id: int):
    await users_col.update_one({"user_id": user_id}, {"$set": {"premium": False}}, upsert=True)

async def ban_user(user_id: int):
    await users_col.update_one({"user_id": user_id}, {"$set": {"banned": True}}, upsert=True)

async def unban_user(user_id: int):
    await users_col.update_one({"user_id": user_id}, {"$set": {"banned": False}}, upsert=True)

async def get_setting(key: str):
    doc = await settings_col.find_one({"_id": "main"})
    return None if not doc else doc.get(key)

async def set_setting(key: str, value):
    await settings_col.update_one({"_id": "main"}, {"$set": {key: value}}, upsert=True)

async def incr_stat(key: str, n: int = 1):
    await stats_col.update_one({"_id": key}, {"$inc": {"count": n}}, upsert=True)

async def send_log(text: str):
    try:
        await bot.send_message(LOG_CHANNEL, text)
    except:
        pass

def human_size(bytes_amount: int):
    if bytes_amount < 1024:
        return f"{bytes_amount} B"
    units = ["KB", "MB", "GB", "TB"]
    size = bytes_amount / 1024.0
    unit_index = 0
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1
    return f"{size:.2f} {units[unit_index]}"

# ---------- Progress tracker for download (stream) ----------
def download_stream(url: str, path: str, progress_callback=None, chunk_size=1024*64):
    """
    Stream download from URL to path. Calls progress_callback(downloaded_bytes, total_bytes).
    Returns final file path.
    """
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length") or 0)
        downloaded = 0
        start = time.time()
        with open(path, "wb") as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if not chunk:
                    continue
                f.write(chunk)
                downloaded += len(chunk)
                if progress_callback:
                    elapsed = max(time.time() - start, 0.0001)
                    speed = downloaded / elapsed
                    try:
                        progress_callback(downloaded, total, speed)
                    except:
                        pass
    return path

# ---------- UI Buttons ----------
def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Set channel", callback_data="set_channel")],
        [InlineKeyboardButton("Reset settings", callback_data="reset_settings"),
         InlineKeyboardButton("Contact Admin", callback_data="contact_admin")],
        [InlineKeyboardButton("Bot Status", callback_data="bot_status")]
    ])

# ---------- Commands ----------
@bot.on_message(filters.command("start"))
async def start_cmd(client: Client, message: Message):
    uid = message.from_user.id
    if await is_banned(uid):
        return await message.reply_text("You are banned.")
    kb = main_keyboard()
    await message.reply_text(
        "Welcome to URL UPLOADER ✅\nSend a direct file URL (http/https) to upload.\nUse the buttons for settings.",
        reply_markup=kb
    )
    await send_log(f"[START] {uid}")

@bot.on_message(filters.command("help"))
async def help_cmd(client, message: Message):
    text = (
        "URL Uploader Help:\n\n"
        "- Send a direct file URL and bot will download & upload it.\n"
        "- If you set a channel via Settings, files will be forwarded there.\n"
        "- Only premium users can use the uploader (Owner can add premium users).\n\n"
        "Admin commands:\n"
        "/addpremium <user_id>\n"
        "/removepremium <user_id>\n"
        "/ban <user_id>\n"
        "/unban <user_id>\n"
        "/setchannel <chat_id>\n"
        "/resetsettings\n"
        "/broadcast <text>\n"
        "/stats\n"
    )
    await message.reply_text(text)

# Admin-only commands
@bot.on_message(filters.command("addpremium") & filters.user(OWNER_ID))
async def cmd_addpremium(c, m: Message):
    if len(m.command) != 2:
        return await m.reply_text("Usage: /addpremium <user_id>")
    uid = int(m.command[1])
    await add_premium(uid)
    await m.reply_text(f"Added premium: {uid}")
    await send_log(f"[ADMIN] Added premium {uid}")

@bot.on_message(filters.command("removepremium") & filters.user(OWNER_ID))
async def cmd_removepremium(c, m: Message):
    if len(m.command) != 2:
        return await m.reply_text("Usage: /removepremium <user_id>")
    uid = int(m.command[1])
    await remove_premium(uid)
    await m.reply_text(f"Removed premium: {uid}")
    await send_log(f"[ADMIN] Removed premium {uid}")

@bot.on_message(filters.command("ban") & filters.user(OWNER_ID))
async def cmd_ban(c, m: Message):
    if len(m.command) != 2:
        return await m.reply_text("Usage: /ban <user_id>")
    uid = int(m.command[1])
    await ban_user(uid)
    await m.reply_text(f"Banned: {uid}")
    await send_log(f"[ADMIN] Banned {uid}")

@bot.on_message(filters.command("unban") & filters.user(OWNER_ID))
async def cmd_unban(c, m: Message):
    if len(m.command) != 2:
        return await m.reply_text("Usage: /unban <user_id>")
    uid = int(m.command[1])
    await unban_user(uid)
    await m.reply_text(f"Unbanned: {uid}")
    await send_log(f"[ADMIN] Unbanned {uid}")

@bot.on_message(filters.command("setchannel") & filters.user(OWNER_ID))
async def cmd_setchannel(c, m: Message):
    if len(m.command) != 2:
        return await m.reply_text("Usage: /setchannel <chat_id>")
    chat_id = int(m.command[1])
    await set_setting("owner_channel_id", chat_id)
    await m.reply_text(f"Channel set to {chat_id}")
    await send_log(f"[ADMIN] Set channel {chat_id}")

@bot.on_message(filters.command("resetsettings") & filters.user(OWNER_ID))
async def cmd_resetsettings(c, m: Message):
    await settings_col.delete_one({"_id": "main"})
    await m.reply_text("Settings reset.")
    await send_log("[ADMIN] Settings reset")

@bot.on_message(filters.command("broadcast") & filters.user(OWNER_ID))
async def cmd_broadcast(c, m: Message):
    text = m.text.partition(" ")[2].strip()
    if not text:
        return await m.reply_text("Usage: /broadcast <message>")
    # iterate premium users and send message (careful with flood)
    cursor = users_col.find({"premium": True})
    sent = 0
    async for doc in cursor:
        uid = doc["user_id"]
        try:
            await bot.send_message(uid, text)
            sent += 1
            await asyncio.sleep(0.1)
        except:
            pass
    await m.reply_text(f"Broadcast sent to {sent}")
    await send_log(f"[ADMIN] Broadcast sent to {sent}")

@bot.on_message(filters.command("stats") & filters.user(OWNER_ID))
async def cmd_stats(c, m: Message):
    total_users = await users_col.count_documents({})
    premium_users = await users_col.count_documents({"premium": True})
    await m.reply_text(f"Users: {total_users}\nPremium: {premium_users}")
    await send_log("[ADMIN] Stats requested")

# Inline callbacks
@bot.on_callback_query()
async def cq_handler(c, cq):
    data = cq.data
    uid = cq.from_user.id
    if data == "set_channel":
        if uid != OWNER_ID:
            return await cq.answer("Only owner can set channel.", show_alert=True)
        await cq.message.edit("Send /setchannel <chat_id> in chat with bot (owner only).")
        return
    if data == "reset_settings":
        if uid != OWNER_ID:
            return await cq.answer("Only owner can reset.", show_alert=True)
        await settings_col.delete_one({"_id":"main"})
        await cq.answer("Settings reset.")
        await send_log("[ADMIN] Settings reset via UI")
        return
    if data == "contact_admin":
        admin_contact = await get_setting("admin_contact")
        if not admin_contact:
            admin_contact = f"https://t.me/{os.getenv('ADMIN_TG','technicalSerena')}"
        await cq.answer(f"Contact Admin: {admin_contact}", show_alert=True)
        return
    if data == "bot_status":
        await cq.answer("Bot is online.", show_alert=True)
        return

# When user sends a URL
@bot.on_message(filters.private & filters.regex(r"^https?://"))
async def url_handler(c, m: Message):
    uid = m.from_user.id
    if await is_banned(uid):
        return await m.reply_text("You are banned.")
    if not await is_premium(uid):
        return await m.reply_text("You must be premium to use this bot. Ask owner to add you.")
    url = m.text.strip()
    await m.reply_text("Starting download... (check progress in chat).")
    await send_log(f"[DOWNLOAD START] {uid} -> {url}")
    # prepare file path
    tmp_dir = "/tmp/urluploader"
    os.makedirs(tmp_dir, exist_ok=True)
    filename = urlparse(url).path.split("/")[-1] or f"file_{int(time.time())}"
    path = os.path.join(tmp_dir, filename)
    last_edit = None
    start_time = time.time()
    def progress_cb(downloaded, total, speed):
        nonlocal last_edit
        # build progress text
        if total:
            pct = downloaded / total * 100
            eta = int((total - downloaded) / (speed + 1e-9))
            text = (f"Downloading: {filename}\n"
                    f"{pct:.2f}% • {human_size(downloaded)} / {human_size(total)}\n"
                    f"Speed: {human_size(int(speed))}/s • ETA: {eta}s")
        else:
            text = f"Downloading: {filename}\n{human_size(downloaded)} downloaded\nSpeed: {human_size(int(speed))}/s"
        # edit or send a short progress message every ~2s
        now = time.time()
        if not last_edit or now - last_edit >= 2:
            try:
                asyncio.get_event_loop().create_task(progress_msg.edit_text(text))
                last_edit = now
            except:
                pass

    try:
        # send initial progress message
        progress_msg = await m.reply_text("Downloading... 0%")
        # stream-download
        download_stream(url, path, progress_callback=progress_cb)
    except Exception as e:
        await m.reply_text("Download failed.")
        await send_log(f"[ERROR DOWNLOAD] {uid} {url} {e}")
        try:
            if os.path.exists(path):
                os.remove(path)
        except:
            pass
        return

    # after download, upload to channel or to user
    owner_channel = await get_setting("owner_channel_id")
    target = owner_channel if owner_channel else uid
    try:
        up_msg = await progress_msg.edit_text("Uploading to Telegram...")
        # send with upload progress callback provided by Pyrogram
        start_upload = time.time()
        def tg_progress(current, total):
            elapsed = max(time.time() - start_upload, 0.0001)
            speed = current / elapsed
            pct = (current/total)*100 if total else 0
            eta = int((total-current)/(speed+1e-9)) if total else 0
            txt = (f"Uploading: {filename}\n{pct:.2f}% • {human_size(current)} / {human_size(total)}\n"
                   f"Speed: {human_size(int(speed))}/s • ETA: {eta}s")
            try:
                asyncio.get_event_loop().create_task(progress_msg.edit_text(txt))
            except:
                pass
        # send file
        await bot.send_document(chat_id=target, document=path, progress=lambda c, t: tg_progress(c, t))
        await progress_msg.edit_text("Upload complete ✅")
        await send_log(f"[UPLOAD COMPLETE] {uid} -> {target} {filename}")
        await incr_stat("uploads")
    except Exception as e:
        await progress_msg.edit_text("Upload failed.")
        await send_log(f"[ERROR UPLOAD] {uid} {e}")
    finally:
        # cleanup
        try:
            if os.path.exists(path):
                os.remove(path)
        except:
            pass

# small helper for human readable sizes
def human_size(num):
    step = 1024.0
    for unit in ["B","KB","MB","GB","TB"]:
        if num < step:
            return f"{num:.2f} {unit}"
        num /= step
    return f"{num:.2f} PB"

# ---------- Start ----------
if __name__ == "__main__":
    bot.run()
