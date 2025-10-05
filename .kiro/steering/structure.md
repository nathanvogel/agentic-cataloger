# Project Structure

## Root Layout

```
/data/                    # CSV data files organized by supermarket
/data-importer/           # TypeScript importer application
/db/                      # Database initialization scripts
docker-compose.yml        # PostgreSQL container configuration
```

## Data Directory

Organized by supermarket and date:

```
/data/{supermarket}-ch-products/
  /YYYY/MM/DD-HH:MM.csv
```

Supermarkets: `coop`, `denner`, `lidl`, `migros`

## Data Importer Structure

```
/data-importer/
  /src/
    /parsers/           # CSV parsing and file scanning logic
    /transformers/      # Data transformation and validation
    /repositories/      # Database access layer (Zapatos)
    /utils/             # Shared utilities (logger, price parser)
  /dist/                # Compiled JavaScript output
  package.json
  tsconfig.json
  vitest.config.ts
```

## Code Organization Patterns

### Utilities (`/utils/`)

- Pure functions with clear single responsibilities
- JSDoc comments for all exported functions
- Co-located test files (`.test.ts`)

### Parsers (`/parsers/`)

- File system operations and CSV parsing
- Extract metadata from file paths (supermarket, timestamp)
- Return structured data interfaces

### Transformers (`/transformers/`)

- Data validation and transformation
- Convert CSV rows to database schema

### Repositories (`/repositories/`)

- Database operations using Zapatos
- Type-safe queries and inserts

## Testing Convention

- Test files co-located with source: `{module}.test.ts`
- Use Vitest with Node environment
- Test utilities and parsers with unit tests

## Database Schema

Main table: `products`

- Supermarket constraint: must be one of `migros`, `lidl`, `coop`, `denner`
- JSONB for flexible attributes
- Text arrays for categories
- Full-text search indexes on product names (German)

Views:

- `cheapest_products` - Price rankings
- `category_price_stats` - Materialized view for analytics
