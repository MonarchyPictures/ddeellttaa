#!/usr/bin/env python3
"""
Delta 9 Local Development Startup Script
========================================

Cross-platform startup script for local development.

Usage:
    python start_local.py

Features:
- Creates virtual environment if missing
- Installs dependencies
- Sets up local environment
- Starts the API server
"""

import os
import sys
import subprocess
import venv
from pathlib import Path


def run_command(cmd, description=None):
    """Run a shell command and print status."""
    if description:
        print(f"➜ {description}...")
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ✗ Failed: {result.stderr}")
        return False
    return True


def main():
    print("=" * 60)
    print("  Delta 9 - Local Development Server")
    print("=" * 60)
    print()
    
    # Check Python version
    if sys.version_info < (3, 10):
        print("✗ Python 3.10+ required")
        sys.exit(1)
    
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor}")
    
    # Create virtual environment if missing
    venv_path = Path(".venv")
    if not venv_path.exists():
        print("➜ Creating virtual environment...")
        venv.create(".venv", with_pip=True)
        print("  ✓ Created .venv")
    else:
        print("✓ Virtual environment exists")
    
    # Determine activation script
    if os.name == 'nt':  # Windows
        activate_script = ".venv\\Scripts\\activate"
        python_exe = ".venv\\Scripts\\python.exe"
        pip_exe = ".venv\\Scripts\\pip.exe"
    else:  # Unix/Mac
        activate_script = ".venv/bin/activate"
        python_exe = ".venv/bin/python"
        pip_exe = ".venv/bin/pip"
    
    # Install dependencies
    print("➜ Installing dependencies...")
    result = subprocess.run([pip_exe, "install", "-q", "-r", "requirements.txt"])
    if result.returncode != 0:
        print("  ✗ Failed to install dependencies")
        sys.exit(1)
    print("  ✓ Dependencies installed")
    
    # Copy local environment if .env doesn't exist
    env_file = Path(".env")
    if not env_file.exists():
        print("➜ Creating .env from .env.local...")
        if Path(".env.local").exists():
            with open(".env.local", "r") as f:
                content = f.read()
            with open(".env", "w") as f:
                f.write(content)
            print("  ✓ Created .env")
        else:
            # Create minimal .env
            with open(".env", "w") as f:
                f.write("DATABASE_URL=sqlite:///./intent_radar_local.db\n")
                f.write("PORT=8001\n")
            print("  ✓ Created minimal .env")
    else:
        print("✓ .env file exists")
    
    # Check frontend build
    frontend_dist = Path("frontend/dist")
    if not frontend_dist.exists():
        print("⚠ Frontend build not found at frontend/dist")
        print("  API will work, but UI will not be available.")
        print("  To build: cd frontend && npm install && npm run build")
        print()
    else:
        print("✓ Frontend build found")
    
    # Start server
    print()
    print("=" * 60)
    print("  Starting Delta 9 API Server...")
    print("  API:   http://localhost:8001")
    print("  Docs:  http://localhost:8001/docs")
    print("  Health: http://localhost:8001/health")
    print("=" * 60)
    print()
    
    # Run uvicorn
    os.environ["PYTHONPATH"] = os.getcwd()
    subprocess.run([
        python_exe, "-m", "uvicorn",
        "app.main:app",
        "--host", "0.0.0.0",
        "--port", "8001",
        "--reload"
    ])


if __name__ == "__main__":
    main()
