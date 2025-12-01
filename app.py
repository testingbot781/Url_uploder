from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"status": "Bot is running ✅", "brand": "Technical Serena"}
