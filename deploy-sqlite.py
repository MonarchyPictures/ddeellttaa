#!/usr/bin/env python3
"""
DELTA-9 QUICK DEPLOYMENT (SQLite Version)
For immediate testing without PostgreSQL/Redis

This uses SQLite instead of PostgreSQL and in-memory storage instead of Redis.
NOT for production use!
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

def print_status(msg, status="info"):
    """Print status message"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    symbols = {"success": "[OK]", "error": "[ERR]", "warning": "[WARN]", "info": "[--]"}
    print(f"[{timestamp}] {symbols.get(status, '[--]')} {msg}")

def check_python():
    """Check Python version"""
    print_status("Checking Python...", "header")
    version = sys.version_info
    if version.major == 3 and version.minor >= 11:
        print_status(f"Python {version.major}.{version.minor}.{version.micro}", "success")
        return True
    else:
        print_status(f"Python {version.major}.{version.minor} (3.11+ recommended)", "warning")
        return True  # Continue anyway

def setup_venv():
    """Setup virtual environment"""
    print_status("Setting up virtual environment...", "header")
    
    if not Path(".venv").exists():
        subprocess.run([sys.executable, "-m", "venv", ".venv"])
        print_status("Virtual environment created", "success")
    else:
        print_status("Virtual environment exists", "success")

def install_deps():
    """Install dependencies"""
    print_status("Installing dependencies...", "header")
    
    pip = ".venv/Scripts/pip" if os.name == 'nt' else ".venv/bin/pip"
    
    # Install core dependencies only
    core_deps = [
        "fastapi==0.104.1",
        "uvicorn[standard]==0.24.0",
        "pydantic==2.5.2",
        "sqlalchemy==2.0.23",
        "phonenumbers==8.13.26",
        "psutil==5.9.6",
        "python-multipart==0.0.6",
        "python-dotenv==1.0.0",
        "email-validator==2.1.0",
        "orjson==3.9.10",
    ]
    
    for dep in core_deps:
        print_status(f"  Installing {dep}...")
        subprocess.run([pip, "install", dep], capture_output=True)
    
    print_status("Dependencies installed", "success")

def init_db():
    """Initialize SQLite database"""
    print_status("Initializing SQLite database...", "header")
    
    python = ".venv/Scripts/python" if os.name == 'nt' else ".venv/bin/python"
    
    init_script = """
import sys
sys.path.insert(0, '.')

from sqlalchemy import create_engine, Column, String, Integer, Text, DateTime, Float
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
print("Database initialized successfully!")
"""
    
    with open("init_sqlite.py", "w") as f:
        f.write(init_script)
    
    result = subprocess.run([python, "init_sqlite.py"], capture_output=True, text=True)
    
    if result.returncode == 0:
        print_status("Database initialized", "success")
        Path("init_sqlite.py").unlink()
    else:
        print_status("Database init failed", "error")
        print(result.stderr)

def start_server():
    """Start the backend server"""
    print_status("Starting Delta-9 server...", "header")
    print_status("API: http://localhost:8000")
    print_status("Docs: http://localhost:8000/docs")
    print_status("Health: http://localhost:8000/api/guardian/health")
    print_status("\nPress Ctrl+C to stop\n")
    
    python = ".venv/Scripts/python" if os.name == 'nt' else ".venv/bin/python"
    
    try:
        subprocess.run([
            python, "-m", "uvicorn", "app.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload",
            "--log-level", "info"
        ])
    except KeyboardInterrupt:
        print_status("\nServer stopped", "info")

def main():
    """Main deployment"""
    print("\n" + "="*60)
    print("DELTA-9 QUICK DEPLOYMENT (SQLite Mode)")
    print("="*60)
    print("\nWARNING: This uses SQLite and in-memory storage.")
    print("For production, use PostgreSQL + Redis with docker-compose.\n")
    
    input("Press Enter to continue...")
    
    # Run setup
    check_python()
    setup_venv()
    install_deps()
    init_db()
    
    print("\n" + "="*60)
    print("SETUP COMPLETE")
    print("="*60)
    
    # Start server
    start_server()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_status("\nDeployment interrupted", "info")
    except Exception as e:
        print_status(f"\nError: {e}", "error")
