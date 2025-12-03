from fastapi import FastAPI
app = FastAPI()
@app.get("/")
async def root():
    return {"status": "ok", "service": "url_uploader_bot"}
