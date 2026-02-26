import os 
from app.core.pipeline_mode import PIPELINE_MODE, PIPELINE_CATEGORY, PIPELINE_QUERY

# Simplified flags
PROD_STRICT = PIPELINE_MODE == "strict"
PROD_RELAXED = PIPELINE_MODE == "relaxed"
BOOTSTRAP = PIPELINE_MODE == "bootstrap"

# --- Render-ready PROD Hardening ---
ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "d9_dev_local_secret_2024")

# Log the status for visibility
import logging
logger = logging.getLogger("Config")
logger.info(f"--- Pipeline Simplified: MODE={PIPELINE_MODE}, QUERY={PIPELINE_QUERY}, CATEGORY={PIPELINE_CATEGORY} ---")
