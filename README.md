# Technical Serena Bot

**Features:**
- /start - Welcome message
- /help - Command info
- /login - Save session for private channel access
- /logout - Remove saved session
- /get <link> - Download single message content
- /bulk <link> <count> - Download multiple messages
- /addpremium <id> - Add user to premium (Owner only)
- /removepremium <id> - Remove user from premium (Owner only)
- All logs automatically sent to LOG_CHANNEL
- Health check route: `/` returns 200 OK

**Deploy Instructions:**
1. Set environment variables on Render:
   - API_ID
   - API_HASH
   - BOT_TOKEN
   - MONGO_URL
   - PORT (default: 10000)
2. Deploy as Web Service.
3. Run `bot_runner.py` as background process for bot commands.
4. `app.py` serves FastAPI health check.
