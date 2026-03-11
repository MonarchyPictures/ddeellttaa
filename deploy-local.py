#!/usr/bin/env python3
"""
DELTA-9 LOCAL DEPLOYMENT SCRIPT
Automated setup and deployment for local development

Usage: python deploy-local.py
"""

import os
import sys
import subprocess
import time
import json
from pathlib import Path
from datetime import datetime

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_status(msg, status="info"):
    """Print colored status message"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    if status == "success":
        print(f"[{timestamp}] {Colors.GREEN}✓{Colors.END} {msg}")
    elif status == "warning":
        print(f"[{timestamp}] {Colors.YELLOW}⚠{Colors.END} {msg}")
    elif status == "error":
        print(f"[{timestamp}] {Colors.RED}✗{Colors.END} {msg}")
    elif status == "header":
        print(f"\n{Colors.BOLD}{Colors.BLUE}{msg}{Colors.END}")
    else:
        print(f"[{timestamp}] {msg}")

def run_command(cmd, capture=True):
    """Run shell command and return result"""
    try:
        if capture:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.returncode == 0, result.stdout, result.stderr
        else:
            result = subprocess.run(cmd, shell=True)
            return result.returncode == 0, "", ""
    except Exception as e:
        return False, "", str(e)

def check_python_version():
    """Check Python version"""
    print_status("Checking Python version...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 11:
        print_status(f"Python {version.major}.{version.minor}.{version.micro}", "success")
        return True
    else:
        print_status(f"Python {version.major}.{version.minor} (requires 3.11+)", "warning")
        return False

def check_postgresql():
    """Check if PostgreSQL is running"""
    print_status("Checking PostgreSQL...")
    success, stdout, stderr = run_command("pg_isready -h localhost")
    if success:
        print_status("PostgreSQL is running", "success")
        return True
    else:
        print_status("PostgreSQL not running or not installed", "warning")
        print_status("  To start: brew services start postgresql@15 (Mac)", "info")
        print_status("  Or use Docker: docker run -d -p 5432:5432 postgres:15", "info")
        return False

def check_redis():
    """Check if Redis is running"""
    print_status("Checking Redis...")
    success, stdout, stderr = run_command("redis-cli ping")
    if success and "PONG" in stdout:
        print_status("Redis is running", "success")
        return True
    else:
        print_status("Redis not running or not installed", "warning")
        print_status("  To start: redis-server", "info")
        print_status("  Or use Docker: docker run -d -p 6379:6379 redis:7", "info")
        return False

def setup_database():
    """Setup PostgreSQL database"""
    print_status("Setting up database...", "header")
    
    # Check if database exists
    success, stdout, stderr = run_command(
        "psql -h localhost -U postgres -lqt | cut -d \| -f 1 | grep -w delta9"
    )
    
    if not success or "delta9" not in stdout:
        print_status("Creating database...")
        
        # Create database and user
        commands = [
            "psql -h localhost -U postgres -c \"CREATE USER delta9 WITH PASSWORD 'delta9_secret';\"",
            "psql -h localhost -U postgres -c \"CREATE DATABASE delta9 OWNER delta9;\"",
            "psql -h localhost -U postgres -c \"GRANT ALL PRIVILEGES ON DATABASE delta9 TO delta9;\""
        ]
        
        for cmd in commands:
            success, stdout, stderr = run_command(cmd)
            if not success:
                print_status(f"Command failed: {cmd}", "warning")
                print_status(f"Error: {stderr}", "info")
        
        print_status("Database created", "success")
    else:
        print_status("Database already exists", "success")

def install_dependencies():
    """Install Python dependencies"""
    print_status("Installing dependencies...", "header")
    
    # Check if virtual environment exists
    if not Path(".venv").exists():
        print_status("Creating virtual environment...")
        run_command("python -m venv .venv")
    
    # Activate and install
    pip_cmd = ".venv/bin/pip" if os.name != 'nt' else ".venv\\Scripts\\pip"
    
    print_status("Upgrading pip...")
    run_command(f"{pip_cmd} install --upgrade pip")
    
    print_status("Installing requirements (this may take a few minutes)...")
    success, stdout, stderr = run_command(f"{pip_cmd} install -r requirements.txt")
    
    if success:
        print_status("Dependencies installed", "success")
        return True
    else:
        print_status("Failed to install dependencies", "error")
        print_status(stderr, "info")
        return False

def run_verification():
    """Run installation verification"""
    print_status("Running verification...", "header")
    success, stdout, stderr = run_command("python verify_installation.py")
    print(stdout)
    return success

def init_database_schema():
    """Initialize database tables"""
    print_status("Initializing database schema...", "header")
    
    # Create init script
    init_sql = """
