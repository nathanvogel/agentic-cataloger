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

3. Ensure PostgreSQL is running (from repo root):

```bash
docker compose -f legacy/docker-compose.yml up -d
```

Or from `legacy/`: `docker compose up -d`.

4. Build the project (re-run after pulling importer path changes — the CLI runs compiled `dist/`):

```bash
yarn run build
```

## Usage

### Import Data

The importer provides a CLI with auto-documented options. View all available options:

```bash
yarn run import --help
```

Import all CSV files from the default data directory:

```bash
yarn run import
```

Import from a specific directory:

```bash
yarn run import -- --data-dir /path/to/data
```

Import only files from a specific supermarket:

```bash
yarn run import -- --supermarket coop
```

Adjust batch size for performance tuning:

```bash
yarn run import -- --batch-size 1000
```

Combine multiple options (run from `legacy/data-importer/`, or pass an absolute path to repo-root `data/`):

```bash
cd legacy/data-importer
yarn run import -- --supermarket migros --batch-size 250 --data-dir ../../../data
```

### CLI Options

| Option                      | Description                                        | Default               |
| --------------------------- | -------------------------------------------------- | --------------------- |
| `-d, --data-dir <path>`     | Path to the data directory containing CSV files    | repo-root `data/` (default resolves `../../../data` from compiled `dist/`) |
| `-s, --supermarket <name>`  | Filter by supermarket (migros, lidl, coop, denner) | All supermarkets      |
| `-b, --batch-size <number>` | Number of records to process in each batch         | 500                   |
| `-h, --help`                | Display help information                           | -                     |
| `-V, --version`             | Output version number                              | -                     |

### Run Tests

Execute the test suite:

```bash
yarn run test
```

Run tests in watch mode during development:

```bash
yarn run test:watch
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

## Unit Normalization

The importer automatically normalizes product units to enable price comparisons across different package sizes.

### Supported Units

**Weight** (normalized to grams):

- `mg` (milligrams) → converts to `g` (÷ 1000)
- `g` (grams) → standard unit
- `kg` (kilograms) → converts to `g` (× 1000)

**Volume** (normalized to liters):

- `ml` (milliliters) → converts to `L` (÷ 1000)
- `cl` (centiliters) → converts to `L` (÷ 100)
- `l` or `L` (liters) → standard unit

**Length** (normalized to meters):

- `m` (meters) → standard unit (for dental floss, string, etc.)

**Area** (normalized to square meters):

- `m2` (square meters) → standard unit (for foil, paper, etc.)

**Count** (normalized to units):

- `Stk`, `Stk.`, `Stück` (pieces) → converts to `unit`
- `ST` (short form) → converts to `unit`
- `POR` (portions) → converts to `unit`
- `Rol` (rolls) → converts to `unit`
- `PAAR` (pairs) → converts to `unit`
- `BLT` (sheets) → converts to `unit`
- `WG` (wash cycles) → converts to `unit`
- `Bd` (bunches) → converts to `unit`

**Multi-pack:**

- `2x200g` → 400g total
- `6x50cl` → 300cl total
- `4x 1kg` → 4000g total (with space)

### Examples

| Original | Normalized | Calculation    | Use Case          |
| -------- | ---------- | -------------- | ----------------- |
| 500g     | 500 g      | no conversion  | Food items        |
| 1kg      | 1000 g     | 1 × 1000       | Food items        |
| 600mg    | 0.6 g      | 600 ÷ 1000     | Spices, saffron   |
| 50cl     | 0.5 L      | 50 ÷ 100       | Beverages         |
| 750ml    | 0.75 L     | 750 ÷ 1000     | Beverages         |
| 6x50cl   | 3 L        | (6 × 50) ÷ 100 | Multi-pack drinks |
| 50m      | 50 m       | no conversion  | Dental floss      |
| 9m2      | 9 m2       | no conversion  | Aluminum foil     |
| 10Rol    | 10 unit    | count items    | Toilet paper      |
| 8PAAR    | 8 unit     | count items    | Socks, gloves     |
| 15WG     | 15 unit    | count items    | Detergent pods    |

### Database Schema

**Products Table** - Key fields for unit normalization:

- `currency` - Currency code (e.g., "CHF")
- `original_quantity` - Original quantity from product (e.g., 500)
- `original_unit` - Original unit (e.g., "g")
- `normalized_quantity` - Converted quantity (e.g., 500)
- `normalized_unit` - Standard unit (e.g., "g")
- `normalized_price` - Price per normalized unit (e.g., 0.01)

**Standard Units:**

- **g** - Grams (for weight)
- **L** - Liters (for volume)
- **m** - Meters (for length)
- **m2** - Square meters (for area)
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
docker compose -f legacy/docker-compose.yml ps
```

Check database logs (from repo root):

```bash
docker compose -f legacy/docker-compose.yml logs -f postgres
```

## Performance

The importer uses several optimizations:

- **Batch Processing**: Inserts records in configurable batches (default 500)
- **Streaming CSV Parsing**: Processes large files without loading into memory
- **Connection Pooling**: Reuses database connections efficiently
- **Transaction Management**: Groups operations for better performance

For large datasets, adjust the batch size using the CLI:

```bash
yarn run import -- --batch-size 1000
```
