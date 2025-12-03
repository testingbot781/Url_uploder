import os
import asyncio
from aiohttp import web
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

OWNER_ID = int(os.getenv("OWNER_ID"))
LOG_CHANNEL = int(os.getenv("LOG_CHANNEL"))

PORT = int(os.getenv("PORT", 8080))

app = Client(
    "UrlUploaderBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ------------------ WEB SERVER ------------------
async def homepage(request):
    return web.Response(text="Bot is running successfully ✔️")

async def start_webserver():
    server = web.Application()
    server.router.add_get("/", homepage)
    runner = web.AppRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"🌐 WebServer running on port {PORT}")


# -------------- BOT COMMANDS ------------------
@app.on_message(filters.command("start"))
async def start_handler(_, message):
    btn = [
        [InlineKeyboardButton("SETTINGS ⚙️", callback_data="settings")],
        [InlineKeyboardButton("CONTACT ADMIN 👤", url="https://t.me/your_username")]
    ]

    await message.reply_text(
        "👋 Welcome!\nSend me any URL & I will upload file to your channel.",
        reply_markup=InlineKeyboardMarkup(btn)
    )


@app.on_message(filters.command("broadcast") & filters.user(OWNER_ID))
async def broadcast(_, message):
    if not message.reply_to_message:
        return await message.reply("Reply to a message to broadcast.")
    
    sent = 0
    async for user in app.get_chat_members(chat_id=LOG_CHANNEL):
        try:
            await message.reply_to_message.copy(user.user.id)
            sent += 1
        except:
            pass

    await message.reply(f"Broadcast sent to {sent} users.")


@app.on_message(filters.text & ~filters.command(["start", "broadcast"]))
async def url_upload(_, message):
    url = message.text.strip()
    status = await message.reply("Downloading... ⏳")

    try:
        # Download Logic Placeholder
        await asyncio.sleep(3)

        await status.edit("Uploading... 📤")
        await asyncio.sleep(2)

        await app.send_message(
            LOG_CHANNEL,
            f"New File Uploaded from User: {message.from_user.id}"
        )

        await status.edit("Uploaded Successfully ✔️")

    except Exception as e:
        await status.edit(f"❌ Error: {e}")


# ---------------- MAIN RUNNER -----------------
async def main():
    await start_webserver()
    await app.start()
    print("Bot + Webserver Started ✔️")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
