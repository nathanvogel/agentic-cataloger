# Design Document: CSV Data Importer

## Overview

The CSV Data Importer is a TypeScript command-line application that imports grocery product data from multiple CSV files into a PostgreSQL database. The system uses a modular architecture with separate concerns for file discovery, CSV parsing, data transformation, and database operations. It leverages Node.js with TypeScript for type safety and uses established libraries for CSV parsing and PostgreSQL connectivity.

## Architecture

### High-Level Architecture

```
┌─────────────────┐
│   CLI Entry     │
│   (index.ts)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Import Service │ ◄─── Configuration
│  (orchestrator) │
└────────┬────────┘
         │
         ├──────────────┬──────────────┬──────────────┐
         ▼              ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ File Scanner │ │ CSV Parser   │ │ Transformer  │ │ DB Repository│
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
                                                     │
                                                     ▼
                                              ┌──────────────┐
                                              │  PostgreSQL  │
                                              └──────────────┘
```

### Technology Stack

- **Runtime**: Node.js (v18+)
- **Language**: TypeScript (v5+)
- **CSV Parsing**: `csv-parse` (from csv package) - Fast, streaming CSV parser
- **Database**: `pg` (node-postgres) - PostgreSQL client
- **CLI**: `commander` - Command-line argument parsing
- **Logging**: `pino` - Fast JSON logger
- **Environment**: `dotenv` - Environment variable management

### Project Structure

```
src/
├── index.ts                 # CLI entry point
├── config/
│   └── database.ts          # Database configuration
├── services/
│   └── import.service.ts    # Main orchestration service
├── parsers/
│   ├── file-scanner.ts      # File discovery logic
│   └── csv-parser.ts        # CSV parsing logic
├── transformers/
│   └── product.transformer.ts # Data transformation and attribute extraction
├── repositories/
│   └── product.repository.ts  # Database operations
├── models/
│   ├── csv-row.model.ts     # CSV row interface
│   └── product.model.ts     # Database product model
└── utils/
    ├── logger.ts            # Logging utility
    └── price-parser.ts      # Price parsing utility
```

## Components and Interfaces

### 1. CLI Entry Point (index.ts)

**Purpose**: Parse command-line arguments and initiate the import process.

**Interface**:

```typescript
// Command-line options
interface CliOptions {
  supermarket?: string;
  dryRun: boolean;
  batchSize: number;
  dataDir: string;
}
```

**Responsibilities**:

- Parse CLI arguments using commander
- Load environment variables
- Initialize logger
- Create and execute ImportService
- Handle top-level errors and exit codes

### 2. File Scanner (file-scanner.ts)

**Purpose**: Discover CSV files in the data directory structure.

**Interface**:

```typescript
interface CsvFileInfo {
  filePath: string;
  supermarket: string; // extracted from directory name
  timestamp?: Date; // extracted from filename
}

class FileScanner {
  async scanDirectory(
    rootDir: string,
    supermarketFilter?: string
  ): Promise<CsvFileInfo[]>;
  private extractSupermarket(path: string): string;
  private extractTimestamp(filename: string): Date | undefined;
}
```

**Implementation Details**:

- Use Node.js `fs.promises` for async file operations
- Recursively walk directory tree
- Extract supermarket from path pattern: `data/{supermarket}-ch-products/`
- Parse timestamp from filename pattern: `YYYY/MM/DD-HH:MM.csv`
- Filter by supermarket if specified

### 3. CSV Parser (csv-parser.ts)

**Purpose**: Parse CSV files and yield rows as typed objects.

**Interface**:

```typescript
interface CsvRow {
  store?: string; // May be missing in some CSVs
  name: string;
  url: string;
  price?: string;
  unit?: string;
  unit_price?: string;
  price_text?: string;
  has_discount?: string | boolean;
  discount_info?: string;
  image_url?: string;
  scraped_from?: string;
  category?: string;
}

class CsvParser {
  async *parseFile(
    filePath: string,
    supermarket: string
  ): AsyncGenerator<CsvRow>;
  private normalizeRow(row: any, supermarket: string): CsvRow;
}
```

**Implementation Details**:

- Use `csv-parse` with streaming for memory efficiency
- Handle missing "store" column by using supermarket from path
- Yield rows one at a time using async generator
- Handle malformed rows gracefully with error logging

### 4. Product Transformer (product.transformer.ts)

**Purpose**: Transform CSV rows into database-ready product objects with extracted attributes.

**Interface**:

