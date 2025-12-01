import os
import asyncio
import aiofiles
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from fastapi import FastAPI
import uvicorn
import threading
from motor.motor_asyncio import AsyncIOMotorClient

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

OWNER_ID = int(os.getenv("OWNER_ID", "1598576202"))
LOG_CHANNEL = int(os.getenv("LOG_CHANNEL", "-1003286415377"))
MONGO_URL = os.getenv("MONGO_URL")

# --------------------------
# Mongo DB
# --------------------------
mongo = AsyncIOMotorClient(MONGO_URL)
db = mongo["BOT_DB"]
premium_col = db["premium_users"]
session_col = db["user_sessions"]

# --------------------------
# Pyrogram Bot
# --------------------------
bot = Client(
    "MainBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# --------------------------
# FastAPI Keep Alive
# --------------------------
app = FastAPI()

@app.get("/")
async def root():
    return {"status": "running"}

def start_fastapi():
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)

# --------------------------
# Premium Check
# --------------------------
async def is_premium(user_id):
    return await premium_col.find_one({"user_id": user_id}) is not None

# --------------------------
# User Session Store
# --------------------------
async def save_session(user_id, session_string):
    await session_col.update_one(
        {"user_id": user_id},
        {"$set": {"session": session_string}},
        upsert=True
    )

async def get_session(user_id):
    data = await session_col.find_one({"user_id": user_id})
    return data["session"] if data else None

# --------------------------
# Commands
# --------------------------
@bot.on_message(filters.command("start"))
async def start_cmd(c, m):
    uid = m.from_user.id
    prem = await is_premium(uid)
    await m.reply(
        f"Hello {m.from_user.first_name},\n"
        f"Bot is active.\n"
        f"Premium: {prem}\n\n"
        f"Use /session to upload your session file."
    )
    await bot.send_message(LOG_CHANNEL, f"#NEW_USER → {uid}")

# --------------------------
# Premium Add/Remove
# --------------------------
@bot.on_message(filters.command("addpremium") & filters.user(OWNER_ID))
async def addprem_cmd(c, m):
    try:
        uid = int(m.command[1])
        await premium_col.update_one({"user_id": uid}, {"$set": {"user_id": uid}}, upsert=True)
        await m.reply("Premium added!")
        await bot.send_message(LOG_CHANNEL, f"#PREMIUM_ADDED → {uid}")
    except:
        await m.reply("Format: /addpremium user_id")

@bot.on_message(filters.command("removepremium") & filters.user(OWNER_ID))
async def removeprem_cmd(c, m):
    try:
        uid = int(m.command[1])
        await premium_col.delete_one({"user_id": uid})
        await m.reply("Premium removed!")
        await bot.send_message(LOG_CHANNEL, f"#PREMIUM_REMOVED → {uid}")
    except:
        await m.reply("Format: /removepremium user_id")

# --------------------------
# Session Upload
# --------------------------
@bot.on_message(filters.command("session"))
async def session_cmd(c, m):
    await m.reply("Send your session string as text.")

@bot.on_message(filters.text & ~filters.command())
async def session_save_cmd(c, m):
    if len(m.text) > 100:  # assume session string
        await save_session(m.from_user.id, m.text)
        await m.reply("Session saved.")
        await bot.send_message(LOG_CHANNEL, f"#SESSION_SAVED → {m.from_user.id}")

# --------------------------
# Bulk Download Handler
# --------------------------
@bot.on_message(filters.media)
async def downloader(c, m):
    uid = m.from_user.id
    premium = await is_premium(uid)

    if not premium:
        return await m.reply("Only premium users can download files.")

    try:
        msg = await m.reply("Downloading...")

        file_path = await m.download()

        await msg.edit("Uploading...")
        await m.reply_document(file_path)

        await msg.delete()
        os.remove(file_path)

        await bot.send_message(LOG_CHANNEL, f"#DOWNLOADED → {uid}")

    except FloodWait as e:
        await asyncio.sleep(e.value)
    except Exception as e:
        await m.reply(f"Error: {e}")

# --------------------------
# Start Threads
# --------------------------
def start_bot():
    asyncio.run(bot.start())
    asyncio.get_event_loop().run_forever()

if __name__ == "__main__":
    threading.Thread(target=start_fastapi).start()
    threading.Thread(target=start_bot).start()
