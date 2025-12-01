import os
import asyncio
from fastapi import FastAPI
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from telethon import TelegramClient
from telethon.sessions import StringSession

# -------------------------------------------------------
# CONFIG
# -------------------------------------------------------
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

OWNER_ID = int(os.getenv("OWNER_ID", "1598576202"))
LOG_CHANNEL = int(os.getenv("LOG_CHANNEL", "-1003286415377"))

# -------------------------------------------------------
# MAIN BOT (Pyrogram)
# -------------------------------------------------------
bot = Client(
    "MainBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    parse_mode=ParseMode.HTML
)

# -------------------------------------------------------
# FASTAPI SERVER (Render Uptime)
# -------------------------------------------------------
app = FastAPI()

@app.get("/")
async def root():
    return {"status": "running", "bot": "Serena MasterBot"}

# -------------------------------------------------------
# STORAGE (in-memory)
# -------------------------------------------------------
USER_SESSIONS = {}          # user_id : telethon_client
USER_STRING = {}            # user_id : string_session

# -------------------------------------------------------
# COMMANDS
# -------------------------------------------------------

@bot.on_message(filters.command("start"))
async def start_cmd(_, msg):
    await msg.reply(
        "👋 <b>Welcome to Serena Multi-Engine Bot</b>\n"
        "Use /help to explore features."
    )
    await bot.send_message(LOG_CHANNEL, f"User {msg.from_user.id} used /start")

@bot.on_message(filters.command("help"))
async def help_cmd(_, msg):
    await msg.reply(
        "📘 <b>Help Menu</b>\n\n"
        "⭐ Session Login Menu:\n"
        "/string — Generate Pyrogram String\n"
        "/login — Login using Telethon\n\n"
        "⭐ Download Tools:\n"
        "/get <msg_link> — download single\n"
        "/bulk <from> <to> <channel_id> — bulk download\n"
        "/logout — remove user session\n"
    )

# -------------------------------------------------------
# STRING SESSION GENERATOR (PYROGRAM)
# -------------------------------------------------------

@bot.on_message(filters.command("string"))
async def string_session(_, msg):
    await msg.reply(
        "🔑 <b>String Session Generator</b>\n"
        "Open this link:\n"
        "https://replit.com/@serena/stringgen"
    )

# -------------------------------------------------------
# TELETHON USER LOGIN (SESSION CONNECT)
# -------------------------------------------------------

@bot.on_message(filters.command("login"))
async def login_start(_, msg):
    user = msg.from_user.id

    await msg.reply(
        "🔐 <b>User Login Mode</b>\n\n"
        "Send your <code>Telethon String Session</code>"
    )

    USER_STRING[user] = "WAITING"

@bot.on_message(filters.private)
async def get_user_session(_, msg):
    user = msg.from_user.id

    # Accept string session
    if user in USER_STRING and USER_STRING[user] == "WAITING":
        string = msg.text.strip()

        try:
            client = TelegramClient(StringSession(string), API_ID, API_HASH)
            await client.connect()

            USER_SESSIONS[user] = client
            USER_STRING[user] = string

            await msg.reply("✅ <b>Session Login Successfully</b>")
            await bot.send_message(LOG_CHANNEL, f"{user} logged in successfully.")

        except Exception as e:
            await msg.reply(f"❌ Login Failed:\n<code>{e}</code>")

# -------------------------------------------------------
# LOGOUT SESSION
# -------------------------------------------------------

@bot.on_message(filters.command("logout"))
async def logout_cmd(_, msg):
    user = msg.from_user.id

    if user in USER_SESSIONS:
        await USER_SESSIONS[user].disconnect()
        USER_SESSIONS.pop(user)
        USER_STRING.pop(user, None)

        await msg.reply("🚪 <b>Logged out successfully.</b>")
        return

    await msg.reply("❌ You are not logged in.")

# -------------------------------------------------------
# SINGLE DOWNLOAD USING USER SESSION
# -------------------------------------------------------

@bot.on_message(filters.command("get"))
async def get_file(_, msg):
    user = msg.from_user.id

    if user not in USER_SESSIONS:
        return await msg.reply("❌ First, login with /login")

    parts = msg.text.split()
    if len(parts) != 2:
        return await msg.reply("Usage: <code>/get message_link</code>")

    link = parts[1]
    client = USER_SESSIONS[user]

    try:
        await msg.reply("⏳ Downloading...")

        entity, msg_id = await client.get_entity_from_link(link)
        m = await client.get_messages(entity, ids=msg_id)

        file = await client.download_media(m)

        await bot.send_document(msg.chat.id, file)
        await bot.send_message(LOG_CHANNEL, f"Downloaded one message for {user}")

    except Exception as e:
        await msg.reply(f"❌ Failed:\n<code>{e}</code>")

# -------------------------------------------------------
# BULK DOWNLOAD
# -------------------------------------------------------

@bot.on_message(filters.command("bulk"))
async def bulk_download(_, msg):
    user = msg.from_user.id

    if user not in USER_SESSIONS:
        return await msg.reply("❌ First login using /login")

    parts = msg.text.split()
    if len(parts) != 4:
        return await msg.reply("Usage:\n/bulk from to channel_id")

    start = int(parts[1])
    end = int(parts[2])
    channel = int(parts[3])

    client = USER_SESSIONS[user]

    await msg.reply(f"📦 <b>Bulk Download Started</b>\nRange: {start} → {end}")

    count = 0

    try:
        for msg_id in range(start, end + 1):
            try:
                m = await client.get_messages(channel, ids=msg_id)
                file = await client.download_media(m)
                await bot.send_document(user, file)
                count += 1
            except:
                pass

        await msg.reply(f"✅ <b>Bulk Completed</b>\nDownloaded: {count}")

    except Exception as e:
        await msg.reply(f"❌ Error:\n<code>{e}</code>")

# -------------------------------------------------------
# RUN BOT SAFELY
# -------------------------------------------------------

async def main():
    await bot.start()
    await bot.send_message(LOG_CHANNEL, "🚀 MASTERBOT STARTED SUCCESSFULLY")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
