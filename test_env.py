import os
print("Env DATABASE_URL:", os.environ.get("DATABASE_URL", "NOT SET"))

from app.core.config import settings
print("Settings DATABASE_URL:", settings.DATABASE_URL)
print("Settings ENVIRONMENT:", settings.ENVIRONMENT)
