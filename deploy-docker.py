#!/usr/bin/env python3
"""
DELTA-9 DOCKER DEPLOYMENT SCRIPT
Complete local deployment using Docker Compose

Prerequisites:
- Docker installed and running
- Docker Compose installed

Usage: python deploy-docker.py
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime

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
    symbols = {
        "success": "[OK]",
        "warning": "[WARN]",
        "error": "[ERR]",
        "header": "",
        "info": "[--]"
    }
    print(f"[{timestamp}] {symbols.get(status, '[--]')} {msg}")

def run_command(cmd, capture=True):
    """Run shell command"""
    try:
        if capture:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.returncode == 0, result.stdout, result.stderr
        else:
            result = subprocess.run(cmd, shell=True)
            return result.returncode == 0, "", ""
    except Exception as e:
        return False, "", str(e)

def check_docker():
    """Check if Docker is running"""
    print_status("Checking Docker...", "header")
    
    success, stdout, stderr = run_command("docker info")
    if success:
        print_status("Docker is running", "success")
        return True
    else:
        print_status("Docker not running or not installed", "error")
        print_status("Please install Docker Desktop:", "info")
        print_status("  https://www.docker.com/products/docker-desktop", "info")
        return False

def check_docker_compose():
    """Check if Docker Compose is available"""
    print_status("Checking Docker Compose...")
    
    # Try docker compose (v2) first
    success, stdout, stderr = run_command("docker compose version")
    if success:
        print_status("Docker Compose v2 available", "success")
        return "docker compose"
    
    # Try docker-compose (v1)
    success, stdout, stderr = run_command("docker-compose version")
    if success:
        print_status("Docker Compose v1 available", "success")
        return "docker-compose"
    
    print_status("Docker Compose not found", "error")
    return None

def create_directories():
    """Create necessary directories"""
    print_status("Creating directories...", "header")
    
    dirs = ["logs", "postgres_data", "redis_data"]
    for d in dirs:
        Path(d).mkdir(exist_ok=True)
        print_status(f"  {d}/", "success")

def setup_env_file():
    """Create .env file if not exists"""
    if not Path(".env").exists():
        print_status("Creating .env file...")
        
        env_content = """# DELTA-9 LOCAL DOCKER CONFIGURATION

# Database
DATABASE_URL=postgresql://delta9:delta9_secret@postgres:5432/delta9
DB_USER=delta9
DB_PASSWORD=delta9_secret
DB_NAME=delta9

# Redis
REDIS_URL=redis://redis:6379/0

# App
APP_ENV=development
DEBUG=true
SECRET_KEY=local-dev-secret-key
PORT=8000

# Guardian
GUARDIAN_ENABLED=true
GUARDIAN_INTERVAL=60

# Frontend
VITE_API_URL=http://localhost:8000
"""
        with open(".env", "w") as f:
            f.write(env_content)
        print_status(".env file created", "success")

def build_and_start(compose_cmd):
    """Build and start services"""
    print_status("Building and starting services...", "header")
    print_status("This may take a few minutes on first run...")
    
    # Build
    print_status("Building containers...")
    success, stdout, stderr = run_command(f"{compose_cmd} build")
    if not success:
        print_status("Build failed", "error")
        print_status(stderr, "info")
        return False
    
    # Start
    print_status("Starting services...")
    success, stdout, stderr = run_command(f"{compose_cmd} up -d")
    if not success:
        print_status("Failed to start services", "error")
        print_status(stderr, "info")
        return False
    
    print_status("Services started", "success")
    return True

def wait_for_services(compose_cmd):
    """Wait for services to be ready"""
    print_status("Waiting for services to be ready...", "header")
    
    max_attempts = 30
    services = ["postgres", "redis", "backend"]
    
    for service in services:
        print_status(f"  Waiting for {service}...")
        for i in range(max_attempts):
            success, stdout, stderr = run_command(
                f"{compose_cmd} ps {service} | grep -q 'healthy\\|Up'"
            )
            if success:
                print_status(f"    {service} is ready", "success")
                break
            time.sleep(2)
        else:
            print_status(f"    {service} failed to start", "warning")

def show_logs(compose_cmd, service=None):
    """Show logs"""
    print_status("Showing logs (Ctrl+C to exit)...", "header")
    
    if service:
        run_command(f"{compose_cmd} logs -f {service}", capture=False)
    else:
        run_command(f"{compose_cmd} logs -f", capture=False)

def print_summary(compose_cmd):
    """Print deployment summary"""
    print("\n" + "="*60)
    print("DELTA-9 DOCKER DEPLOYMENT COMPLETE")
    print("="*60)
    
    # Get container status
    success, stdout, stderr = run_command(f"{compose_cmd} ps")
    
    print("""
Services:
  Backend API:    http://localhost:8000
  Health Check:   http://localhost:8000/api/guardian/health
  API Docs:       http://localhost:8000/docs
  Frontend:       http://localhost:3000

Container Status:
""")
    if success:
        print(stdout)
    
    print("""
Useful Commands:
  View logs:      docker-compose logs -f
  Stop:           docker-compose down
  Restart:        docker-compose restart
  Shell:          docker-compose exec backend bash
  DB Shell:       docker-compose exec postgres psql -U delta9 -d delta9

Documentation:
  Architecture:   ARCHITECTURE.md
  Quick Start:    README_HARDENED.md
""")
    print("="*60)

def stop_services(compose_cmd):
    """Stop all services"""
    print_status("Stopping services...", "header")
    run_command(f"{compose_cmd} down")
    print_status("Services stopped", "success")

def main():
    """Main deployment flow"""
    print("\n" + "="*60)
    print("DELTA-9 DOCKER DEPLOYMENT")
    print("="*60 + "\n")
    
    # Check Docker
    if not check_docker():
        return 1
    
    # Check Docker Compose
    compose_cmd = check_docker_compose()
    if not compose_cmd:
        return 1
    
    # Setup
    create_directories()
    setup_env_file()
    
    # Build and start
    if not build_and_start(compose_cmd):
        return 1
    
    # Wait for services
    wait_for_services(compose_cmd)
    
    # Print summary
    print_summary(compose_cmd)
    
    # Ask what to do next
    print("\nOptions:")
    print("  1. View logs (all services)")
    print("  2. View backend logs only")
    print("  3. Stop services and exit")
    print("  4. Exit (services keep running)")
    
    choice = input("\nChoice (1-4): ").strip()
    
    if choice == "1":
        try:
            show_logs(compose_cmd)
        except KeyboardInterrupt:
            pass
    elif choice == "2":
        try:
            show_logs(compose_cmd, "backend")
        except KeyboardInterrupt:
            pass
    elif choice == "3":
        stop_services(compose_cmd)
    else:
        print_status("Services are running in the background", "success")
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print_status("\nDeployment interrupted", "info")
        sys.exit(0)
    except Exception as e:
        print_status(f"\nDeployment failed: {str(e)}", "error")
        sys.exit(1)
