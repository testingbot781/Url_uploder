import os
import asyncio
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from telethon import TelegramClient
from telethon.sessions import StringSession
from motor.motor_asyncio import AsyncIOMotorClient

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO = os.getenv("MONGO_DB")

OWNER_ID = 1598576202
LOG_CHANNEL = -1003286415377

bot = Client("SerenaBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
mongo = AsyncIOMotorClient(MONGO)
db = mongo["SerenaBot"]
premium_db = db["premium"]

USER_SESSION = {}
USER_STRING = {}

async def is_premium(uid):
    data = await premium_db.find_one({"user_id": uid})
    return bool(data)

async def log(text):
    try:
        await bot.send_message(LOG_CHANNEL, f"📝 {text}")
    except:
        pass

@bot.on_message(filters.command("start"))
async def start_cmd(_, m):
    await m.reply("👋 Welcome! Session Login + Bulk Download Ready.")
    await log(f"{m.from_user.id} used /start")

@bot.on_message(filters.command("help"))
async def help_cmd(_, m):
    await m.reply(
        "📌 Commands:\n"
        "/string — Generate Pyrogram String\n"
        "/login — Login via Telethon Session\n"
        "/logout — Remove session\n"
        "/get <link> — Download 1 file\n"
        "/bulk <from> <to> <channel_id> — Bulk messages\n"
        "/addpremium <user_id>\n"
        "/delpremium <user_id>"
    )

@bot.on_message(filters.command("addpremium"))
async def add_premium(_, m):
    if m.from_user.id != OWNER_ID:
        return
    if len(m.text.split()) != 2:
        return await m.reply("Usage: /addpremium user_id")

    uid = int(m.text.split()[1])
    await premium_db.update_one({"user_id": uid}, {"$set": {"user_id": uid}}, upsert=True)
    await m.reply("✅ Premium Added")
    await log(f"Premium Added → {uid}")

@bot.on_message(filters.command("delpremium"))
async def del_premium(_, m):
    if m.from_user.id != OWNER_ID:
        return
    if len(m.text.split()) != 2:
        return await m.reply("Usage: /delpremium user_id")

    uid = int(m.text.split()[1])
    await premium_db.delete_one({"user_id": uid})
    await m.reply("❌ Premium Removed")
    await log(f"Premium Removed → {uid}")

@bot.on_message(filters.command("login"))
async def login_cmd(_, m):
    USER_STRING[m.from_user.id] = "WAIT"
    await m.reply("🔐 Send your Telethon String Session now.")

@bot.on_message(filters.private)
async def take_session(_, m):
    uid = m.from_user.id
    if uid in USER_STRING and USER_STRING[uid] == "WAIT":
        try:
            string = m.text.strip()
            client = TelegramClient(StringSession(string), API_ID, API_HASH)
            await client.connect()

            USER_SESSION[uid] = client
            USER_STRING[uid] = string

            await m.reply("✅ Session Login Successful!")
            await log(f"{uid} logged in session")
        except Exception as e:
            await m.reply(f"❌ Session Error: {e}")

@bot.on_message(filters.command("logout"))
async def logout_cmd(_, m):
    uid = m.from_user.id
    if uid in USER_SESSION:
        await USER_SESSION[uid].disconnect()
        USER_SESSION.pop(uid)
        USER_STRING.pop(uid, None)
        return await m.reply("🚪 Logged out.")

    await m.reply("❌ No active session.")

@bot.on_message(filters.command("get"))
async def get_file(_, m):
    uid = m.from_user.id

    if uid not in USER_SESSION:
        return await m.reply("❌ Login first using /login")

    if not await is_premium(uid):
        return await m.reply("⛔ Premium required.")

    parts = m.text.split()
    if len(parts) != 2:
        return await m.reply("Usage: /get link")

    link = parts[1]
    client = USER_SESSION[uid]

    try:
        await m.reply("⏳ Downloading…")

        entity, msg_id = await client.get_entity_from_link(link)
        msgx = await client.get_messages(entity, ids=msg_id)

        file = await client.download_media(msgx)
        await bot.send_document(uid, file)

        await log(f"Single File Sent → {uid}")

    except Exception as e:
        await m.reply(f"❌ Error: {e}")

@bot.on_message(filters.command("bulk"))
async def bulk_cmd(_, m):
    uid = m.from_user.id

    if uid not in USER_SESSION:
        return await m.reply("❌ Login first using /login")

    if not await is_premium(uid):
        return await m.reply("⛔ Premium required.")

    parts = m.text.split()
    if len(parts) != 4:
        return await m.reply("Usage: /bulk from to channel_id")

    s = int(parts[1])
    e = int(parts[2])
    channel = int(parts[3])

    client = USER_SESSION[uid]
    await m.reply(f"📦 Bulk Download Started\nRange: {s}-{e}")

    count = 0

    for msg_id in range(s, e + 1):
        try:
            x = await client.get_messages(channel, ids=msg_id)
            file = await client.download_media(x)
            await bot.send_document(uid, file)
            count += 1
            await asyncio.sleep(10)
        except:
            pass

    await m.reply(f"✅ Completed → {count} files")
    await log(f"Bulk Download Completed by {uid}")

async def main():
    await bot.start()
    await log("BOT ONLINE")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
