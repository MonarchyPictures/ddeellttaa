import logging
from typing import Optional, Union, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError
from app.db.models import Lead

logger = logging.getLogger(__name__)

def model_to_dict(obj: Lead) -> Dict[str, Any]:
    """Convert SQLAlchemy model to dictionary, excluding internal state."""
    data = {}
    for column in obj.__table__.columns:
        val = getattr(obj, column.name, None)
        if val is not None:
            data[column.name] = val
    return data

def upsert_lead_atomic(db: Session, lead_obj: Union[Lead, Dict[str, Any]]) -> Optional[Lead]:
    """
    🛡️ ATOMIC UPSERT: Inserts lead if new, updates if exists (on source_url).
    Handles race conditions using DB-level locking/constraints.
    """
    try:
        # 1. Convert to dict if needed
        if isinstance(lead_obj, Lead):
            lead_data = model_to_dict(lead_obj)
        else:
            lead_data = lead_obj.copy()

        # Ensure ID is present
        if 'id' not in lead_data:
            import uuid
            lead_data['id'] = uuid.uuid4()
            
        # 2. Determine dialect
        dialect = db.bind.dialect.name
        stmt = None
        
        # 3. Construct Upsert Statement
        if dialect == 'postgresql':
            stmt = pg_insert(Lead).values(**lead_data)
            # Define what to update on conflict
            # We don't want to overwrite everything (e.g. created_at)
            # But we do want to update status, price, etc.
            update_dict = {
                'updated_at': stmt.excluded.updated_at,
                'last_activity': stmt.excluded.last_activity,
                'price': stmt.excluded.price,
                'status': stmt.excluded.status,
                'is_hot_lead': stmt.excluded.is_hot_lead,
                'tap_count': Lead.tap_count + 1,
                'confidence_score': stmt.excluded.confidence_score,
                'intent_score': stmt.excluded.intent_score
            }
            stmt = stmt.on_conflict_do_update(
                index_elements=['source_url'], # Assumes UniqueConstraint on source_url
                set_=update_dict
            )
            
        elif dialect == 'sqlite':
            stmt = sqlite_insert(Lead).values(**lead_data)
            update_dict = {
                'updated_at': stmt.excluded.updated_at,
                'last_activity': stmt.excluded.last_activity,
                'price': stmt.excluded.price,
                'status': stmt.excluded.status,
                'is_hot_lead': stmt.excluded.is_hot_lead,
                'confidence_score': stmt.excluded.confidence_score,
                'intent_score': stmt.excluded.intent_score
            }
            stmt = stmt.on_conflict_do_update(
                index_elements=['source_url'],
                set_=update_dict
            )
        else:
            # Fallback for other DBs (MySQL etc) - explicit merge
            logger.warning(f"⚠️ Unsupported dialect {dialect} for atomic upsert. Using merge.")
            merged = db.merge(Lead(**lead_data))
            db.commit()
            return merged

        # 4. Execute
        db.execute(stmt)
        db.commit()
        
        # 5. Return updated object
        # Since we committed, we can query it back
        return db.query(Lead).filter(Lead.source_url == lead_data['source_url']).first()
            
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity Error in upsert: {e}")
        return None
    except Exception as e:
        db.rollback()
        logger.error(f"Atomic Upsert Failed: {e}")
        return None
