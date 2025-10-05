# Requirements Document

## Introduction

This feature provides a TypeScript-based data import system to load grocery product data from CSV files into a PostgreSQL database. The system needs to handle multiple supermarket datasets (Coop, Denner, Lidl, Migros), parse CSV files with varying structures, extract product attributes (like "Bio" labels), and support a flexible category system where products can belong to multiple categories. The importer should be robust enough to handle data quality issues and provide clear feedback on the import process.

## Requirements

### Requirement 1: CSV File Discovery and Processing

**User Story:** As a data administrator, I want the system to automatically discover and process all CSV files in the data directory structure, so that I can import all available product data without manually specifying each file.

#### Acceptance Criteria

1. WHEN the import script is executed THEN the system SHALL recursively scan the data directory for all CSV files
2. WHEN CSV files are discovered THEN the system SHALL extract the supermarket name from the directory path (coop-ch-products, denner-ch-products, lidl-ch-products, migros-ch-products)
3. WHEN CSV files are discovered THEN the system SHALL extract the timestamp from the filename or directory structure
4. IF a CSV file cannot be read THEN the system SHALL log an error and continue processing other files
5. WHEN processing multiple files THEN the system SHALL provide progress feedback showing which file is currently being processed

### Requirement 2: CSV Data Parsing and Validation

**User Story:** As a data administrator, I want the system to parse CSV data correctly and validate required fields, so that only valid product records are imported into the database.

#### Acceptance Criteria

1. WHEN parsing a CSV file THEN the system SHALL read the header row to identify column names
2. WHEN parsing product rows THEN the system SHALL extract all standard fields: store, name, url, price, unit, unit_price, price_text, has_discount, discount_info, image_url, scraped_from, category
3. IF the price field contains non-numeric characters THEN the system SHALL extract the numeric value or set it to NULL
4. IF the has_discount field is a string THEN the system SHALL convert it to a boolean value
5. WHEN a required field (name, store) is missing THEN the system SHALL skip that record and log a warning
6. WHEN parsing is complete THEN the system SHALL report the number of valid and invalid records

### Requirement 3: Attribute Extraction and Classification

**User Story:** As a user searching for products, I want products to be tagged with attributes like "Bio" automatically extracted from their names, so that I can filter products by these attributes.

#### Acceptance Criteria

1. WHEN processing a product name THEN the system SHALL detect if it contains "Bio" or "Naturaplan Bio" keywords
2. WHEN "Bio" is detected THEN the system SHALL add a bio: true attribute to the product's JSONB attributes field
3. WHEN processing a product name THEN the system SHALL detect other common attributes (e.g., "Fairtrade", "Max Havelaar", "Demeter", "Knospe")
4. WHEN attributes are detected THEN the system SHALL store them in a normalized format in the attributes JSONB column
5. WHEN no special attributes are detected THEN the system SHALL store an empty JSONB object

### Requirement 4: Category System Implementation

**User Story:** As a user, I want products to be organized into multiple categories, so that I can browse and filter products by category even when they belong to multiple categories.

#### Acceptance Criteria

1. WHEN importing a product THEN the system SHALL extract the category from the CSV's category field
2. WHEN a category is extracted THEN the system SHALL store it in the categories array column
3. WHEN processing categories THEN the system SHALL normalize category names (trim whitespace, handle special characters)
4. IF a product has multiple categories in the source data THEN the system SHALL support storing all categories in the array
5. WHEN querying by category THEN the database indexes SHALL enable fast category-based searches

### Requirement 5: Database Connection and Transaction Management

**User Story:** As a data administrator, I want the import process to use database transactions properly, so that failed imports don't leave the database in an inconsistent state.

#### Acceptance Criteria

1. WHEN the import script starts THEN the system SHALL establish a connection to PostgreSQL using environment variables or configuration
2. WHEN importing a batch of products THEN the system SHALL use a database transaction
3. IF an error occurs during import THEN the system SHALL roll back the transaction for that batch
4. WHEN a transaction is rolled back THEN the system SHALL log the error and continue with the next batch
5. WHEN the import completes THEN the system SHALL close the database connection properly
6. WHEN importing THEN the system SHALL use batch inserts for performance (e.g., 100-500 records per batch)

### Requirement 6: Duplicate Handling and Data Updates

**User Story:** As a data administrator, I want to be able to re-run imports without creating duplicate records, so that I can update product data when new CSV files are available.