CREATE TABLE IF NOT EXISTS leads (
    id VARCHAR(32) PRIMARY KEY,
    query VARCHAR(255) NOT NULL,
    text TEXT NOT NULL,
    phone VARCHAR(20) NOT NULL,
    source_platform VARCHAR(50) NOT NULL,
    source_name VARCHAR(255) NOT NULL,
    source_url TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    location VARCHAR(100) NOT NULL,
    intent_score INTEGER NOT NULL,
    temperature VARCHAR(20),
    lead_hash VARCHAR(32) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_leads_phone ON leads(phone);
CREATE INDEX IF NOT EXISTS idx_leads_timestamp ON leads(timestamp);
CREATE INDEX IF NOT EXISTS idx_leads_source ON leads(source_platform);
CREATE INDEX IF NOT EXISTS idx_leads_temperature ON leads(temperature);

CREATE TABLE IF NOT EXISTS scraper_heartbeats (
    id SERIAL PRIMARY KEY,
    scraper_id VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    leads_collected INTEGER DEFAULT 0,
    last_run TIMESTAMP,
    errors INTEGER DEFAULT 0,
    memory_mb FLOAT,
    cpu_percent FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pipeline_logs (
    id SERIAL PRIMARY KEY,
    lead_hash VARCHAR(32),
    action VARCHAR(50) NOT NULL,
    reason VARCHAR(100),
    stage VARCHAR(50),
    processing_time_ms FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""
    
    # Write to temp file and execute
    with open("init_db.sql", "w") as f:
        f.write(init_sql)
    
    success, stdout, stderr = run_command(
        "psql -h localhost -U delta9 -d delta9 -f init_db.sql"
    )
    
    if success:
        print_status("Database schema initialized", "success")
    else:
        print_status("Schema initialization failed", "warning")
        print_status(stderr, "info")

def start_backend():
    """Start backend server"""
    print_status("Starting backend server...", "header")
    print_status("API will be available at: http://localhost:8000")
    print_status("Health check: http://localhost:8000/api/guardian/health")
    print_status("\nPress Ctrl+C to stop\n")
    
    python_cmd = ".venv/bin/python" if os.name != 'nt' else ".venv\\Scripts\\python"
    
    # Start with unbuffered output
    os.environ["PYTHONUNBUFFERED"] = "1"
    
    try:
        subprocess.run([
            python_cmd, "-m", "uvicorn", "app.main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000",
            "--reload",
            "--log-level", "info"
        ])
    except KeyboardInterrupt:
        print_status("\nBackend stopped", "info")

def start_frontend():
    """Start frontend development server"""
    print_status("Starting frontend...", "header")
    print_status("Frontend will be available at: http://localhost:5173")
    
    os.chdir("frontend")
    
    # Check if node_modules exists
    if not Path("node_modules").exists():
        print_status("Installing frontend dependencies...")
        run_command("npm install", capture=False)
    
    try:
        run_command("npm run dev", capture=False)
    except KeyboardInterrupt:
        print_status("\nFrontend stopped", "info")

def print_deployment_summary():
    """Print deployment summary"""
    print("\n" + "="*60)
    print("DELTA-9 LOCAL DEPLOYMENT SUMMARY")
    print("="*60)
    print("""
Services:
  Backend API:    http://localhost:8000
  Health Check:   http://localhost:8000/api/guardian/health
  API Docs:       http://localhost:8000/docs
  Frontend:       http://localhost:5173 (if started)

Environment:
  Database:       postgresql://delta9:***@localhost:5432/delta9
  Redis:          redis://localhost:6379/0
  Debug Mode:     true

Useful Commands:
  Check health:   curl http://localhost:8000/api/guardian/health
  View logs:      tail -f logs/delta9.log
  Restart:        Ctrl+C, then python deploy-local.py

Documentation:
  Architecture:   ARCHITECTURE.md
  Quick Start:    README_HARDENED.md
    """)
    print("="*60)

def main():
    """Main deployment flow"""
    print("\n" + "="*60)
    print("DELTA-9 LOCAL DEPLOYMENT")
    print("Production-Grade Hardened Architecture v2.0")
    print("="*60 + "\n")
    
    # Pre-flight checks
    print_status("Running pre-flight checks...", "header")
    
    checks = {
        "Python 3.11+": check_python_version(),
        "PostgreSQL": check_postgresql(),
        "Redis": check_redis(),
    }
    
    # Setup database if PostgreSQL is available
    if checks["PostgreSQL"]:
        setup_database()
    else:
        print_status("\nDatabase not available. Setup will continue but may fail.", "warning")
        print_status("Please start PostgreSQL first:\n", "info")
        print_status("  Mac:    brew services start postgresql@15", "info")
        print_status("  Linux:  sudo service postgresql start", "info")
        print_status("  Docker: docker run -d --name delta9-postgres -p 5432:5432 -e POSTGRES_PASSWORD=delta9_secret postgres:15\n", "info")
        
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return 1
    
    # Install dependencies
    if not install_dependencies():
        print_status("Failed to install dependencies", "error")
        return 1
    
    # Run verification
    if not run_verification():
        print_status("Verification failed", "warning")
    
    # Initialize database schema
    if checks["PostgreSQL"]:
        init_database_schema()
    
    # Print summary
    print_deployment_summary()
    
    # Start services
    print_status("Starting services...", "header")
    
    # Option to start frontend
    start_fe = input("Start frontend too? (y/n): ").lower() == 'y'
    
    if start_fe:
        # Start frontend in background
        import threading
        fe_thread = threading.Thread(target=start_frontend)
        fe_thread.daemon = True
        fe_thread.start()
        time.sleep(3)
    
    # Start backend (blocking)
    start_backend()
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print_status("\n\nDeployment interrupted by user", "info")
        sys.exit(0)
    except Exception as e:
        print_status(f"\n\nDeployment failed: {str(e)}", "error")
        sys.exit(1)
