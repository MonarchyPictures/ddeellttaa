#!/usr/bin/env python3
"""
DELTA-9 QUICK DEPLOYMENT (SQLite Version) - AUTOMATED
For immediate testing without PostgreSQL/Redis
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

# Set environment for SQLite mode
os.environ["DATABASE_URL"] = "sqlite:///./delta9.db"
os.environ["REDIS_URL"] = ""
os.environ["APP_ENV"] = "development"
os.environ["DEBUG"] = "true"
os.environ["SECRET_KEY"] = "local-dev-key"
os.environ["PYTHONPATH"] = "."

def print_status(msg, status="info"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    symbols = {"success": "[OK]", "error": "[ERR]", "warning": "[WARN]", "info": "[--]", "header": ""}
    if status == "header":
        print(f"\n{'='*60}\n{msg}\n{'='*60}")
    else:
        print(f"[{timestamp}] {symbols.get(status, '[--]')} {msg}")

def run_cmd(cmd, capture=True):
    try:
        if capture:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.returncode == 0, result.stdout, result.stderr
        else:
            return subprocess.run(cmd, shell=True).returncode == 0, "", ""
    except Exception as e:
        return False, "", str(e)

print_status("DELTA-9 SQLITE DEPLOYMENT", "header")

# Check Python
print_status("Checking Python...")
v = sys.version_info
print_status(f"Python {v.major}.{v.minor}.{v.micro}", "success")

# Setup venv
print_status("Setting up virtual environment...", "header")
if not Path(".venv").exists():
    subprocess.run([sys.executable, "-m", "venv", ".venv"])
    print_status("Created virtual environment", "success")
else:
    print_status("Virtual environment exists", "success")

pip = ".venv/Scripts/pip" if os.name == 'nt' else ".venv/bin/pip"
python = ".venv/Scripts/python" if os.name == 'nt' else ".venv/bin/python"

# Install deps
print_status("Installing dependencies...", "header")
core_deps = [
    "fastapi==0.104.1", "uvicorn[standard]==0.24.0", "pydantic==2.5.2",
    "sqlalchemy==2.0.23", "phonenumbers==8.13.26", "psutil==5.9.6",
    "python-multipart==0.0.6", "python-dotenv==1.0.0", "email-validator==2.1.0"
]

for i, dep in enumerate(core_deps):
    print_status(f"[{i+1}/{len(core_deps)}] Installing {dep}...")
    run_cmd(f"{pip} install {dep}")

print_status("Dependencies installed", "success")

# Init DB
print_status("Initializing SQLite database...", "header")

init_script = '''
import sys
sys.path.insert(0, '.')
from sqlalchemy import create_engine, Column, String, Integer, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()
engine = create_engine('sqlite:///./delta9.db', echo=False)

class Lead(Base):
    __tablename__ = 'leads'
    id = Column(String(32), primary_key=True)
    query = Column(String(255), nullable=False)
    text = Column(Text, nullable=False)
    phone = Column(String(20), nullable=False)
    source_platform = Column(String(50), nullable=False)
    source_name = Column(String(255), nullable=False)
    source_url = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    location = Column(String(100), nullable=False)
    intent_score = Column(Integer, nullable=False)
    temperature = Column(String(20))
    lead_hash = Column(String(32), unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(engine)
print("Database initialized!")
'''

with open("init_sqlite.py", "w") as f:
    f.write(init_script)

run_cmd(f"{python} init_sqlite.py")
Path("init_sqlite.py").unlink()
print_status("Database initialized", "success")

# Print summary
print_status("SETUP COMPLETE", "header")
print("""
Services:
  Backend API:    http://localhost:8000
  API Docs:       http://localhost:8000/docs
  Health Check:   http://localhost:8000/api/guardian/health

Starting server...
Press Ctrl+C to stop
""")

# Start server
try:
    subprocess.run([
        python, "-m", "uvicorn", "app.main:app",
        "--host", "0.0.0.0", "--port", "8000",
        "--reload", "--log-level", "info"
    ])
except KeyboardInterrupt:
    print_status("\nServer stopped", "info")