#### Acceptance Criteria

1. WHEN importing a product THEN the system SHALL check if a product with the same name, supermarket, and URL already exists
2. IF a duplicate is found THEN the system SHALL update the existing record with new price and attribute data
3. IF a duplicate is found THEN the system SHALL update the scraped_at timestamp
4. WHEN updating records THEN the system SHALL preserve the original product ID
5. WHEN inserting new records THEN the system SHALL create new entries with auto-generated IDs

### Requirement 7: Command-Line Interface and Configuration

**User Story:** As a data administrator, I want to run the import script with command-line options, so that I can control which data to import and how the import behaves.

#### Acceptance Criteria

1. WHEN running the script THEN the system SHALL accept a --supermarket flag to import only specific supermarkets
2. WHEN running the script THEN the system SHALL accept a --dry-run flag to validate data without importing
3. WHEN running the script THEN the system SHALL accept a --batch-size flag to control transaction batch sizes
4. WHEN running the script THEN the system SHALL read database connection details from environment variables (DATABASE_URL or individual DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)
5. WHEN no command-line options are provided THEN the system SHALL import all available data with default settings
6. WHEN the script completes THEN the system SHALL exit with code 0 on success or non-zero on failure

### Requirement 8: Unit Normalization and Standardization

**User Story:** As a user comparing prices, I want all products to be normalized to consistent units (e.g., flour per 1kg, lemons per unit), so that I can accurately compare prices across different package sizes and supermarkets.

#### Acceptance Criteria

1. WHEN importing a product THEN the system SHALL extract the quantity and unit from the unit field in the CSV
2. WHEN a quantity and unit are extracted THEN the system SHALL calculate a normalized price per standard unit
3. WHEN normalizing units THEN the system SHALL use standard base units: kg for weight, L for volume, unit for countable items
4. WHEN a product is measured in grams THEN the system SHALL convert to kilograms (e.g., 500g → 0.5kg, 250g → 0.25kg)
5. WHEN a product is measured in milliliters THEN the system SHALL convert to liters (e.g., 500ml → 0.5L)
6. WHEN a product is sold by count (Stk., Stück, Stk) THEN the system SHALL use "unit" as the standard measure and extract the quantity
7. WHEN a product has multi-pack format (e.g., "2x200g") THEN the system SHALL calculate total quantity (e.g., 400g → 0.4kg)
8. WHEN a product has decimal quantities with European format (e.g., "1,5kg") THEN the system SHALL parse the comma as decimal separator
9. WHEN storing normalized data THEN the system SHALL save: original_quantity, original_unit, normalized_quantity, normalized_unit, normalized_price, currency
10. IF unit extraction fails THEN the system SHALL log a warning and store the product with null normalized values

### Requirement 9: Currency and Unit Data Structure

**User Story:** As a developer querying product data, I want currency and unit information to be explicitly stored in the database schema, so that I can perform accurate price comparisons and handle multi-currency scenarios in the future.

#### Acceptance Criteria

1. WHEN storing a product THEN the system SHALL save the currency code (e.g., "CHF") in a dedicated currency field
2. WHEN storing normalized data THEN the system SHALL save both original and normalized unit information
3. WHEN querying products THEN the database schema SHALL support filtering by normalized_unit
4. WHEN comparing prices THEN the system SHALL ensure all prices include currency information
5. WHEN storing unit data THEN the system SHALL use an enum or constraint for valid unit types: kg, L, unit, m, m2, m3
6. WHEN a product has no price THEN the system SHALL allow null values for price fields but still store unit information

### Requirement 10: Logging and Error Reporting

**User Story:** As a data administrator, I want detailed logs of the import process, so that I can troubleshoot issues and verify that data was imported correctly.

#### Acceptance Criteria

1. WHEN the import starts THEN the system SHALL log the total number of CSV files discovered
2. WHEN processing each file THEN the system SHALL log the filename and number of records being processed
3. WHEN errors occur THEN the system SHALL log detailed error messages including the file, row number, and error reason
4. WHEN the import completes THEN the system SHALL log summary statistics: total records processed, inserted, updated, and failed
5. WHEN running in dry-run mode THEN the system SHALL log what would be imported without making database changes
6. WHEN logging THEN the system SHALL use appropriate log levels (info, warn, error)
7. WHEN unit normalization fails THEN the system SHALL log the product name and reason for failure
