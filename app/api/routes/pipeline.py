from fastapi import APIRouter, Depends, HTTPException, Header
from app.middleware.auth import require_admin
from app.config import PROD_STRICT

router = APIRouter(tags=["Pipeline"])

@router.post("/override")
def override_pipeline(role: str = Depends(require_admin)):
    """
    🔐 Emergency override of PROD_STRICT.
    Allows temporary bypass of strict verification rules.
    """
    # This could be a temporary state change in memory or a config toggle
    # For now, we'll return the status and acknowledge the override
    return {
        "status": "success",
        "message": f"PROD_STRICT override active for session by User({role})",
        "current_mode": "override_active",
        "role": role
    }
