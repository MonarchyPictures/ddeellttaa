
from app.db.database import engine
from app.db import models

print("Dropping all tables...")
models.Base.metadata.drop_all(bind=engine)
print("Creating all tables...")
models.Base.metadata.create_all(bind=engine)
print("Database reset successfully.")
