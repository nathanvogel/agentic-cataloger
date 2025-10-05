# Data Importer

CSV data importer for PostgreSQL using Zapatos for type-safe database interactions.

## Setup

1. Install dependencies:

```bash
yarn install
```

2. Configure environment:

```bash
cp .env.example .env
# Edit .env with your database credentials
```

3. Build the project:

```bash
yarn run build
```

4. Run the importer:

```bash
yarn run import
```

## Project Structure

- `src/utils/` - Utility functions and helpers
- `src/parsers/` - CSV parsing logic
- `src/transformers/` - Data transformation and validation
- `src/repositories/` - Database access layer using Zapatos
