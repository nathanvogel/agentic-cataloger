# Database Migrations

This directory contains database migration scripts for the Product Categorization System.

## Migration Files

### 001_add_categorization_system.sql

Adds the core tables and schema for the LLM-powered product categorization system:

**New Tables:**

- `categories` - Stores discovered product categories based on consumer substitutability
- `category_schemas` - Stores JSONSchema definitions for each category's attributes
- `global_attributes` - Centralized registry of all attributes used across categories
- `agent_executions` - Logs all LLM agent interactions for review and debugging

**Products Table Extensions:**

- `category_id` - Foreign key linking products to their discovered category
- `categorization_confidence` - Confidence score for category assignment (0.00-1.00)
- `attributes_extracted_at` - Timestamp when attributes were last extracted

**Indexes:**

- Standard B-tree indexes for foreign keys and frequently queried columns
- GIN indexes on array columns (`product_ids`, `category_ids`, `schema_ids`) for efficient array queries
- Partial indexes for optimized queries on nullable columns

**Triggers:**

- Automatic `updated_at` timestamp updates for `categories` and `global_attributes` tables

**Requirements Addressed:**

- 2.1: Category Registry storage
- 7.1: Product attributes in JSONB with schema validation
- 8.1: Agent execution logging with full LLM input/output
- 8.2: Linking executions to affected entities

## Applying Migrations

### Using Docker (Recommended)

```bash
# Apply migration
docker exec -i pricecomp-db psql -U pricecomp_user -d pricecomp_db < db/migrations/001_add_categorization_system.sql

# Verify migration
docker exec -i pricecomp-db psql -U pricecomp_user -d pricecomp_db -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('categories', 'category_schemas', 'global_attributes', 'agent_executions');"
```

### Using the Migration Script

```bash
# Make script executable (first time only)
chmod +x db/migrations/apply_migration.sh

# Apply specific migration
./db/migrations/apply_migration.sh 001_add_categorization_system.sql
```

## Rolling Back Migrations

```bash
# Rollback using Docker
docker exec -i pricecomp-db psql -U pricecomp_user -d pricecomp_db < db/migrations/001_add_categorization_system_rollback.sql
```

**Warning:** Rolling back will delete all affected data.

## Testing Migrations

Run the test script to verify the migration works correctly:

```bash
docker exec -i pricecomp-db psql -U pricecomp_user -d pricecomp_db < db/migrations/001_test_migration.sql
```

This test script:

1. Creates test data in all new tables
2. Verifies foreign key relationships
3. Tests GIN indexes on array columns
4. Verifies triggers update timestamps
5. Cleans up test data (uses ROLLBACK)

## Verification Queries

### Check all tables exist

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('categories', 'category_schemas', 'global_attributes', 'agent_executions')
ORDER BY table_name;
```

### Check products table extensions

```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'products'
AND column_name IN ('category_id', 'categorization_confidence', 'attributes_extracted_at')
ORDER BY column_name;
```

### Check GIN indexes

```sql
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'agent_executions'
AND indexdef LIKE '%gin%';
```

### Check foreign key constraints

```sql
SELECT conname, conrelid::regclass AS table_name, confrelid::regclass AS referenced_table
FROM pg_constraint
WHERE contype = 'f'
AND conrelid::regclass::text IN ('products', 'categories', 'category_schemas');
```

## Notes

- All timestamps use `TIMESTAMP WITHOUT TIME ZONE` (server local time)
- Array columns use PostgreSQL native array types with GIN indexes for efficient querying
- JSONB columns are used for flexible schema storage and LLM input/output
- Confidence scores are stored as `DECIMAL(3, 2)` allowing values from 0.00 to 1.00
- The migration uses `ON DELETE CASCADE` for category_schemas and `ON DELETE SET NULL` for products
- Triggers automatically maintain `updated_at` timestamps on categories and global_attributes
