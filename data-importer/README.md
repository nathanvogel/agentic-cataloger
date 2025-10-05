# Data Importer

CSV data importer for Swiss grocery product data. Imports product information from CSV files into PostgreSQL with automatic attribute extraction, unit normalization, and price comparison support.

## Setup

1. Install dependencies:

```bash
yarn install
```

2. Configure environment:

```bash
cp .env.example .env
# Edit .env with your database credentials if needed
```

3. Ensure PostgreSQL is running:

```bash
docker-compose up -d
```

4. Build the project:

```bash
yarn run build
```

## Usage

### Basic Import

Import all CSV files from the data directory:

```bash
yarn run import
```

### Environment Variables

Configure the importer using environment variables in `.env`, see `.env.example`.

## Attribute Extraction

The importer automatically detects and extracts product attributes from product names:

- **Bio**: Organic products (Bio, Naturaplan Bio)
- **Fairtrade**: Fair trade certified products
- **Max Havelaar**: Max Havelaar certified products
- **Demeter**: Demeter certified products
- **Knospe**: Knospe (Bio Suisse) certified products

Attributes are stored in the `attributes` JSONB column for flexible querying.

## Database Schema

### Products Table

Key fields for unit normalization:

- `currency` - Currency code (e.g., "CHF")
- `original_quantity` - Original quantity from product (e.g., 500)
- `original_unit` - Original unit (e.g., "g")
- `normalized_quantity` - Converted quantity (e.g., 0.5)
- `normalized_unit` - Standard unit (e.g., "kg")
- `normalized_price` - Price per normalized unit (e.g., 5.00)

### Standard Units

- **kg** - Kilograms (for weight)
- **L** - Liters (for volume)
- **unit** - Individual items (for count)

## Testing

Run the test suite:

```bash
yarn run test
```

Run tests in watch mode:

```bash
yarn run test:watch
```

## Project Structure

- `src/import.ts` - Main entry point and orchestration
- `src/utils/` - Utility functions (logger, price parser)
- `src/parsers/` - CSV parsing and file scanning logic
- `src/transformers/` - Data transformation, attribute extraction, and unit normalization
- `src/repositories/` - Database access layer using Zapatos
- `src/models/` - TypeScript type definitions

## Troubleshooting

### Database Connection Issues

Ensure PostgreSQL is running:

```bash
docker-compose ps
```

Check database logs:

```bash
docker-compose logs -f postgres
```

## Performance

The importer uses several optimizations:

- **Batch Processing**: Inserts records in configurable batches (default 500)
- **Streaming CSV Parsing**: Processes large files without loading into memory
- **Connection Pooling**: Reuses database connections efficiently
- **Transaction Management**: Groups operations for better performance

For large datasets, adjust the batch size:

```bash
BATCH_SIZE=1000 yarn run import
```
