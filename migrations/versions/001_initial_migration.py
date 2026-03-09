"""
Initial migration - Create all tables.

Revision ID: 001
Revises: 
Create Date: 2026-03-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all initial tables."""
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(), unique=True, index=True, nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_superuser', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('last_login', sa.DateTime(), nullable=True),
    )
    
    # Create agents table
    op.create_table(
        'agents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('query', sa.String(), nullable=False),
        sa.Column('location', sa.String(), nullable=True),
        sa.Column('interval_hours', sa.Integer(), default=2),
        sa.Column('duration_days', sa.Integer(), default=7),
        sa.Column('start_time', sa.DateTime(), default=sa.func.now()),
        sa.Column('end_time', sa.DateTime()),
        sa.Column('next_run_at', sa.DateTime(), default=sa.func.now(), index=True),
        sa.Column('active', sa.Boolean(), default=True, index=True),
        sa.Column('is_running', sa.Boolean(), default=False, index=True),
        sa.Column('last_heartbeat', sa.DateTime(), default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    
    # Create leads table
    op.create_table(
        'leads',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('buyer_name', sa.String(), nullable=True, index=True),
        sa.Column('title', sa.String(), nullable=False, index=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('product_category', sa.String(), index=True),
        sa.Column('price', sa.String(), nullable=True),
        sa.Column('location', sa.String(), nullable=True),
        sa.Column('source', sa.String(), nullable=False, index=True),
        sa.Column('url', sa.String(), nullable=False, unique=True),
        sa.Column('intent_score', sa.Float(), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), index=True),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agents.id'), nullable=True, index=True),
        sa.Column('query', sa.String(), nullable=True),
        sa.Column('contact_phone', sa.String(), index=True),
        sa.Column('contact_email', sa.String(), index=True),
        sa.Column('quantity_requirement', sa.String()),
        sa.Column('location_raw', sa.String()),
        sa.Column('radius_km', sa.Float(), default=0.0),
        sa.Column('request_timestamp', sa.DateTime(), index=True),
        sa.Column('whatsapp_link', sa.String()),
        sa.Column('contact_method', sa.String()),
        sa.Column('status', sa.String(), default='NEW', index=True),
        sa.Column('http_status', sa.Integer()),
        sa.Column('latency_ms', sa.Integer()),
        sa.Column('is_hot_lead', sa.Integer(), default=0, index=True),
        sa.Column('buyer_request_snippet', sa.String()),
        sa.Column('urgency_level', sa.String(), default='low', index=True),
        sa.Column('confidence_score', sa.Float(), default=0.0, index=True),
        sa.Column('is_saved', sa.Integer(), default=0),
        sa.Column('is_verified_signal', sa.Integer(), default=1, index=True),
        sa.Column('verification_flag', sa.String(), default='verified'),
        sa.Column('notes', sa.String()),
        sa.Column('content_hash', sa.String(), index=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.String(), index=True),
        sa.Column('title', sa.String()),
        sa.Column('message', sa.Text()),
        sa.Column('type', sa.String(), default='info'),
        sa.Column('read', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    
    # Create buyer_leads table
    op.create_table(
        'buyer_leads',
        sa.Column('id', sa.String(), primary_key=True, index=True),
        sa.Column('name', sa.String()),
        sa.Column('platform', sa.String()),
        sa.Column('intent', sa.String()),
        sa.Column('location', sa.String()),
        sa.Column('contact', sa.String()),
        sa.Column('contact_status', sa.String()),
        sa.Column('confidence', sa.Float()),
        sa.Column('posted_at', sa.DateTime()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    
    # Create agent_run_logs table
    op.create_table(
        'agent_run_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agents.id', ondelete='CASCADE'), index=True, nullable=False),
        sa.Column('run_time', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('leads_found', sa.Integer(), default=0),
        sa.Column('errors', sa.Text(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), default=0),
    )
    
    # Create buyer_intents table
    op.create_table(
        'buyer_intents',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.String(), index=True),
        sa.Column('interest_type', sa.String(), index=True),
        sa.Column('vehicle_type', sa.String(), index=True),
        sa.Column('keywords', sa.String(), nullable=True),
        sa.Column('budget_min', sa.Float(), default=0.0),
        sa.Column('budget_max', sa.Float()),
        sa.Column('location', sa.String(), index=True),
        sa.Column('urgency', sa.String(), default='medium'),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('notification_preferences', sa.String(), default='email,sms'),
        sa.Column('is_active', sa.Integer(), default=1),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime()),
    )
    
    # Create search_patterns table
    op.create_table(
        'search_patterns',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('keyword', sa.String(), unique=True),
        sa.Column('category', sa.String()),
        sa.Column('is_active', sa.Integer(), default=1),
    )
    
    # Create activity_logs table
    op.create_table(
        'activity_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('event_type', sa.String(), index=True),
        sa.Column('lead_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('leads.id'), nullable=True),
        sa.Column('session_id', sa.String(), index=True, nullable=True),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.func.now(), index=True),
        sa.Column('extra_metadata', sa.JSON(), nullable=True),
    )
    
    # Create scraper_metrics table
    op.create_table(
        'scraper_metrics',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('scraper_name', sa.String(), unique=True, index=True),
        sa.Column('runs', sa.Integer(), default=0),
        sa.Column('leads_found', sa.Integer(), default=0),
        sa.Column('verified_leads', sa.Integer(), default=0),
        sa.Column('failures', sa.Integer(), default=0),
        sa.Column('consecutive_failures', sa.Integer(), default=0),
        sa.Column('last_success', sa.DateTime()),
        sa.Column('history', sa.JSON()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create category_metrics table
    op.create_table(
        'category_metrics',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('category_name', sa.String(), unique=True, index=True),
        sa.Column('total_leads', sa.Integer(), default=0),
        sa.Column('verified_leads', sa.Integer(), default=0),
        sa.Column('verified_rate', sa.Float(), default=0.0),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create system_settings table
    op.create_table(
        'system_settings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('key', sa.String(), unique=True, index=True),
        sa.Column('value', sa.JSON()),
        sa.Column('updated_at', sa.DateTime()),
    )
    
    # Create cache table
    op.create_table(
        'cache',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('query', sa.String(), index=True),
        sa.Column('location', sa.String(), default='default'),
        sa.Column('data', sa.JSON()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), index=True),
        sa.UniqueConstraint('query', name='uix_cache_query'),
    )
    
    # Create refresh_token_blacklist table (for logout functionality)
    op.create_table(
        'refresh_token_blacklist',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('token_jti', sa.String(), unique=True, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('expires_at', sa.DateTime()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table('refresh_token_blacklist')
    op.drop_table('cache')
    op.drop_table('system_settings')
    op.drop_table('category_metrics')
    op.drop_table('scraper_metrics')
    op.drop_table('activity_logs')
    op.drop_table('search_patterns')
    op.drop_table('buyer_intents')
    op.drop_table('agent_run_logs')
    op.drop_table('buyer_leads')
    op.drop_table('notifications')
    op.drop_table('leads')
    op.drop_table('agents')
    op.drop_table('users')
