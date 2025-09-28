# Database Migrations Guide

This document provides instructions for managing database migrations in the Social Suit project using Alembic.

## Overview

The project uses Alembic for database schema migrations. Alembic tracks changes to your database schema and provides tools to:

- Generate migration scripts automatically based on model changes
- Apply migrations to update the database schema
- Revert migrations when needed
- Track migration history

## Prerequisites

- Alembic installed (`pip install alembic`)
- Database connection configured in environment variables

## Social Suit Migrations

### Directory Structure

```
social-suit/
├── alembic/
│   ├── versions/       # Migration script files
│   ├── env.py          # Environment configuration
│   └── script.py.mako  # Migration script template
├── alembic.ini         # Alembic configuration
└── scripts/
    ├── generate_migration.py  # Script to generate migrations
    └── run_migrations.py      # Script to run migrations
```

### Using the PowerShell Script

A PowerShell script is provided at the root of the repository to simplify running migration commands:

```powershell
# Generate a new migration
.\db_migrate.ps1 -Project social-suit -Command generate -Message "add user table"

# Apply migrations
.\db_migrate.ps1 -Project social-suit -Command upgrade

# Revert migrations
.\db_migrate.ps1 -Project social-suit -Command downgrade
```

### Environment Variables

The following environment variables are used for database connection:

- `DB_USER`: Database username (default: "postgres")
- `DB_PASSWORD`: Database password (default: "postgres")
- `DB_HOST`: Database host (default: "localhost")
- `DB_PORT`: Database port (default: "5432")
- `DB_NAME`: Database name (default: "social_suit")

### Commands

#### Generate Migrations

To generate a new migration based on model changes:

```bash
python scripts/generate_migration.py "description of changes"
```

This will create a new migration script in the `alembic/versions/` directory.

#### Apply Migrations

To apply all pending migrations:

```bash
python scripts/run_migrations.py
```

To apply migrations up to a specific revision:

```bash
python scripts/run_migrations.py revision_id
```

#### Revert Migrations

To revert the most recent migration:

```bash
python scripts/run_migrations.py --down
```

To revert to a specific revision:

```bash
python scripts/run_migrations.py --down revision_id
```

## Best Practices

1. **Always generate migrations in development environments**, not in production.
2. **Review migration scripts** before applying them to ensure they make the expected changes.
3. **Test migrations** in a staging environment before applying them to production.
4. **Back up your database** before applying migrations in production.
5. **Include migrations in version control** to ensure all developers and environments have the same database schema.
6. **Use descriptive migration messages** to make it easier to understand what each migration does.
7. **Keep migrations small and focused** on specific changes to make them easier to review and troubleshoot.

## Troubleshooting

### Common Issues

1. **Migration conflicts**: If multiple developers create migrations simultaneously, conflicts can occur. Resolve by:
   - Reviewing and merging the conflicting migrations
   - Running `alembic merge` to combine migrations

2. **Failed migrations**: If a migration fails, Alembic will stop and the database may be in an inconsistent state. To recover:
   - Fix the issue in the migration script
   - Run `alembic upgrade head` again
   - Or downgrade to a previous working revision

3. **Model changes not detected**: Ensure all models are imported in `alembic/env.py`.

## Additional Resources

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)