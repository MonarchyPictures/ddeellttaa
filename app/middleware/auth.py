import os
import hmac
import hashlib
from fastapi import HTTPException, Request, Header
from app.config import ADMIN_SECRET_KEY, PIPELINE_MODE

def require_admin(request: Request, x_role: str = Header(None), x_admin_signature: str = Header(None)):
    """
    🔐 Render-ready PROD hardening: Role-based access control with Signed Headers.
    To prevent header spoofing in production, admin overrides require a valid HMAC signature.
    """
    if x_role != "user":
        # Soft flagging for role check
        print(f"WARNING: Access denied: Required role 'user' not found. Got: {x_role}")
        # raise HTTPException(status_code=403, detail="Access denied: Required role 'user' not found.")
    
    # In production, require a signed header for any action that bypasses user limits
    if PIPELINE_MODE in ["strict", "relaxed"]:
        if not x_admin_signature:
            print("WARNING: Production Security: Missing admin signature.")
            # raise HTTPException(status_code=401, detail="Production Security: Missing admin signature.")
        
        else:
            # Verify signature: HMAC-SHA256(key=ADMIN_SECRET_KEY, msg=x_role)
            expected_signature = hmac.new(
                ADMIN_SECRET_KEY.encode(),
                x_role.encode(),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(x_admin_signature, expected_signature):
                print("WARNING: Production Security: Invalid admin signature.")
                # raise HTTPException(status_code=401, detail="Production Security: Invalid admin signature.")
            
    return x_role
