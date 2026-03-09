"""Simple Delta 9 server for local testing"""
import os
import sys

# Fix encoding on Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)

os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['ENVIRONMENT'] = 'development'
os.environ['DATABASE_URL'] = 'sqlite:///./delta9.db'
os.environ['REDIS_URL'] = 'redis://localhost:6379/0'

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI(title="Delta 9")

@app.get("/")
def root():
    return {"message": "Delta 9 API", "status": "running", "url": "http://localhost:8000"}

@app.get("/health")
def health():
    return {"status": "healthy", "version": "1.0.0"}

@app.get("/docs-ui", response_class=HTMLResponse)
def docs_ui():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Delta 9 - API Documentation</title>
        <style>
            body { font-family: sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            h1 { color: #e94560; }
            .endpoint { background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 8px; }
            .method { color: #28a745; font-weight: bold; }
            code { background: #e9ecef; padding: 2px 6px; border-radius: 4px; }
        </style>
    </head>
    <body>
        <h1>🎯 Delta 9 API</h1>
        <p>Kenya Lead Intelligence Platform</p>
        
        <h2>Endpoints</h2>
        
        <div class="endpoint">
            <span class="method">GET</span> <code>/</code><br>
            API root - returns basic info
        </div>
        
        <div class="endpoint">
            <span class="method">GET</span> <code>/health</code><br>
            Health check
        </div>
        
        <div class="endpoint">
            <span class="method">POST</span> <code>/api/search</code><br>
            Search for buyer leads<br>
            Body: <code>{"query": "tires", "location": "Kenya"}</code>
        </div>
        
        <h2>Try It</h2>
        <p>Visit <a href="/docs">/docs</a> for interactive Swagger UI</p>
        
        <p><strong>Server is running on:</strong> http://localhost:8000</p>
    </body>
    </html>
    """

if __name__ == "__main__":
    print("="*60)
    print("  DELTA 9 SERVER")
    print("="*60)
    print()
    print("  Starting on http://localhost:8000")
    print()
    print("  Available URLs:")
    print("    http://localhost:8000/       - API Root")
    print("    http://localhost:8000/health - Health Check")
    print("    http://localhost:8000/docs   - Swagger UI")
    print("    http://localhost:8000/docs-ui - Simple Docs")
    print()
    print("  Press CTRL+C to stop")
    print("="*60)
    print()
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
