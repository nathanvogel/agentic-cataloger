# Swiss Grocery Price Comparison

Compare prices across Swiss supermarkets: Migros, Lidl, Coop, and Denner.

## Prerequisites

- Docker & Docker Compose
- Node.js v25+ (via nvm recommended)
- Corepack enabled (for Yarn 4.11.0+)

## Setup

### 1. Enable Corepack

Corepack manages the correct Yarn version automatically:

```bash
npm install -g corepack
corepack enable
```

### 2. Start the Database

```bash
docker-compose up -d
```

Wait for PostgreSQL to be ready (about 5-10 seconds):

```bash
docker-compose logs -f postgres
```

## Direct Database Queries

Connect to the database:

```bash
docker exec -it pricecomp-db psql -U pricecomp_user -d pricecomp_db
```

Or use any PostgreSQL client:

- Host: localhost
- Port: 5532
- Database: pricecomp_db
- User: pricecomp_user
- Password: abc

## Stopping the Database

```bash
docker-compose down
```

## Project Structure

See [.kiro/steering/structure.md](.kiro/steering/structure.md)
