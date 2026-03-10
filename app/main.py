from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Mount assets only if directory exists (for Railway deployment)
if os.path.isdir("frontend/dist/assets"):
    app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")

@app.get("/", response_class=HTMLResponse)
async def home():
    """Serve the landing page"""
    return FileResponse("static/landing.html")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Serve the dashboard UI"""
    if os.path.exists("frontend/dist/index.html"):
        return FileResponse("frontend/dist/index.html")
    # Fallback to landing page if dashboard not built
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
