import os
import asyncio
import time
import math
import tempfile
from urllib.parse import urlparse
from aiohttp import ClientSession, web
from motor.motor_asyncio import AsyncIOMotorClient
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message

# ---------- ENV / CONSTANTS ----------
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
OWNER_ID = int(os.getenv("OWNER_ID", "1598576202"))
LOG_CHANNEL = int(os.getenv("LOG_CHANNEL", "-1003286415377"))
PORT = int(os.getenv("PORT", "10000"))

# ---------- DB ----------
mongo = AsyncIOMotorClient(MONGO_URI)
db = mongo["url_uploader_bot"]
users_col = db["users"]          # { user_id, premium:bool, banned:bool }
config_col = db["config"]        # single doc with _id:"main", owner_channel_id, admin_contact
stats_col = db["stats"]          # usage stats

# ---------- BOT ----------
bot = Client("url_uploader", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ---------- HELPERS ----------
async def is_banned(user_id: int) -> bool:
    doc = await users_col.find_one({"user_id": user_id})
    return bool(doc and doc.get("banned", False))

async def is_premium(user_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
    doc = await users_col.find_one({"user_id": user_id})
    return bool(doc and doc.get("premium", False))

async def set_premium(user_id: int, value: bool):
    await users_col.update_one({"user_id": user_id}, {"$set": {"premium": value}}, upsert=True)

async def set_banned(user_id: int, value: bool):
    await users_col.update_one({"user_id": user_id}, {"$set": {"banned": value}}, upsert=True)

async def get_owner_channel():
    doc = await config_col.find_one({"_id": "main"})
    return None if not doc else doc.get("owner_channel_id")

async def set_owner_channel(chat_id: int):
    await config_col.update_one({"_id": "main"}, {"$set": {"owner_channel_id": chat_id}}, upsert=True)

async def reset_config():
    await config_col.delete_one({"_id": "main"})

async def incr_stat(key: str, n: int = 1):
    await stats_col.update_one({"_id": key}, {"$inc": {"count": n}}, upsert=True)

async def send_log(text: str):
    try:
        await bot.send_message(LOG_CHANNEL, text)
    except:
        pass

def human(n: float) -> str:
    n = float(n)
    if n < 1024:
        return f"{n:.0f} B"
    for unit in ("KB","MB","GB","TB"):
        n /= 1024.0
        if n < 1024:
            return f"{n:.2f} {unit}"
    return f"{n:.2f} PB"

# ---------- HTTP HEALTH (aiohttp) ----------
async def http_index(request):
    return web.json_response({"status": "ok", "service": "url_uploader"})

async def start_http_server():
    app = web.Application()
    app.router.add_get("/", http_index)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

# ---------- UI ----------
def main_keyboard():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("⚙ Settings", callback_data="settings")],
            [InlineKeyboardButton("📞 Contact Owner", url=f"tg://user?id={OWNER_ID}")]
        ]
    )

# ---------- COMMANDS ----------
@bot.on_message(filters.command("start"))
async def cmd_start(_, m: Message):
    uid = m.from_user.id
    await m.reply(
        "Welcome — send a direct http/https file link and I'll download & upload it.\n\n"
        "Use Settings for channel forwarding or contact owner.",
        reply_markup=main_keyboard()
    )
    await send_log(f"[START] {uid}")

@bot.on_message(filters.command("help"))
async def cmd_help(_, m: Message):
    await m.reply(
        "/start - welcome\n"
        "/help - this\n"
        "/addpremium <id> - owner only\n"
        "/removepremium <id> - owner only\n"
        "/ban <id> - owner only\n"
        "/unban <id> - owner only\n"
        "/setchannel <chat_id> - owner only\n"
        "/resetsettings - owner only\n"
        "/broadcast <text> - owner only\n"
        "/stats - owner only\n"
        "Send any direct file URL (http/https) in private chat to upload."
    )

# Admin commands
@bot.on_message(filters.command("addpremium") & filters.user(OWNER_ID))
async def cmd_addpremium(_, m: Message):
    if len(m.command) != 2:
        return await m.reply("Usage: /addpremium <user_id>")
    uid = int(m.command[1])
    await set_premium(uid, True)
    await m.reply(f"Added premium: {uid}")
    await send_log(f"[ADMIN] Added premium {uid}")

