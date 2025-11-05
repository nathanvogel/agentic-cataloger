# Requirements Document

## Introduction

This feature enables precise product categorization and labeling for Swiss grocery products using an LLM-powered agentic system. The system dynamically discovers categories based on consumer substitutability, generates schemas for each category, and extracts structured attributes to support granular price comparisons. The initial scope focuses on vegetables and fruits ("Gemüse" and "Früchte" categories).

This document marks requirements and acceptance criteria as **[MVP]** (must-have for initial release) or **[POST-MVP]** (future enhancement).

## Glossary

- **LLM Agent**: A Large Language Model that performs specific tasks (categorization, schema generation, attribute extraction) with full context of relevant data
- **Category**: A precise grouping of products that consumers would reasonably substitute for each other (e.g., "lemon" is a category, but "lemon" and "lime" are separate categories)
- **Consumer Substitutability**: The likelihood that a regular shopper would switch from one product to another for everyday purchases
- **Category Schema**: A JSONSchema definition that specifies the attributes and their types for products in a category
- **Global Attribute Registry**: A centralized registry of all attributes used across categories, ensuring consistent naming conventions
- **Attribute Extraction**: The process of identifying and extracting attribute values from product data according to a category schema
- **Agentic System**: A system where LLM agents make decisions based on full context rather than following predefined rules
- **Explicit Attribute**: An attribute directly stated in product name or metadata (e.g., "Bio", "500g", "Gala")
- **Implicit Attribute**: An attribute inferred from LLM reasoning about product characteristics (e.g., "sweet" for Gala apples, "crisp" texture)
- **Quality Indicator**: Explicit marketing or grading terms in product names (e.g., "Extra", "Sélection", "Class I", "Premium", "Primagusto")

## Dependencies and Assumptions

### Data Dependencies

1. **Product Data Quality** [MVP]

   - Assumes product names contain sufficient information for categorization
   - Assumes CSV data includes categories field for initial filtering
   - Assumes product names follow reasonably consistent naming patterns within each supermarket

2. **LLM API Access** [MVP]
   - Requires access to LLM API (OpenAI GPT-4, Anthropic Claude, or similar)
   - Assumes API availability and reasonable rate limits
   - Assumes budget for LLM API costs (estimated based on product volume)

### Maintenance Responsibilities

1. **Category Management** [MVP]

   - LLM agents create initial categories automatically
   - System administrators review and approve category structures
   - **[POST-MVP]** Re-categorization can be triggered when new product patterns emerge

2. **Schema Evolution** [MVP]
   - LLM agents create schemas during initial pipeline run
   - **[POST-MVP]** LLM agents propose schema updates when new attribute patterns are detected
   - **[POST-MVP]** System administrators approve schema changes
   - **[POST-MVP]** Products are re-processed when schemas are updated

## Requirements

### Requirement 1 [MVP]

**User Story:** As a system administrator, I want an LLM agent to automatically discover product categories based on consumer substitutability, so that products are grouped meaningfully for price comparison.

#### Acceptance Criteria

1. WHEN THE Category Discovery Agent receives all products from "Gemüse" and "Früchte" categories, THE agent SHALL analyze product names and group products based on consumer substitutability
2. THE Category Discovery Agent SHALL create separate categories for products that consumers would not reasonably substitute (e.g., lemon and lime SHALL be separate categories)
3. THE Category Discovery Agent SHALL create single categories for products that consumers would substitute (e.g., organic and non-organic lemons SHALL be in the same category)
4. WHEN THE Category Discovery Agent creates a category, THE agent SHALL provide reasoning for the categorization decision
5. **[POST-MVP]** THE Category Discovery Agent SHALL assign a confidence score to each categorization decision

### Requirement 2 [MVP]

**User Story:** As a system administrator, I want discovered categories to be stored in a registry, so that products can be linked to their categories and schemas can be generated.

#### Acceptance Criteria

1. THE Category Registry SHALL store each discovered category with a unique identifier, name, and display name
2. WHEN a category is created, THE Category Registry SHALL store the LLM agent's reasoning
3. THE Category Registry SHALL maintain a count of products assigned to each category
4. THE Category Registry SHALL support querying all categories
5. **[POST-MVP]** THE Category Registry SHALL allow updating category assignments when products are re-categorized

### Requirement 3 [MVP]

**User Story:** As a system administrator, I want an LLM agent to generate JSONSchema definitions for each category by analyzing products in that category, so that attributes are discovered from actual data rather than predefined.

#### Acceptance Criteria

