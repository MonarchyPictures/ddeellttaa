from app.main import app

if __name__ == "__main__":
    import uvicorn
    import os
    # Binds to 0.0.0.0 to fix host resolution issues
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",  # NOT 127.0.0.1
        port=port,
        reload=True
    )
