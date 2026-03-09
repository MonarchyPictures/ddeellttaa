# Database Migrations

This directory contains Alembic database migrations for the Delta 9 application.

## Quick Start

### Create a new migration

```bash
# Auto-generate from model changes
alembic revision --autogenerate -m "description of changes"

# Create empty migration
alembic revision -m "description of changes"
```

### Run migrations

```bash
# Upgrade to latest
alembic upgrade head

# Upgrade to specific version
alembic upgrade 001

# Downgrade one version
alembic downgrade -1

# Downgrade to specific version
alembic downgrade 001
```

### Check current status

```bash
# Show current revision
alembic current

# Show migration history
alembic history --verbose
```

## Best Practices

1. **Always review auto-generated migrations** before applying them
2. **Test migrations** on a copy of production data before deploying
3. **Never modify existing migrations** that have been applied to production
4. **Make migrations reversible** when possible
5. **Use transactions** for data migrations

## Environment Variables

Migrations use the `DATABASE_URL` environment variable from your `.env` file.

```bash
# Development (SQLite)
DATABASE_URL=sqlite:///./delta9.db

# Production (PostgreSQL)
DATABASE_URL=postgresql://user:password@localhost/delta9
```
