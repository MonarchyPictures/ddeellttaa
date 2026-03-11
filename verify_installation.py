#!/usr/bin/env python3
"""
DELTA-9 INSTALLATION VERIFICATION
Run this script to verify all components are in place
"""

import sys
from pathlib import Path

def check_file(path, description):
    """Check if a file exists"""
    if Path(path).exists():
        print(f"[OK] {description}")
        return True
    else:
        print(f"[MISSING] {description}: {path}")
        return False

def check_import(module, description):
    """Check if a module can be imported"""
    try:
        __import__(module)
        print(f"[OK] {description}")
        return True
    except ImportError as e:
        print(f"[ERROR] {description}: {e}")
        return False

def main():
    print("=" * 60)
    print("DELTA-9 INSTALLATION VERIFICATION")
    print("=" * 60)
    
    all_ok = True
    
    # Check core files
    print("\n[Core Files]")
    all_ok &= check_file("app/pipeline/lead_pipeline.py", "Lead Pipeline")
    all_ok &= check_file("app/core/system_guardian.py", "System Guardian")
    all_ok &= check_file("app/core/logging_system.py", "Logging System")
    all_ok &= check_file("app/scrapers/base_hardened.py", "Base Scraper")
    all_ok &= check_file("app/scrapers/scraper_orchestrator.py", "Scraper Orchestrator")
    all_ok &= check_file("app/services/deduplication_service.py", "Deduplication Service")
    all_ok &= check_file("app/startup.py", "Startup Script")
    all_ok &= check_file("app/api/routes/guardian.py", "Guardian API")
    
    # Check deployment files
    print("\n[Deployment Files]")
    all_ok &= check_file("Dockerfile", "Dockerfile")
    all_ok &= check_file("docker-compose.yml", "Docker Compose")
    all_ok &= check_file("railway.toml", "Railway Config")
    all_ok &= check_file("requirements.txt", "Requirements")
    
    # Check documentation
    print("\n[Documentation]")
    all_ok &= check_file("ARCHITECTURE.md", "Architecture Docs")
    all_ok &= check_file("IMPLEMENTATION_SUMMARY.md", "Implementation Summary")
    
    # Check frontend
    print("\n[Frontend]")
    all_ok &= check_file("frontend/src/pages/LiveBuyersPage.jsx", "Live Buyers Page")
    
    # Check Python imports
    print("\n[Python Dependencies]")
    all_ok &= check_import("fastapi", "FastAPI")
    all_ok &= check_import("pydantic", "Pydantic")
    all_ok &= check_import("sqlalchemy", "SQLAlchemy")
    all_ok &= check_import("phonenumbers", "Phone Numbers")
    all_ok &= check_import("psutil", "PSUtil")
    
    print("\n" + "=" * 60)
    if all_ok:
        print("ALL CHECKS PASSED")
        print("Delta-9 is ready for deployment!")
        return 0
    else:
        print("SOME CHECKS FAILED")
        print("Please install missing dependencies or files")
        return 1

if __name__ == "__main__":
    sys.exit(main())
