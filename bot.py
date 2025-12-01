import os
import asyncio
from fastapi import FastAPI
from pyrogram import Client, filters
from pyrogram.enums import ParseMode

# -------------------------
# CONFIG
# -------------------------
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
LOG_CHANNEL = int(os.getenv("LOG_CHANNEL", "-1003286415377"))
OWNER_ID = int(os.getenv("OWNER_ID", "1598576202"))

# -------------------------
# BOT CLIENT
# -------------------------
bot = Client(
    "SerenaBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    parse_mode=ParseMode.HTML
)

# -------------------------
# FASTAPI (KEEP ALIVE)
# -------------------------
app = FastAPI()

@app.get("/")
async def home():
    return {"status": "running", "message": "Serena V2 Online"}

# -------------------------
# COMMANDS
# -------------------------

@bot.on_message(filters.command("start"))
async def start_cmd(client, message):
    await message.reply(
        "👋 <b>Welcome!</b>\n\n"
        "Main active hoon. Use /help to explore commands."
    )
    await client.send_message(LOG_CHANNEL, f"START used by {message.from_user.id}")

@bot.on_message(filters.command("help"))
async def help_cmd(client, message):
    await message.reply(
        "📘 <b>Help Menu</b>\n\n"
        "/start – Bot Online Check\n"
        "/help – Commands List\n"
        "/ping – Speed Test\n"
        "/about – Bot Info\n"
    )

@bot.on_message(filters.command("ping"))
async def ping_cmd(client, message):
    await message.reply("🏓 Pong!")

@bot.on_message(filters.command("about"))
async def about_cmd(client, message):
    await message.reply(
        "🤖 <b>Serena V2 Bot</b>\n"
        "Optimized for Render deployment.\n"
        "Fast • Stable • Clean Architecture."
    )

# -------------------------
# AUTO LOGGING ALL EXCEPT COMMANDS
# -------------------------

@bot.on_message(filters.private & ~filters.command(["start", "help", "ping", "about"]))
async def log_all(client, msg):
    try:
        await client.send_message(LOG_CHANNEL, f"User {msg.from_user.id} sent: {msg.text}")
    except:
        pass

# -------------------------
# BOT RUNNER (SAFE)
# -------------------------

async def main():
    print("Starting bot...")
    await bot.start()
    print("Bot started successfully.")

    await bot.send_message(LOG_CHANNEL, "🚀 Serena V2 is now LIVE on Render!")

    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot Stopped.")
