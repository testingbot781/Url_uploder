Save Restricted Content Bot (safe, session-based)

Files:
- bot.py
- requirements.txt
- runtime.txt
- README.md

Deployment (Render):
1. Create a Git repo with these files.
2. On Render create a Web Service:
   - Build Command: pip install -r requirements.txt
   - Start Command: python bot.py
3. Add environment variables in Render:
   - API_ID
   - API_HASH
   - BOT_TOKEN
   - MONGO_URI
   - (optional) PORT, TMP_DIR
4. Deploy.

Usage:
- /start, /help
- /settings -> Settings panel:
  - Set target chat id (numeric) where saved items should be sent
  - Replace Word (from => to)
  - Remove Word (single token)
  - Session (paste your session string here so bot can read private channels for you)
- /bulk <t.me link> -> bot will ask how many messages (max 500). After each sent message bot sleeps 10s.
- Admin: /add <id>, /remove <id>, /broadcast <text>, /users, /banned, /status

Session strings:
- To access private channels using a user session, generate a session string locally (Telethon/Pyrogram tools) and paste it in Settings -> Session.
- This bot DOES NOT ask for phone numbers or OTPs.

Notes:
- Owner: 1598576202
- Bot log channel: -1003286415377
- This project is designed to avoid OTP/phone collection and follows safe practices.# Url_uploder