@bot.on_message(filters.command("removepremium") & filters.user(OWNER_ID))
async def cmd_removepremium(_, m: Message):
    if len(m.command) != 2:
        return await m.reply("Usage: /removepremium <user_id>")
    uid = int(m.command[1])
    await set_premium(uid, False)
    await m.reply(f"Removed premium: {uid}")
    await send_log(f"[ADMIN] Removed premium {uid}")

@bot.on_message(filters.command("ban") & filters.user(OWNER_ID))
async def cmd_ban(_, m: Message):
    if len(m.command) != 2:
        return await m.reply("Usage: /ban <user_id>")
    uid = int(m.command[1])
    await set_banned(uid, True)
    await m.reply(f"Banned: {uid}")
    await send_log(f"[ADMIN] Banned {uid}")

@bot.on_message(filters.command("unban") & filters.user(OWNER_ID))
async def cmd_unban(_, m: Message):
    if len(m.command) != 2:
        return await m.reply("Usage: /unban <user_id>")
    uid = int(m.command[1])
    await set_banned(uid, False)
    await m.reply(f"Unbanned: {uid}")
    await send_log(f"[ADMIN] Unbanned {uid}")

@bot.on_message(filters.command("setchannel") & filters.user(OWNER_ID))
async def cmd_setchannel(_, m: Message):
    if len(m.command) != 2:
        return await m.reply("Usage: /setchannel <chat_id>")
    chat_id = int(m.command[1])
    await set_owner_channel(chat_id)
    await m.reply(f"Owner upload channel set to: {chat_id}")
    await send_log(f"[ADMIN] Set owner channel {chat_id}")

@bot.on_message(filters.command("resetsettings") & filters.user(OWNER_ID))
async def cmd_resetsettings(_, m: Message):
    await reset_config()
    await m.reply("Settings reset.")
    await send_log("[ADMIN] Settings reset")

@bot.on_message(filters.command("broadcast") & filters.user(OWNER_ID))
async def cmd_broadcast(_, m: Message):
    text = m.text.partition(" ")[2].strip()
    if not text:
        return await m.reply("Usage: /broadcast <text>")
    cursor = users_col.find({"premium": True})
    sent = 0
    async for u in cursor:
        uid = u["user_id"]
        try:
            await bot.send_message(uid, text)
            sent += 1
            await asyncio.sleep(0.05)
        except:
            pass
    await m.reply(f"Broadcast to {sent} users.")
    await send_log(f"[ADMIN] Broadcast sent to {sent}")

@bot.on_message(filters.command("stats") & filters.user(OWNER_ID))
async def cmd_stats(_, m: Message):
    total = await users_col.count_documents({})
    premium = await users_col.count_documents({"premium": True})
    bans = await users_col.count_documents({"banned": True})
    await m.reply(f"Users: {total}\nPremium: {premium}\nBanned: {bans}")

# ---------- CALLBACKS ----------
@bot.on_callback_query()
async def cb_handler(_, cq):
    data = cq.data
    uid = cq.from_user.id
    if data == "settings":
        owner_channel = await get_owner_channel()
        await cq.message.edit(
            f"⚙ Settings\nUpload Channel: `{owner_channel}`",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Set Channel", callback_data="set_channel")],
                [InlineKeyboardButton("Reset", callback_data="reset_conf")],
                [InlineKeyboardButton("Contact Owner", url=f"tg://user?id={OWNER_ID}")]
            ])
        )
        return
    if data == "set_channel":
        if uid != OWNER_ID:
            return await cq.answer("Only owner can set.", show_alert=True)
        await cq.answer("Send /setchannel <chat_id> to set upload channel.", show_alert=True)
        return
    if data == "reset_conf":
        if uid != OWNER_ID:
            return await cq.answer("Only owner can reset.", show_alert=True)
        await reset_config()
        await cq.answer("Settings reset.", show_alert=True)
        await send_log("[ADMIN] Reset via UI")
        return

