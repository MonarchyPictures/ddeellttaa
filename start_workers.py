#!/usr/bin/env python3
"""
Start Celery Workers for Delta-9
Convenience script for local development
"""
import subprocess
import sys
import os
import signal
from pathlib import Path

# Worker configurations
WORKERS = [
    {
        "name": "scraper-1",
        "queue": "scrapers",
        "concurrency": 2,
        "loglevel": "info",
    },
    {
        "name": "scraper-2",
        "queue": "scrapers",
        "concurrency": 2,
        "loglevel": "info",
    },
    {
        "name": "default",
        "queue": "default",
        "concurrency": 2,
        "loglevel": "info",
    },
    {
        "name": "high-priority",
        "queue": "high_priority",
        "concurrency": 4,
        "loglevel": "info",
    },
]


def start_worker(config):
    """Start a single worker process"""
    cmd = [
        sys.executable, "-m", "celery",
        "-A", "app.core.celery_config.celery_app",
        "worker",
        "-Q", config["queue"],
        "-n", f"{config['name']}@%h",
        "--concurrency", str(config["concurrency"]),
        "--loglevel", config["loglevel"],
    ]
    
    print(f"Starting worker: {config['name']} (queue: {config['queue']})")
    
    return subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
    )


def start_beat():
    """Start the Celery beat scheduler"""
    cmd = [
        sys.executable, "-m", "celery",
        "-A", "app.core.celery_config.celery_app",
        "beat",
        "--loglevel", "info",
    ]
    
    print("Starting Celery beat scheduler")
    
    return subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
    )


def main():
    """Main function"""
    print("=" * 60)
    print("Delta 9 - Distributed Worker Manager")
    print("=" * 60)
    print()
    
    # Check if Redis is running
    try:
        import redis
        r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        r.ping()
        print("✅ Redis is connected")
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        print("Make sure Redis is running: redis-server")
        sys.exit(1)
    
    print()
    
    processes = []
    
    try:
        # Start beat scheduler
        beat_proc = start_beat()
        processes.append(("beat", beat_proc))
        
        # Start workers
        for config in WORKERS:
            proc = start_worker(config)
            processes.append((config["name"], proc))
        
        print()
        print("=" * 60)
        print("All workers started. Press Ctrl+C to stop.")
        print("=" * 60)
        print()
        
        # Monitor processes
        while True:
            for name, proc in processes:
                retcode = proc.poll()
                if retcode is not None:
                    print(f"⚠️  Worker '{name}' exited with code {retcode}")
                    
                    # Print remaining output
                    output, _ = proc.communicate()
                    if output:
                        print(output)
                    
                    # Restart worker
                    if name == "beat":
                        new_proc = start_beat()
                    else:
                        config = next(w for w in WORKERS if w["name"] == name)
                        new_proc = start_worker(config)
                    
                    processes = [(n, p) if n != name else (name, new_proc) for n, p in processes]
                    print(f"🔄 Restarted worker: {name}")
            
    except KeyboardInterrupt:
        print()
        print("\nStopping all workers...")
        
        for name, proc in processes:
            print(f"Stopping {name}...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        
        print("All workers stopped.")


if __name__ == "__main__":
    main()
