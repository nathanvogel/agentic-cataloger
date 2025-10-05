# Implementation Plan

- [x] 1. Set up project structure and dependencies

  - Initialize npm project with TypeScript configuration
  - Install dependencies: typescript, @types/node, pg, @types/pg, csv-parse, dotenv
  - Configure tsconfig.json with ES2020 target
  - Create src directory with subdirectories: utils/, parsers/, transformers/, repositories/
  - Add npm scripts for build and import
  - _Requirements: 7.4, 7.5_

- [ ] 2. Create utility functions

  - [ ] 2.1 Implement price parser utility

    - Create utils/price-parser.ts with parsePrice function
    - Handle formats: "CHF 3.95", "4.95", "–.70 (per Stück)"
    - Return null for invalid prices
    - _Requirements: 2.3_

  - [ ] 2.2 Create simple console logger
    - Create utils/logger.ts with info, warn, error functions
    - Add timestamp and log level formatting
    - _Requirements: 8.1, 8.2, 8.3, 8.6_

- [ ] 3. Implement file scanner

  - Create parsers/file-scanner.ts with scanDirectory function
  - Recursively find all CSV files in data directory
  - Extract supermarket name from path (e.g., "coop-ch-products" → "coop")
  - Return array of file paths with metadata
  - _Requirements: 1.1, 1.2, 1.3_

- [ ] 4. Implement CSV parser with streaming

  - Create parsers/csv-parser.ts with parseFile async generator
  - Use csv-parse to stream CSV rows
  - Handle missing "store" column by using supermarket from path
  - Yield normalized row objects
  - _Requirements: 1.4, 2.1, 2.2, 2.5_

- [ ] 5. Implement product transformer

  - Create transformers/product-transformer.ts with transform function
  - Extract attributes using regex: Bio, Fairtrade, Max Havelaar, Demeter, Knospe
  - Parse price using price parser utility
  - Convert has_discount to boolean
  - Parse categories into array
  - Return database-ready product object
  - _Requirements: 2.3, 2.4, 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3_

- [ ] 6. Implement database repository

  - Create repositories/product-repository.ts with ProductRepository class
  - Set up pg.Pool connection from environment variables
  - Implement upsertBatch method with INSERT ... ON CONFLICT
  - Use (name, supermarket, product_url) as conflict key
  - Add transaction handling for batches
  - Implement close method for cleanup
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ] 7. Create main import script

  - Create src/import.ts as entry point
  - Load environment variables with dotenv
  - Initialize database connection and repository
  - Scan for CSV files using file scanner
  - Process each file: parse CSV, transform rows, batch upsert
  - Track statistics: files processed, records inserted/updated/failed
  - Log progress for each file and final summary
  - Handle errors gracefully and continue processing
  - Close database connection on completion
  - _Requirements: 1.5, 2.6, 7.4, 8.1, 8.2, 8.3, 8.4_

- [ ] 8. Add configuration and documentation

  - Create .env.example with database configuration
  - Add package.json script: "import": "tsx src/import.ts"
  - Document usage in README: how to run import, environment variables
  - _Requirements: 7.5, 7.6_

- [ ] 9. Test with real data
  - Run import on actual CSV files
  - Verify products inserted with correct data
  - Re-run import to test upsert (should update, not duplicate)
  - Verify Bio attribute extraction
  - Test database queries: cheapest lemons, Bio filter, supermarket comparison
  - _Requirements: 3.1, 3.2, 4.4, 6.1, 6.2, 6.3_
