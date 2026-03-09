import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['ENVIRONMENT'] = 'development'

from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Delta 9")

@app.get("/")
def root():
    return {"message": "Delta 9 is RUNNING!", "status": "ok", "url": "http://localhost:8000"}

@app.get("/health")
def health():
    return {"status": "healthy", "version": "1.0.0"}

print("="*60)
print("  DELTA 9 SERVER STARTED!")
print("="*60)
print()
print("  URL: http://localhost:8000")
print("  Health: http://localhost:8000/health")
print()
print("  Press CTRL+C to stop")
print("="*60)

uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
