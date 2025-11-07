# Database Migrations

This directory contains database setup and migration scripts for the Product Categorization System.

## Useful SQL queries

See the `./queries` subfolder.

## Migration Files

- `001_add_categorization_system.sql`: Adds the core tables and schema for the LLM-powered product categorization system.
- `002_add_token_columns.sql`: Adds separate input/output token tracking columns to the agent_executions table.

## Applying Migrations

### Method 1: Interactive Shell

```bash
# Enter the container
docker exec -it pricecomp-db /bin/sh

# Navigate to migrations directory
cd /docker-entrypoint-initdb.d/migrations

# Apply migration
psql -U pricecomp_user -d pricecomp_db -f 002_add_token_columns.sql
```

### Method 2: Direct Command

```bash
# From host machine
docker exec -i pricecomp-db psql -U pricecomp_user -d pricecomp_db -f /docker-entrypoint-initdb.d/migrations/002_add_token_columns.sql
```

### Method 3: Using the Migration Script

```bash
# Apply specific migration
./db/migrations/apply_migration.sh 002_add_token_columns.sql
```

## Database Backup and Restore

### Creating Backups

```bash
# Enter container
docker exec -it pricecomp-db /bin/sh

# Create compressed backup with timestamp
pg_dump -U pricecomp_user pricecomp_db | gzip > /docker-entrypoint-initdb.d/backups/$(date +%Y-%m-%d-%H-%M)-backup.sql.gz

# Check backup size
ls -lah /docker-entrypoint-initdb.d/backups/
```

### Restoring from Backup

```bash
# Decompress backup
gzip -dk /docker-entrypoint-initdb.d/backups/backup-file.sql.gz

# Restore to existing database (will show errors for existing objects)
psql -U pricecomp_user -d pricecomp_db < /docker-entrypoint-initdb.d/backups/backup-file.sql

# Restore to new database (clean restore)
createdb -U pricecomp_user pricecomp_db_restore
psql -U pricecomp_user -d pricecomp_db_restore < /docker-entrypoint-initdb.d/backups/backup-file.sql
```

## Database Connection Tips

### Common Connection Patterns

```bash
# List databases
psql -l -U pricecomp_user

# Execute file
psql -U pricecomp_user -d pricecomp_db -f migration_file.sql
```

## Verification Queries

### Check table structure

```sql
-- List all tables
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;

-- Check specific table columns
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'agent_executions'
ORDER BY ordinal_position;

-- Check new token columns
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'agent_executions'
AND column_name IN ('input_tokens', 'output_tokens', 'tokens_used');
```

### Check indexes

```sql
-- List all indexes for a table
SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'agent_executions';

-- Check GIN indexes specifically
SELECT indexname, indexdef FROM pg_indexes WHERE indexdef LIKE '%gin%';
```

### Check constraints

```sql
-- List foreign key constraints
SELECT conname, conrelid::regclass AS table_name, confrelid::regclass AS referenced_table
FROM pg_constraint WHERE contype = 'f';
```

## Migration Best Practices

1. **Always backup before migrations**: Create a backup before applying any migration
2. **Create rollback migration files**: Create a file that undo the changes applied by the migration and suffix it with `_rollback`.
3. **Test on restore database**: Apply migrations to a test database first
4. **Use transactions**: Wrap migrations in `BEGIN;` and `COMMIT;` for rollback capability
5. **Check for existing objects**: Migrations should handle "already exists" errors gracefully
6. **Document changes**: Update this README when adding new migrations
