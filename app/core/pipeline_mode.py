import os
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

# 🌍 Pipeline Configuration
# KEEP ONLY: bootstrap (local + dev), strict (production)
# Relaxed mode is DEPRECATED for production.
PIPELINE_MODE = os.getenv("PIPELINE_MODE", "bootstrap").lower()
if PIPELINE_MODE not in ["bootstrap", "strict", "relaxed"]:
    # Fallback to strict for safety if unknown
    PIPELINE_MODE = "bootstrap"

# Single rule: Flexible query-based discovery
PIPELINE_QUERY = os.getenv("PIPELINE_QUERY", "").lower()
PIPELINE_CATEGORY = os.getenv("PIPELINE_CATEGORY", "general").lower()

# 🚀 Bootstrap rules for local development
BOOTSTRAP_RULES = {
    "min_sources": 1,
    "min_confidence": 0.4,
    "allow_unverified": True,
    "label": "Early signal (local)"
}

# 🛡️ Relaxed Production rules (Recommended)
RELAXED_RULES = {
    "min_sources": 1,
    "min_confidence": 0.6,
    "allow_unverified": False,
    "label": "Standard Production"
}

def is_prod() -> bool:
    return PIPELINE_MODE in ["strict", "relaxed"]

def is_strict() -> bool:
    return PIPELINE_MODE == "strict"

def is_bootstrap() -> bool:
    return PIPELINE_MODE == "bootstrap"
