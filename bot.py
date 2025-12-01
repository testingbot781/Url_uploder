import os
import asyncio
from pyrogram import Client, filters
from motor.motor_asyncio import AsyncIOMotorClient

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 1598576202  # Fixed Owner ID
LOG_CHANNEL = -1003286415377  # Fixed Logs Channel
MONGO_URL = os.getenv("MONGO_URL")

mongo = AsyncIOMotorClient(MONGO_URL)
db = mongo["serena_bot"]
premium_col = db["premium"]

bot = Client("serena_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

async def send_log(text):
    try:
        await bot.send_message(LOG_CHANNEL, text)
    except:
        pass

@bot.on_message(filters.command("start"))
async def start_cmd(client, message):
    uid = message.from_user.id
    await message.reply("Welcome to Technical Serena Bot ✅")
    await send_log(f"/start {uid}")

@bot.on_message(filters.command("help"))
async def help_cmd(client, message):
    await message.reply(
        "Commands:\n"
        "/start - welcome\n"
        "/help - this info\n"
        "/login - save session\n"
        "/logout - remove session\n"
        "/get <link> - download single\n"
        "/bulk <link> <count> - bulk\n"
        "/addpremium <id> - owner only\n"
        "/removepremium <id> - owner only"
    )

@bot.on_message(filters.command("addpremium") & filters.user(OWNER_ID))
async def add_premium(client, message):
    try:
        uid = int(message.command[1])
        await premium_col.update_one({"user": uid}, {"$set": {"user": uid}}, upsert=True)
        await message.reply("Added to Premium ✅")
        await send_log(f"Premium Added {uid}")
    except:
        await message.reply("Usage: /addpremium <user_id>")

@bot.on_message(filters.command("removepremium") & filters.user(OWNER_ID))
async def remove_premium(client, message):
    try:
        uid = int(message.command[1])
        await premium_col.delete_one({"user": uid})
        await message.reply("Removed from Premium ✅")
        await send_log(f"Premium Removed {uid}")
    except:
        await message.reply("Usage: /removepremium <user_id>")

if __name__ == "__main__":
    bot.run()