```typescript
interface Product {
  name: string;
  price: number | null;
  price_text: string | null;
  unit: string | null;
  unit_price: string | null;
  is_discounted: boolean;
  discount_info: string | null;
  supermarket: string;
  categories: string[];
  attributes: Record<string, any>;
  image_url: string | null;
  product_url: string;
  scraped_at: Date;
}

class ProductTransformer {
  transform(csvRow: CsvRow, fileInfo: CsvFileInfo): Product;
  private extractAttributes(name: string): Record<string, any>;
  private parsePrice(priceStr: string): number | null;
  private parseBoolean(value: string | boolean): boolean;
  private extractCategories(category: string): string[];
}
```

**Implementation Details**:

- **Attribute Extraction**: Use regex patterns to detect:
  - Bio: `/\b(bio|naturaplan bio)\b/i`
  - Fairtrade: `/\bfairtrade\b/i`
  - Max Havelaar: `/\bmax havelaar\b/i`
  - Demeter: `/\bdemeter\b/i`
  - Knospe: `/\bknospe\b/i`
- **Price Parsing**: Extract numeric value from strings like "CHF 3.95" or "4.95"
- **Category Handling**: Split on delimiters if multiple categories exist, normalize whitespace
- **Validation**: Ensure required fields (name, product_url) are present

### 5. Product Repository (product.repository.ts)

**Purpose**: Handle all database operations for products.

**Interface**:

```typescript
class ProductRepository {
  constructor(pool: pg.Pool);

  async upsertBatch(products: Product[]): Promise<UpsertResult>;
  async findExisting(
    name: string,
    supermarket: string,
    url: string
  ): Promise<Product | null>;
  async beginTransaction(): Promise<pg.PoolClient>;
  async commitTransaction(client: pg.PoolClient): Promise<void>;
  async rollbackTransaction(client: pg.PoolClient): Promise<void>;
  async close(): Promise<void>;
}

interface UpsertResult {
  inserted: number;
  updated: number;
  failed: number;
}
```

**Implementation Details**:

- Use PostgreSQL `INSERT ... ON CONFLICT` for upsert operations
- Conflict detection on: `(name, supermarket, product_url)`
- Batch inserts using parameterized queries
- Transaction management for batch consistency
- Connection pooling for performance

### 6. Import Service (import.service.ts)

**Purpose**: Orchestrate the entire import process.

**Interface**:

```typescript
interface ImportOptions {
  supermarket?: string;
  dryRun: boolean;
  batchSize: number;
  dataDir: string;
}

interface ImportStats {
  filesProcessed: number;
  totalRecords: number;
  inserted: number;
  updated: number;
  failed: number;
  duration: number;
}

class ImportService {
  constructor(
    private fileScanner: FileScanner,
    private csvParser: CsvParser,
    private transformer: ProductTransformer,
    private repository: ProductRepository,
    private logger: Logger
  );

  async import(options: ImportOptions): Promise<ImportStats>;
  private async processFile(
    fileInfo: CsvFileInfo,
    options: ImportOptions
  ): Promise<void>;
  private async processBatch(
    products: Product[],
    dryRun: boolean
  ): Promise<UpsertResult>;
}
```

**Implementation Details**:

- Discover files using FileScanner
- Process files sequentially to avoid overwhelming the database
- Accumulate products in batches (default 500)
- Transform and validate each product
- Upsert batches with transaction management
- Track statistics throughout the process
- Handle errors gracefully, continuing with next file/batch

## Data Models

### CSV Row Model

```typescript
// Represents a raw CSV row with optional fields
interface CsvRow {
  store?: string;
  name: string;
  url: string;
  price?: string;
  unit?: string;
  unit_price?: string;
  price_text?: string;
  has_discount?: string | boolean;
  discount_info?: string;
  image_url?: string;
  scraped_from?: string;
  category?: string;
}
```

### Product Model

```typescript
// Represents a product ready for database insertion
interface Product {
  name: string;
  price: number | null;
  price_text: string | null;
  unit: string | null;
  unit_price: string | null;
  is_discounted: boolean;
  discount_info: string | null;
  supermarket: "migros" | "lidl" | "coop" | "denner";
  categories: string[];
  attributes: Record<string, any>; // JSONB in database
  image_url: string | null;
  product_url: string;
  scraped_at: Date;
}
```

### Database Schema Mapping

The existing database schema already supports our needs:

- `categories TEXT[]` - Maps to Product.categories
- `attributes JSONB` - Maps to Product.attributes
- Indexes on categories (GIN) and attributes (GIN) for fast queries
- Full-text search index on name

