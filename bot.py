import os
import asyncio
from urllib.parse import urlparse
from fastapi import FastAPI
from pyrogram import Client, filters
from pyrogram.errors import RPCError
from telethon import TelegramClient
from telethon.sessions import StringSession
from motor.motor_asyncio import AsyncIOMotorClient

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN"))
OWNER_ID = int(os.getenv("OWNER_ID", "1598576202"))
LOG_CHANNEL = int(os.getenv("LOG_CHANNEL", "-1003286415377"))
MONGO_URL = os.getenv("MONGO_URL")

mongo = AsyncIOMotorClient(MONGO_URL)
db = mongo["serena_bot"]
premium_col = db["premium"]
session_col = db["sessions"]

bot = Client("serena_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
app = FastAPI()
TCACHE = {}

def parse_tme(link):
    try:
        u = urlparse(link.strip())
        if 't.me' not in u.netloc and 'telegram.me' not in u.netloc:
            return None
        parts = u.path.strip('/').split('/')
        if parts[0] == 'c' and len(parts) >= 3:
            internal = parts[1]
            msgid = int(parts[2])
            chat_id = int(f"-100{internal}")
            return chat_id, msgid
        if len(parts) >= 2:
            chat = parts[0]
            msgid = int(parts[1])
            return chat, msgid
    except:
        return None

async def is_premium(uid):
    return await premium_col.find_one({"user": uid}) is not None or uid == OWNER_ID

async def save_session(uid, s):
    await session_col.update_one({"user": uid}, {"$set": {"session": s}}, upsert=True)
    if uid in TCACHE:
        try:
            await TCACHE[uid].disconnect()
        except:
            pass
        TCACHE.pop(uid, None)

async def get_saved_session(uid):
    row = await session_col.find_one({"user": uid})
    return row["session"] if row and "session" in row else None

async def get_tele_client(uid):
    if uid in TCACHE:
        return TCACHE[uid]
    s = await get_saved_session(uid)
    if not s:
        return None
    client = TelegramClient(StringSession(s), API_ID, API_HASH)
    await client.connect()
    TCACHE[uid] = client
    return client

async def send_log(text):
    try:
        await bot.send_message(LOG_CHANNEL, text)
    except:
        pass

def make_progress_cb(msg, start_time):
    async def _cb(current, total):
        try:
            now = asyncio.get_event_loop().time()
            elapsed = max(now - start_time, 0.0001)
            speed = current / elapsed
            percent = (current / total) * 100 if total else 0
            eta = int((total - current) / speed) if speed > 0 else 0
            barlen = 20
            filled = int(barlen * percent / 100)
            bar = "█" * filled + "░" * (barlen - filled)
            txt = f"{bar} {percent:5.1f}%\nUploaded: {current/1024/1024:.2f}MB/{total/1024/1024:.2f}MB\nSpeed: {speed/1024/1024:.2f}MB/s ETA:{eta}s"
            await msg.edit(txt)
        except:
            pass
    return _cb

async def fetch_via_pyrogram(chat, msgid):
    try:
        m = await bot.get_messages(chat, msgid)
        return m
    except RPCError:
        return None
    except:
        return None

async def fetch_via_tele(client, chat, msgid):
    try:
        if isinstance(chat, int):
            entity = await client.get_entity(chat)
        else:
            entity = await client.get_entity(chat)
        m = await client.get_messages(entity, ids=msgid)
        return m
    except:
        return None

@app.on_event("startup")
async def _startup():
    await bot.start()
    await send_log("BOT STARTED")

@app.on_event("shutdown")
async def _shutdown():
    try:
        await bot.stop()
    except:
        pass
    for c in list(TCACHE.values()):
        try:
            await c.disconnect()
        except:
            pass

@app.get("/")
async def _root():
    return {"status": "running"}

@bot.on_message(filters.command("start"))
async def cmd_start(client, message):
    uid = message.from_user.id
    prem = await is_premium(uid)
    await message.reply(f"Welcome. Premium: {prem}")
    await send_log(f"/start {uid}")

@bot.on_message(filters.command("help"))
async def cmd_help(client, message):
    await message.reply("/login - save session string\n/logout - remove session\n/get <link> - download single\n/bulk <link> <count> - bulk up to 500\n/addpremium <id> (owner)\n/removepremium <id> (owner)")

@bot.on_message(filters.command("login"))
async def cmd_login(client, message):
    await message.reply("Send your Telethon string session now")

@bot.on_message(filters.private & ~filters.command())
async def save_session_msg(client, message):
    uid = message.from_user.id
    text = message.text or ""
    if len(text) < 100:
        return
    await save_session(uid, text)
    await message.reply("Session saved")
    await send_log(f"SESSION SAVED {uid}")

@bot.on_message(filters.command("logout"))
async def cmd_logout(client, message):
    uid = message.from_user.id
    await session_col.delete_one({"user": uid})
    if uid in TCACHE:
        try:
            await TCACHE[uid].disconnect()
        except:
            pass
        TCACHE.pop(uid, None)
    await message.reply("Session removed")
    await send_log(f"SESSION REMOVED {uid}")

@bot.on_message(filters.command("addpremium") & filters.user(OWNER_ID))
async def cmd_add_prem(client, message):
    try:
        uid = int(message.command[1])
        await premium_col.update_one({"user": uid}, {"$set": {"user": uid}}, upsert=True)
        await message.reply("Added")
        await send_log(f"PREMIUM ADDED {uid}")
    except:
        await message.reply("Usage: /addpremium user_id")

@bot.on_message(filters.command("removepremium") & filters.user(OWNER_ID))
async def cmd_remove_prem(client, message):
    try:
        uid = int(message.command[1])
        await premium_col.delete_one({"user": uid})
        await message.reply("Removed")
        await send_log(f"PREMIUM REMOVED {uid}")
    except:
        await message.reply("Usage: /removepremium user_id")

@bot.on_message(filters.command("get"))
async def cmd_get(client, message):
    uid = message.from_user.id
    if not await is_premium(uid):
        return await message.reply("Premium required")
    parts = message.text.split(maxsplit=1)
    if len(parts) != 2:
        return await message.reply("Usage: /get <t.me link>")
    link = parts[1].strip()
    parsed = parse_tme(link)
    if not parsed:
        return await message.reply("Invalid link")
    chat, msgid = parsed
    m = await fetch_via_pyrogram(chat, msgid)
    tele_used = False
    if not m:
        tc = await get_tele_client(uid)
        if not tc:
            return await message.reply("Private content: login required (/login)")
        m = await fetch_via_tele(tc, chat, msgid)
        tele_used = True
    if not m:
        return await message.reply("Message not found")
    try:
        status = await message.reply("Downloading...")
        if tele_used:
            path = await m.download_media()
        else:
            path = await m.download()
        up_msg = await message.reply("Uploading...")
        start = asyncio.get_event_loop().time()
        cb = make_progress_cb(up_msg, start)
        await bot.send_document(uid, path, progress=cb)
        try:
            await status.delete()
        except:
            pass
        await send_log(f"GET by {uid} from {chat}/{msgid}")
    except Exception as e:
        await message.reply("Failed")
        await send_log(f"ERROR_GET {e}")

@bot.on_message(filters.command("bulk"))
async def cmd_bulk(client, message):
    uid = message.from_user.id
    if not await is_premium(uid):
        return await message.reply("Premium required")
    parts = message.text.split()
    if len(parts) < 3:
        return await message.reply("Usage: /bulk <link> <count>")
    link = parts[1]
    try:
        count = int(parts[2])
    except:
        return await message.reply("Count must be number")
    if count < 1 or count > 500:
        return await message.reply("Count 1..500")
    parsed = parse_tme(link)
    if not parsed:
        return await message.reply("Invalid link")
    chat, start_msg = parsed
    tc = await get_tele_client(uid)
    use_tele = False
    if tc:
        use_tele = True
    await message.reply(f"Starting bulk {count}")
    done = 0
    for i in range(count):
        mid = start_msg - i
        m = None
        if not use_tele:
            try:
                m = await fetch_via_pyrogram(chat, mid)
            except:
                m = None
        if not m and use_tele:
            try:
                m = await fetch_via_tele(tc, chat, mid)
            except:
                m = None
        if not m:
            continue
        try:
            info = await message.reply(f"Downloading {mid}")
            if use_tele and hasattr(m, "download_media"):
                path = await m.download_media()
            else:
                path = await m.download()
            up = await message.reply(f"Uploading {mid}")
            start = asyncio.get_event_loop().time()
            cb = make_progress_cb(up, start)
            await bot.send_document(uid, path, progress=cb)
            try:
                await info.delete()
                await up.delete()
            except:
                pass
            done += 1
            await asyncio.sleep(10)
        except Exception:
            pass
    await message.reply(f"Bulk done. Sent: {done}")
    await send_log(f"BULK by {uid} requested {count} from {chat}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "10000")))
