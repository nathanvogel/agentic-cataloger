# Technology Stack

## Database

- PostgreSQL 18 (Alpine)
- Zapatos for type-safe database interactions
- Docker Compose for local development

## Data Importer

- TypeScript with strict mode enabled
- Node.js (ES2020 target)
- CommonJS modules
- Yarn (with PnP) for package management

### Key Libraries

- `csv-parse` - CSV parsing
- `pg` - PostgreSQL client
- `zapatos` - Type-safe database layer
- `dotenv` - Environment configuration
- `vitest` - Testing framework

## Build System

TypeScript compiler (tsc) with:

- Strict type checking
- Source maps and declarations
- Output to `dist/` directory

## Common Commands

### Database

```bash
# Start database
docker-compose up -d

# View logs
docker-compose logs -f postgres

# Connect to database
docker exec -it pricecomp-db psql -U pricecomp_user -d pricecomp_db

# Stop database
docker-compose down

# Remove all data
docker-compose down -v
```

### Data Importer

```bash
# Install dependencies
yarn install

# Build
yarn run build

# Run importer
yarn run import

# Run tests
yarn run test

# Watch mode tests
yarn run test:watch
```

## Database Connection

- Host: localhost
- Port: 5532
- Database: pricecomp_db
- User: pricecomp_user
- Password: abc (development only)
