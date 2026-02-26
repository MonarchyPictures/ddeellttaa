
import re
from typing import List

# 🏭 Industrial/Commercial Category Signals
INDUSTRIAL_KEYWORDS = [
    "pipe", "pvc", "hdpe", "conduit", "cement", "ballast", "sand", "timber",
    "steel", "iron", "construction", "industrial", "machinery", "generator",
    "wholesale", "bulk", "truck", "lorry", "container", "hardware", "electrical",
    "solar", "battery", "pump", "irrigation", "greenhouse", "poultry", "feed",
    "fertilizer", "tractor", "plough", "excavator", "backhoe"
]

def is_industrial_query(query: str) -> bool:
    """Detects if a search query belongs to an industrial or commercial category."""
    if not query:
        return False
    query = query.lower()
    return any(keyword in query for keyword in INDUSTRIAL_KEYWORDS)

def get_industrial_threshold_adjustment(query: str) -> float:
    """Returns a threshold reduction for industrial queries (smarter strict mode)."""
    return -0.05 if is_industrial_query(query) else 0.0
