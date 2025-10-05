# Implementation Plan

- [x] 1. Set up project structure and dependencies

  - Initialize yarn project with TypeScript configuration
  - Install dependencies: typescript, @types/node, pg, @types/pg, csv-parse, dotenv
  - Configure tsconfig.json with ES2020 target
  - Create src directory with subdirectories: utils/, parsers/, transformers/, repositories/
  - Add yarn scripts for build and import
  - _Requirements: 7.4, 7.5_

- [x] 2. Create utility functions

  - [x] 2.1 Implement price parser utility

    - Write tests for parsePrice function covering all formats
    - Create utils/price-parser.ts with parsePrice function
    - Handle formats: "CHF 3.95", "4.95", "–.70 (per Stück)"
    - Return null for invalid prices
    - Verify all tests pass
    - _Requirements: 2.3_

  - [x] 2.2 Create simple console logger
    - Write tests for logger functions (info, warn, error)
    - Create utils/logger.ts with info, warn, error functions
    - Add timestamp and log level formatting
    - Verify all tests pass
    - _Requirements: 8.1, 8.2, 8.3, 8.6_

- [x] 3. Implement file scanner

  - Write tests for scanDirectory function with mock file system
  - Create parsers/file-scanner.ts with scanDirectory function
  - Recursively find all CSV files in data directory
  - Extract supermarket name from path (e.g., "coop-ch-products" → "coop")
  - Return array of file paths with metadata
  - Verify all tests pass
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 4. Implement CSV parser with streaming

  - Write tests for parseFile async generator with sample CSV data
  - Create parsers/csv-parser.ts with parseFile async generator
  - Use csv-parse to stream CSV rows
  - Handle missing "store" column by using supermarket from path
  - Yield normalized row objects
  - Verify all tests pass
  - _Requirements: 1.4, 2.1, 2.2, 2.5_

- [x] 5. Implement product transformer

  - Write tests for transform function covering all attribute extraction scenarios
  - Create transformers/product-transformer.ts with transform function
  - Extract attributes using regex: Bio, Fairtrade, Max Havelaar, Demeter, Knospe
  - Parse price using price parser utility
  - Convert has_discount to boolean
  - Parse categories into array
  - Return database-ready product object
  - Verify all tests pass
  - _Requirements: 2.3, 2.4, 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3_

- [x] 6. Implement unit normalizer

  - [x] 6.1 Create unit models and types

    - Create models/unit.model.ts with UnitInfo, NormalizedUnit, StandardUnit types
    - Define StandardUnit enum: kg, L, unit
    - _Requirements: 8.3, 9.5_

  - [x] 6.2 Implement unit extraction

    - Write tests for extractUnit function with various unit formats
    - Create transformers/unit-normalizer.ts with UnitNormalizer class
    - Implement extractUnit method to parse unit field from CSV
    - Handle weight patterns: /(\d+(?:[.,]\d+)?)\s\*(g|kg)/i
    - Handle volume patterns: /(\d+(?:[.,]\d+)?)\s\*(ml|l)/i
    - Handle count patterns: /(\d+)\s\*(Stk\.?|Stück)/i
    - Handle multi-pack patterns: /(\d+)x(\d+)(g|kg|ml|l)/i
    - Parse European decimal format (replace comma with dot)
    - Return UnitInfo or null if no unit detected
    - Verify all tests pass
    - _Requirements: 8.1, 8.4, 8.5, 8.6, 8.7, 8.8_

  - [x] 6.3 Implement unit normalization

    - Write tests for normalize function with conversion scenarios
    - Implement normalize method to convert to standard units
    - Convert g → kg (÷ 1000)
    - Convert ml → L (÷ 1000)
    - Map Stk/Stück → unit
    - Return NormalizedUnit with original and normalized values
    - Verify all tests pass
    - _Requirements: 8.3, 8.4, 8.5, 8.6_

  - [x] 6.4 Implement normalized price calculation

    - Write tests for calculateNormalizedPrice function
    - Implement calculateNormalizedPrice method
    - Calculate: normalized_price = price / normalized_quantity
    - Handle null prices gracefully
    - Verify all tests pass
    - _Requirements: 8.2_

  - [x] 6.5 Integrate unit normalizer into product transformer
    - Update product-transformer.ts to use UnitNormalizer
    - Extract currency from price_text field (default "CHF")
    - Call unitNormalizer.extractUnit with CSV unit field
    - Call unitNormalizer.normalize if unit extracted
    - Calculate normalized price if normalization succeeded
    - Populate all unit-related fields in Product model
    - Log warning if unit extraction fails
    - Update tests to verify unit normalization
    - _Requirements: 8.1, 8.2, 8.9, 8.10, 10.7_

- [x] 7. Update database schema

  - Update db/init.sql to add new columns to products table
  - Add currency VARCHAR(3) DEFAULT 'CHF'
  - Add original_quantity DECIMAL(10,3)
  - Add original_unit VARCHAR(20)
  - Add normalized_quantity DECIMAL(10,3)
  - Add normalized_unit VARCHAR(10)
  - Add normalized_price DECIMAL(10,2)
  - Add CHECK constraint on normalized_unit for valid values: 'kg', 'L', 'unit'
  - Create index on normalized_unit
  - Create index on normalized_price
  - Create composite index on (normalized_unit, normalized_price)
  - Recreate database with updated schema (docker-compose down -v && docker-compose up -d)
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

- [ ] 8. Implement database repository

  - Write tests for ProductRepository class with mock database connection
  - Create repositories/product-repository.ts with ProductRepository class
  - Set up pg.Pool connection from environment variables
  - Implement upsertBatch method with INSERT ... ON CONFLICT
  - Use (name, supermarket, product_url) as conflict key
  - Include all new unit-related fields in INSERT statement
  - Add transaction handling for batches
  - Implement close method for cleanup
  - Verify all tests pass
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ] 9. Create main import script

  - Write integration tests for import script with mock components
  - Create src/import.ts as entry point
  - Load environment variables with dotenv
  - Initialize database connection and repository
  - Scan for CSV files using file scanner
  - Process each file: parse CSV, transform rows, batch upsert
  - Track statistics: files processed, records inserted/updated/failed
  - Log progress for each file and final summary
  - Handle errors gracefully and continue processing
  - Close database connection on completion
  - Verify all tests pass
  - _Requirements: 1.5, 2.6, 7.4, 10.1, 10.2, 10.3, 10.4_

- [ ] 10. Add configuration and documentation

  - Create .env.example with database configuration
  - Add package.json script: "import": "tsx src/import.ts"
  - Document usage in README: how to run import, environment variables
  - Document unit normalization feature and examples
  - _Requirements: 7.5, 7.6_

- [ ] 11. Test with real data
  - Run import on actual CSV files
  - Verify products inserted with correct data including normalized units
  - Re-run import to test upsert (should update, not duplicate)
  - Verify Bio attribute extraction
  - Verify unit normalization: check products with g→kg, ml→L, Stk→unit conversions
  - Verify normalized prices calculated correctly
  - Test database queries: cheapest products per kg, Bio filter, supermarket comparison
  - Test queries filtering by normalized_unit
  - _Requirements: 3.1, 3.2, 4.4, 6.1, 6.2, 6.3, 8.2, 8.3, 8.4, 8.5, 8.6, 9.3_