1. WHEN THE Schema Generation Agent receives a category and all its products, THE agent SHALL analyze product variations to identify relevant explicit attributes including certifications, varieties, packaging types, and quality indicators (e.g., "Extra", "Sélection", "Premium", "Class I", "Primagusto")
2. THE Schema Generation Agent SHALL check the Global Attribute Registry for existing attributes before creating new ones
3. WHEN THE Schema Generation Agent identifies a new attribute, THE agent SHALL register it in the Global Attribute Registry with a normalized name following snake_case convention
4. THE Schema Generation Agent SHALL generate a JSONSchema that defines attribute types, constraints, and enum values where applicable
5. THE Schema Generation Agent SHALL provide reasoning for the schema structure and attribute choices

### Requirement 4 [MVP]

**User Story:** As a developer, I want a Global Attribute Registry that maintains consistent attribute naming across all categories, so that cross-category queries and UI generation are possible.

#### Acceptance Criteria

1. THE Global Attribute Registry SHALL store each attribute with a unique normalized name, display name, type, and description
2. THE Global Attribute Registry SHALL enforce snake_case naming convention for all attribute names
3. THE Global Attribute Registry SHALL support querying all attributes by type
4. THE Global Attribute Registry SHALL provide a mechanism for managing normalization rules that map raw attribute values to standardized values (e.g., mapping "Bio", "Naturaplan Bio", "Organic" → standardized value "ORGANIC"; or mapping "500g", "0.5kg" → standardized value 500 with unit "g")
5. **[POST-MVP]** THE Global Attribute Registry SHALL track usage count when an attribute is used in multiple category schemas

### Requirement 5 [MVP]

**User Story:** As a system administrator, I want an LLM agent to extract attribute values for products according to their category schema, so that products have structured, queryable attributes.

#### Acceptance Criteria

1. WHEN THE Attribute Extraction Agent receives a product and its category schema, THE agent SHALL extract attribute values from the product name and metadata
2. THE Attribute Extraction Agent SHALL normalize attribute values according to the schema constraints (e.g., using exact enum values)
3. THE Attribute Extraction Agent SHALL validate extracted attributes against the JSONSchema before storing
4. **[POST-MVP]** WHEN THE Attribute Extraction Agent cannot extract a required attribute with confidence, THE agent SHALL mark the product for manual review
5. **[POST-MVP]** THE Attribute Extraction Agent SHALL provide a confidence score and reasoning for each extraction

### Requirement 6 [MVP]

**User Story:** As a system administrator, I want the agentic system to process products in phases (categorization → schema generation → extraction), so that each phase has the full context it needs.

#### Acceptance Criteria

1. THE Agentic System SHALL execute Phase 1 (Category Discovery) with full access to all products in the target categories
2. WHEN Phase 1 is complete, THE Agentic System SHALL execute Phase 2 (Schema Generation) with full access to all products in each discovered category
3. WHEN Phase 2 is complete, THE Agentic System SHALL execute Phase 3 (Attribute Extraction) with access to each product and its category schema
4. **[POST-MVP]** THE Agentic System SHALL allow manual review and approval between phases
5. **[POST-MVP]** THE Agentic System SHALL support re-running individual phases without affecting other phases

### Requirement 7 [MVP]

**User Story:** As a developer, I want product attributes stored in a JSONB column that conforms to the category schema, so that I can query products by any combination of attributes.

#### Acceptance Criteria

1. THE Product Repository SHALL store extracted attributes in the products table JSONB column
2. THE Product Repository SHALL validate attributes against the category schema before storing
3. THE Product Repository SHALL support querying products by any attribute using PostgreSQL JSONB operators
4. THE Product Repository SHALL support multi-attribute queries (e.g., organic AND packaged)
5. **[POST-MVP]** THE Product Repository SHALL maintain additional indexes on the JSONB column for optimized querying

### Requirement 8 [MVP]

**User Story:** As a system administrator, I want the system to log all LLM agent executions with complete input/output and link to affected entities, so that I can monitor costs, debug issues, and review outputs for quality assurance.

#### Acceptance Criteria

1. THE Agentic System SHALL log each LLM agent execution with phase, status, complete LLM input, complete LLM output, and timestamps
2. THE Agentic System SHALL link each execution to affected product IDs, category IDs, and schema IDs
3. WHEN an LLM agent executes, THE system SHALL record tokens used, duration, model, and provider
4. WHEN an LLM agent execution fails, THE system SHALL log the error message and context
5. THE Agentic System SHALL support marking executions as reviewed with correctness flag and optional reviewer notes
6. THE Agentic System SHALL support querying execution logs by phase, status, model, or affected entities
7. **[POST-MVP]** THE Agentic System SHALL provide reporting on total token usage and estimated costs per phase

