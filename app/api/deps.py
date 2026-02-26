from fastapi import Request, Header, HTTPException
import os

API_KEY = os.getenv("API_KEY", "")
ENFORCE_API_KEY = os.getenv("ENFORCE_API_KEY", "true").lower() == "true"

def verify_api_key(request: Request, x_api_key: str = Header(None)):
    if request.method == "OPTIONS":
        return
    if ENFORCE_API_KEY and not API_KEY:
        raise HTTPException(status_code=503, detail="API key enforcement enabled but API_KEY is not configured")
    if not x_api_key or x_api_key != API_KEY:
        if ENFORCE_API_KEY:
            raise HTTPException(status_code=401, detail="Invalid API key")
        # Backward-compatible soft mode for non-production local setups
        print(f"WARNING: Invalid API Key: {x_api_key}")
    return x_api_key
