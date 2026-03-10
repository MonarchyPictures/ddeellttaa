"""
Delta 9 - Main Entry Point for Railway
"""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(title="Delta 9", version="3.0.0")

# Static files
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", response_class=HTMLResponse)
def home():
    """Landing page"""
    try:
        with open(os.path.join(static_dir, "landing.html"), "r", encoding="utf-8") as f:
            return f.read()
    except:
        return """
        <!DOCTYPE html>
        <html>
        <head><title>Delta 9</title></head>
        <body style="background:#0f172a; color:white; text-align:center; padding:100px;">
            <h1>Delta 9</h1>
            <p>AI Buyer Discovery Engine</p>
            <a href="/dashboard" style="color:#fbbf24;">Enter Dashboard</a>
        </body>
        </html>
        """

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/dashboard")
def dashboard():
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head><title>Delta 9 Dashboard</title></head>
    <body style="background:#0f172a; color:white; padding:50px;">
        <h1>Delta 9 Dashboard</h1>
        <p>Dashboard loading...</p>
    </body>
    </html>
    """)
