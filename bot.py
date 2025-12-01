import os
import asyncio
from urllib.parse import urlparse
from pyrogram import Client, filters
from pyrogram.errors import RPCError
from telethon import TelegramClient
from telethon.sessions import StringSession
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import FastAPI
import uvicorn

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "1598576202"))
LOG_CHANNEL = int(os.getenv("LOG_CHANNEL", "-1003286415377"))
MONGO_URL = os.getenv("MONGO_URL")

mongo = AsyncIOMotorClient(MONGO_URL)
db = mongo["serena_bot"]
premium_col = db["premium"]
session_col = db["sessions"]

bot = Client("serena_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
TCACHE = {}

app = FastAPI()

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
        entity = await client.get_entity(chat)
        m = await client.get_messages(entity, ids=msgid)
        return m
    except:
        return None

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await bot.start()
    await send_log("BOT STARTED ✅")
    yield
    await bot.stop()
    for c in list(TCACHE.values()):
        try:
            await c.disconnect()
        except:
            pass

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"status": "Bot is running ✅", "brand": "Technical Serena"}

all_commands = ["start","help","login","logout","get","bulk","addpremium","removepremium"]

@bot.on_message(filters.command("start"))
async def cmd_start(client, message):
    uid = message.from_user.id
    prem = await is_premium(uid)
    await message.reply(f"Welcome. Premium: {prem}")
    await send_log(f"/start {uid}")

@bot.on_message(filters.command("help"))
async def cmd_help(client, message):
    await message.reply(
        "Commands:\n/start - welcome\n/help - this info\n/login - save session\n/logout - remove session\n/get <link> - download single\n/bulk <link> <count> - bulk\n/addpremium <id> - owner only\n/removepremium <id> - owner only"
    )

@bot.on_message(filters.command("login"))
async def cmd_login(client, message):
    await message.reply("Send your Telethon string session now")

@bot.on_message(filters.private & ~filters.command(all_commands))
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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "10000")))
