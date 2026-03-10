#!/usr/bin/env python3
"""
Database Management Script for Delta-9

Usage:
    python manage_db.py init          # Create all tables
    python manage_db.py migrate       # Run Alembic migrations
    python manage_db.py reset         # Drop and recreate all tables (DANGER)
    python manage_db.py stats         # Show database statistics
    python manage_db.py seed          # Seed with sample data
    python manage_db.py backup        # Backup database
    python manage_db.py verify        # Verify database connection
"""
import sys
import os
import json
from datetime import datetime, timedelta

# Add app to path
sys.path.insert(0, os.path.dirname(__file__))

from app.models.lead import (
    init_db, reset_db, get_db_stats, engine, Base,
    Lead, Signal, SearchQuery, LeadActivity,
    SessionLocal
)
from app.services.lead_verification import get_verification_service
from app.services.intent_detection import get_intent_service


def cmd_init():
    """Initialize database tables"""
    print("Creating database tables...")
    init_db()
    print("✅ Database initialized successfully")
    
    # Show stats
    stats = get_db_stats()
    print(f"\nCurrent stats: {stats}")


def cmd_migrate():
    """Run Alembic migrations"""
    print("Running database migrations...")
    try:
        from alembic import command
        from alembic.config import Config
        
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        print("✅ Migrations completed")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        print("Make sure Alembic is installed: pip install alembic")


def cmd_reset():
    """Reset database (DANGER: loses all data)"""
    confirm = input("⚠️  This will DELETE ALL DATA. Type 'yes' to confirm: ")
    if confirm != 'yes':
        print("Aborted")
        return
    
    print("Resetting database...")
    reset_db()
    print("✅ Database reset complete")


def cmd_stats():
    """Show database statistics"""
    print("Getting database statistics...")
    stats = get_db_stats()
    
    print("\n" + "=" * 50)
    print("DATABASE STATISTICS")
    print("=" * 50)
    
    for table, count in stats.items():
        print(f"  {table:20s}: {count:>6,}")
    
    print("=" * 50)
    
    # Detailed stats
    db = SessionLocal()
    try:
        # Lead status breakdown
        print("\nLead Status Breakdown:")
        from sqlalchemy import func
        status_counts = db.query(Lead.status, func.count(Lead.id)).group_by(Lead.status).all()
        for status, count in status_counts:
            print(f"  {status:15s}: {count:>6,}")
        
        # Signal source breakdown
        print("\nSignal Source Breakdown:")
        source_counts = db.query(Signal.source, func.count(Signal.id)).group_by(Signal.source).all()
        for source, count in source_counts:
            print(f"  {source:15s}: {count:>6,}")
        
        # Recent activity
        print("\nRecent Activity (24h):")
        recent_signals = db.query(Signal).filter(
            Signal.discovered_at >= datetime.utcnow() - timedelta(hours=24)
        ).count()
        recent_leads = db.query(Lead).filter(
            Lead.first_seen >= datetime.utcnow() - timedelta(hours=24)
        ).count()
        print(f"  Signals: {recent_signals:>6,}")
        print(f"  Leads:   {recent_leads:>6,}")
        
    finally:
        db.close()


def cmd_seed():
    """Seed database with sample data"""
    print("Seeding database with sample data...")
    
    db = SessionLocal()
    try:
        # Create sample search query
        query = SearchQuery(
            original_query="plumber",
            expanded_queries=["need plumber", "looking for plumber", "plumber nairobi"],
            category="services",
            location="Nairobi",
        )
        db.add(query)
        db.commit()
        
        # Create sample signals
        intent_service = get_intent_service()
        verification_service = get_verification_service()
        
        sample_signals = [
            {
                "text": "I need a good plumber in Nairobi ASAP! Please recommend.",
                "author": "homeowner_ke",
                "platform": "reddit",
            },
            {
                "text": "Looking for web development services. Budget is 50k KES.",
                "author": "startup_founder",
                "platform": "twitter",
            },
            {
                "text": "Anyone know a reliable electrician? Urgent help needed.",
                "author": "business_owner",
                "platform": "forum",
            },
        ]
        
        for i, data in enumerate(sample_signals):
            # Analyze intent
            intent = intent_service.analyze(data["text"], "plumber")
            
            # Verify
            signal_data = {
                "text": data["text"],
                "author": data["author"],
                "platform": data["platform"],
                "posted_at": datetime.utcnow().isoformat(),
            }
            verification = verification_service.verify(signal_data)
            
            signal = Signal(
                external_id=f"sample_{i}",
                source=data["platform"],
                content=data["text"],
                author=data["author"],
                query_matched="plumber",
                search_query_id=query.id,
                intent_score=intent.intent_score,
                intent_category=intent.intent_category,
                buying_urgency=intent.buying_urgency,
                verification_score=verification.verification_score,
                verification_status=verification.status.value,
                is_processed=True,
                is_lead=True,
                discovered_at=datetime.utcnow(),
            )
            db.add(signal)
        
        db.commit()
        
        # Create leads from signals
        signals = db.query(Signal).filter(Signal.search_query_id == query.id).all()
        for signal in signals:
            lead = Lead(
                signal_ids=[signal.id],
                sources=[signal.source],
                username=signal.author,
                intent_score=signal.intent_score,
                intent_category=signal.intent_category,
                buying_urgency=signal.buying_urgency,
                verification_score=signal.verification_score,
                status="new",
                first_seen=datetime.utcnow(),
                last_active=datetime.utcnow(),
            )
            db.add(lead)
            
            # Update signal
            signal.lead_id = lead.id
        
        db.commit()
        
        print(f"✅ Seeded {len(sample_signals)} signals and leads")
        
    finally:
        db.close()


def cmd_backup():
    """Backup database (SQLite only)"""
    import shutil
    
    db_url = os.getenv("DATABASE_URL", "sqlite:///./delta9.db")
    
    if not db_url.startswith("sqlite"):
        print("⚠️  Backup only supported for SQLite")
        print("For PostgreSQL, use: pg_dump")
        return
    
    db_path = db_url.replace("sqlite:///", "")
    backup_path = f"delta9_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    
    print(f"Backing up {db_path} to {backup_path}...")
    shutil.copy(db_path, backup_path)
    print(f"✅ Backup created: {backup_path}")


def cmd_verify():
    """Verify database connection"""
    print("Verifying database connection...")
    
    try:
        # Test connection
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
        
        print("✅ Database connection successful")
        
        # Check tables
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print(f"\nTables found ({len(tables)}):")
        for table in tables:
            print(f"  - {table}")
        
        # Expected tables
        expected = ['search_queries', 'signals', 'leads', 'lead_activities', 'lead_analytics']
        missing = [t for t in expected if t not in tables]
        
        if missing:
            print(f"\n⚠️  Missing tables: {missing}")
            print("Run: python manage_db.py init")
        else:
            print("\n✅ All expected tables present")
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1]
    
    commands = {
        'init': cmd_init,
        'migrate': cmd_migrate,
        'reset': cmd_reset,
        'stats': cmd_stats,
        'seed': cmd_seed,
        'backup': cmd_backup,
        'verify': cmd_verify,
    }
    
    if command in commands:
        commands[command]()
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
