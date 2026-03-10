from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI()

# Mount static files for images
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def home():
    """Serve the Delta 9 dashboard HTML"""
    return FileResponse("static/landing.html")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/leads")
async def get_leads():
    return {
        "signals_scanned": 0,
        "buyers_found": 0,
        "leads": []
    }
