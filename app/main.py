from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")

@app.get("/", response_class=HTMLResponse)
async def home():
    """Serve the landing page"""
    return FileResponse("static/landing.html")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Serve the dashboard UI"""
    return FileResponse("frontend/dist/index.html")

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
