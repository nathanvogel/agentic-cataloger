#!/bin/bash

# Script to apply database migrations
# Usage: ./apply_migration.sh [migration_file]

set -e

# Database connection details
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5532}"
DB_NAME="${DB_NAME:-pricecomp_db}"
DB_USER="${DB_USER:-pricecomp_user}"
DB_PASSWORD="${DB_PASSWORD:-abc}"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get migration file from argument
MIGRATION_FILE="${1}"
MIGRATION_PATH="$(dirname "$0")/${MIGRATION_FILE}"

echo -e "${YELLOW}=== Database Migration Tool ===${NC}"
echo "Database: ${DB_NAME}"
echo "Host: ${DB_HOST}:${DB_PORT}"
echo "Migration: ${MIGRATION_FILE}"
echo ""

# Check if migration file exists
if [ ! -f "${MIGRATION_PATH}" ]; then
    echo -e "${RED}Error: Migration file not found: ${MIGRATION_PATH}${NC}"
    exit 1
fi

# Check if database is accessible
echo -e "${YELLOW}Checking database connection...${NC}"
export PGPASSWORD="${DB_PASSWORD}"
if ! psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c "SELECT 1;" > /dev/null 2>&1; then
    echo -e "${RED}Error: Cannot connect to database${NC}"
    echo "Make sure PostgreSQL is running: docker-compose up -d"
    exit 1
fi
echo -e "${GREEN}✓ Database connection successful${NC}"
echo ""

# Apply migration
echo -e "${YELLOW}Applying migration...${NC}"
if psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -f "${MIGRATION_PATH}"; then
    echo ""
    echo -e "${GREEN}✓ Migration applied successfully${NC}"
else
    echo ""
    echo -e "${RED}✗ Migration failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}=== Migration Complete ===${NC}"