### Requirement 9 [MVP]

**User Story:** As a developer, I want an LLM client abstraction that handles retries, rate limiting, and error handling, so that agent operations are reliable.

#### Acceptance Criteria

1. THE LLM Client SHALL support sending prompts to LLM APIs and receiving structured JSON responses
2. WHEN an LLM API call fails due to rate limiting, THE LLM Client SHALL retry with exponential backoff
3. THE LLM Client SHALL validate LLM responses against expected JSONSchema before returning
4. **[POST-MVP]** WHEN an LLM response is invalid, THE LLM Client SHALL retry with clarifying instructions
5. THE LLM Client SHALL enforce timeout limits and maximum retry counts to prevent infinite loops

### Requirement 10 [MVP]

**User Story:** As a system administrator, I want to run the categorization pipeline on existing products in the database, so that I can enrich historical data.

#### Acceptance Criteria

1. THE Agentic System SHALL provide a batch processing mode that operates on existing database records
2. WHEN running in batch mode, THE Agentic System SHALL filter products by category (e.g., "Gemüse" or "Früchte")
3. THE Agentic System SHALL process products in batches to manage memory and API rate limits
4. THE Agentic System SHALL provide progress reporting during batch processing (current/total)
5. WHEN batch processing encounters errors, THE Agentic System SHALL log errors and continue processing remaining products

### Requirement 11 [POST-MVP]

**User Story:** As a developer building a price comparison UI, I want to retrieve category schemas via API, so that I can dynamically generate filter interfaces.

#### Acceptance Criteria

1. **[POST-MVP]** THE Schema Repository SHALL provide an API endpoint to retrieve all categories
2. **[POST-MVP]** THE Schema Repository SHALL provide an API endpoint to retrieve the JSONSchema for a specific category
3. **[POST-MVP]** THE Schema Repository SHALL provide an API endpoint to retrieve all global attributes
4. **[POST-MVP]** WHEN a category schema is retrieved, THE response SHALL include the JSONSchema and attribute metadata (display names, descriptions)
5. **[POST-MVP]** THE Schema Repository SHALL support versioning of schemas to handle schema evolution

### Requirement 12 [MVP]

**User Story:** As a shopper comparing products, I want to filter products by multiple attributes simultaneously, so that I can find exactly what I'm looking for.

#### Acceptance Criteria

1. THE Product Repository SHALL support filtering products by category
2. THE Product Repository SHALL support filtering products by any attribute defined in the category schema
3. WHEN multiple attribute filters are specified, THE Product Repository SHALL return only products matching all criteria
4. **[POST-MVP]** THE Product Repository SHALL support filtering by attribute ranges for numeric attributes (e.g., price between X and Y)
5. THE Product Repository SHALL provide query performance suitable for interactive use (sub-second response times)

### Requirement 13 [POST-MVP]

**User Story:** As a system administrator, I want the system to handle schema evolution gracefully, so that attribute definitions can be refined over time.

#### Acceptance Criteria

1. **[POST-MVP]** THE Schema Repository SHALL support multiple versions of a category schema
2. **[POST-MVP]** WHEN a schema is updated, THE Schema Repository SHALL increment the version number
3. **[POST-MVP]** THE Product Repository SHALL track which schema version was used for attribute extraction
4. **[POST-MVP]** THE Agentic System SHALL support re-extracting attributes for products when a schema is updated
5. **[POST-MVP]** THE Schema Repository SHALL maintain backward compatibility by preserving old schema versions

### Requirement 14 [POST-MVP]

**User Story:** As a shopper, I want to find products based on their taste profile (e.g., sweet, sour, mild) and other subjective characteristics, so I can discover products that match my preferences even when these attributes are not explicitly stated on the label.

#### Acceptance Criteria

1. **[POST-MVP]** WHEN THE Schema Generation Agent creates a schema for a category, THE agent SHALL identify both explicit attributes (from product names) and implicit attributes (inferred from LLM reasoning about variety characteristics)
2. **[POST-MVP]** WHEN THE Attribute Extraction Agent processes a product with a known variety, THE agent SHALL use LLM reasoning to infer subjective attributes (e.g., "sweet" for Gala apples, "tart" for Granny Smith)
3. **[POST-MVP]** THE Agentic System SHALL distinguish between explicit attributes (extracted from product data) and inferred attributes (derived from LLM reasoning) in the stored metadata