## Error Handling

### Error Categories

1. **File System Errors**

   - Missing data directory
   - Unreadable CSV files
   - **Handling**: Log error, skip file, continue with others

2. **CSV Parsing Errors**

   - Malformed CSV rows
   - Missing required columns
   - **Handling**: Log warning with row number, skip row, continue

3. **Data Validation Errors**

   - Invalid price formats
   - Missing required fields
   - **Handling**: Log warning, skip record, continue

4. **Database Errors**

   - Connection failures
   - Transaction failures
   - Constraint violations
   - **Handling**: Rollback transaction, log error, retry batch or skip

5. **Configuration Errors**
   - Missing environment variables
   - Invalid database credentials
   - **Handling**: Fail fast with clear error message

### Error Recovery Strategy

```typescript
// Pseudo-code for error handling flow
try {
  for each file {
    try {
      for each batch {
        try {
          await upsertBatch(products)
        } catch (BatchError) {
          rollback()
          log error
          continue with next batch
        }
      }
    } catch (FileError) {
      log error
      continue with next file
    }
  }
} catch (FatalError) {
  log error
  exit with code 1
}
```

## Testing Strategy

### Unit Tests

1. **Price Parser Tests**

   - Test various price formats: "CHF 3.95", "4.95", "–.70"
   - Test invalid inputs
   - Test null/undefined handling

2. **Attribute Extractor Tests**

   - Test Bio detection: "Naturaplan Bio Apfel", "Bio Milch"
   - Test multiple attributes: "Bio Fairtrade Kaffee"
   - Test case insensitivity
   - Test no attributes found

3. **Category Parser Tests**

   - Test single category
   - Test multiple categories (if format supports)
   - Test normalization (trim, special chars)

4. **Transformer Tests**
   - Test complete CSV row transformation
   - Test missing optional fields
   - Test invalid data handling

### Integration Tests

1. **File Scanner Tests**

   - Create test directory structure
   - Verify correct file discovery
   - Verify supermarket extraction
   - Verify timestamp parsing

2. **CSV Parser Tests**

   - Test with sample CSV files from each supermarket
   - Verify row count matches
   - Verify field mapping

3. **Database Repository Tests**
   - Use test database or transaction rollback
   - Test insert operations
   - Test update operations (upsert)
   - Test batch operations
   - Test transaction rollback

### End-to-End Tests

1. **Full Import Test**

   - Use small test dataset
   - Run complete import
   - Verify database contents
   - Verify statistics accuracy

2. **Dry Run Test**

   - Run with --dry-run flag
   - Verify no database changes
   - Verify logging output

3. **Incremental Import Test**
   - Import dataset once
   - Import same dataset again
   - Verify updates, not duplicates

## Configuration

### Environment Variables

```bash
# Database connection (option 1: connection string)
DATABASE_URL=postgresql://pricecomp_user:abc@localhost:5532/pricecomp_db

# Database connection (option 2: individual settings)
DB_HOST=localhost
DB_PORT=5532
DB_NAME=pricecomp_db
DB_USER=pricecomp_user
DB_PASSWORD=abc

# Optional settings
LOG_LEVEL=info
BATCH_SIZE=500
```

### Command-Line Usage

```bash
# Import all data
npm run import

# Import specific supermarket
npm run import -- --supermarket coop

# Dry run (no database changes)
npm run import -- --dry-run

# Custom batch size
npm run import -- --batch-size 1000

# Combine options
npm run import -- --supermarket lidl --batch-size 250
```

## Performance Considerations

1. **Batch Processing**: Use configurable batch size (default 500) to balance memory usage and database round-trips

2. **Streaming CSV Parsing**: Use async generators to avoid loading entire files into memory

3. **Connection Pooling**: Use pg.Pool for efficient database connection reuse

4. **Indexes**: Leverage existing GIN indexes on categories and attributes for fast queries

5. **Transaction Batching**: Group inserts into transactions to reduce commit overhead

6. **Parallel Processing**: Initially process files sequentially; can be enhanced later with worker threads if needed

## Future Enhancements

1. **Parallel File Processing**: Use worker threads to process multiple files simultaneously
2. **Incremental Updates**: Track last import timestamp to only process new files
3. **Data Validation Rules**: Add configurable validation rules for data quality
4. **Progress Bar**: Add visual progress indicator for long imports
5. **Category Mapping**: Add configuration file to map/normalize category names across supermarkets
6. **Deduplication**: Implement fuzzy matching to detect duplicate products across supermarkets