# ---------- DOWNLOAD / UPLOAD LOGIC ----------
async def stream_download(url: str, path: str, progress_cb=None):
    timeout = aiohttp_timeout = 60
    async with ClientSession(timeout=org_timeout(timeout)) as sess:
        async with sess.get(url) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length") or 0)
            downloaded = 0
            start = time.time()
            with open(path, "wb") as f:
                async for chunk in resp.content.iter_chunked(64 * 1024):
                    if not chunk:
                        continue
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_cb:
                        elapsed = max(time.time() - start, 0.0001)
                        speed = downloaded / elapsed
                        await progress_cb(downloaded, total, speed)

# small helper to create aiohttp timeout object to avoid NameError on some envs
def org_timeout(t: int):
    from aiohttp import ClientTimeout
    return ClientTimeout(total=t)

async def handle_url_message(m: Message):
    uid = m.from_user.id
    url = m.text.strip()
    if await is_banned(uid):
        return await m.reply("You are banned.")
    if not await is_premium(uid):
        return await m.reply("You must be premium to use this bot. Ask owner to add you.")
    if not (url.startswith("http://") or url.startswith("https://")):
        return await m.reply("Send a valid http/https URL.")

    tmp = tempfile.gettempdir()
    filename = urlparse(url).path.split("/")[-1] or f"file_{int(time.time())}"
    if len(filename) > 200:
        filename = filename[-200:]
    path = os.path.join(tmp, filename)

    progress_msg = await m.reply_text("Downloading... 0%")

    last_edit = 0

    async def progress_cb(downloaded, total, speed):
        nonlocal last_edit
        now = time.time()
        if now - last_edit < 1.5:
            return
        last_edit = now
        if total:
            pct = downloaded * 100 / total
            eta = int((total - downloaded) / (speed + 1e-9))
            txt = (
                f"Downloading: {filename}\n"
                f"{pct:.2f}% • {human(downloaded)} / {human(total)}\n"
                f"Speed: {human(speed)}/s • ETA: {eta}s"
            )
        else:
            txt = f"Downloading: {filename}\n{human(downloaded)} downloaded\nSpeed: {human(speed)}/s"
        try:
            await progress_msg.edit_text(txt)
        except:
            pass

    try:
        await send_log(f"[DL START] {uid} -> {url}")
        await stream_download(url, path, progress_cb=progress_cb)
    except Exception as e:
        await progress_msg.edit_text("Download failed.")
        await send_log(f"[DL ERROR] {uid} -> {url} -> {e}")
        try:
            if os.path.exists(path):
                os.remove(path)
        except:
            pass
        return

    owner_channel = await get_owner_channel()
    target = owner_channel if owner_channel else uid

    try:
        await progress_msg.edit_text("Uploading to Telegram...")
        start_upload = time.time()
        def tg_progress(cur, tot):
            elapsed = max(time.time() - start_upload, 0.0001)
            speed = cur / elapsed
            try:
                pct = cur * 100 / tot if tot else 0
                eta = int((tot - cur) / (speed + 1e-9)) if tot else 0
                txt = (
                    f"Uploading: {filename}\n"
                    f"{pct:.2f}% • {human(cur)} / {human(tot)}\n"
                    f"Speed: {human(speed)}/s • ETA: {eta}s"
                )
                asyncio.get_event_loop().create_task(progress_msg.edit_text(txt))
            except:
                pass
        await bot.send_document(chat_id=target, document=path, progress=lambda c, t: tg_progress(c, t))
        await progress_msg.edit_text("Upload complete ✅")
        await send_log(f"[UPLOAD] {uid} -> {target} : {filename}")
        await incr_stat("uploads")
    except Exception as e:
        await progress_msg.edit_text("Upload failed.")
        await send_log(f"[UPLOAD ERROR] {uid} -> {e}")
    finally:
        try:
            if os.path.exists(path):
                os.remove(path)
        except:
            pass

# route private text URLs
@bot.on_message(filters.private & filters.regex(r"^https?://"))
async def url_handler(m: Message, _=None):
    await handle_url_message(m)

# fallback: any text in private that is not command and not url
@bot.on_message(filters.private & filters.text & ~filters.command)
async def private_text_handler(m: Message, _=None):
    await m.reply("Send direct http/https URL to download. Use /help for commands.")

# ---------- STARTUP ----------
async def main():
    await start_http_server()
    await bot.start()
    await send_log("Bot started (single-process mode).")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
