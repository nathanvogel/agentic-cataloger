# Implementation Plan

This plan converts the product categorization system design into actionable coding tasks. Each task builds incrementally on previous work, with the final system enabling LLM-powered product categorization, schema generation, and attribute extraction.

## Task List

- [x] 1. Set up database schema and migrations

  - Create migration script for new tables (categories, category_schemas, global_attributes, agent_executions)
  - Add category_id column to products table
  - Create all necessary indexes including GIN indexes for array columns
  - Test migration on local database
  - _Requirements: 2.1, 7.1, 8.1, 8.2_

- [x] 2. Implement LLM client using model-agnostic library

  - [x] 2.1 Choose and install model-agnostic library

    - Install chosen library (Vercel AI SDK) and dependencies
    - Configure API keys for multiple providers (OpenAI, Anthropic)
    - _Requirements: 15.1_

  - [x] 2.2 Create LLM client wrapper

    - Define TypeScript interfaces (LLMClient, CompletionOptions, LLMResponse)
    - Wrap library with our interface for structured JSON output
    - Implement retry logic with exponential backoff
    - Implement timeout handling
    - Add request/response logging
    - Extract provider from model identifier
    - _Requirements: 9.1, 9.2, 9.5, 15.1, 15.3_

  - [x] 2.3 Add model configuration
    - Create configuration file for default models per phase (e.g., gpt-4 for discovery, gpt-3.5-turbo for extraction)
    - Support model override via options
    - Add environment variable support for API keys
    - _Requirements: 15.2_

- [x] 3. Implement database repositories

  - [x] 3.1 Create Products repository

    - Implement getProductsByCategories method to filter products by category array (e.g., "Gemüse", "Früchte")
    - Implement getProductsByCategory method to get all products in a discovered category
    - Implement updateProductCategory method to assign category_id to products
    - Implement updateProductAttributes method to store extracted attributes in JSONB column
    - Add Zapatos integration for type-safe queries
    - _Requirements: 1.1, 5.2, 7.1, 10.2_

  - [x] 3.2 Create Category Registry repository

    - Implement createCategory, getCategory, getAllCategories methods
    - Implement assignProducts method
    - Add transaction support
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 3.3 Create Schema Repository

    - Implement saveSchema, getSchema methods
    - Implement registerAttribute, getGlobalAttributes methods
    - Add schema versioning support
    - _Requirements: 3.2, 3.3, 4.1, 4.2_

  - [x] 3.4 Create Agent Execution Logger

    - Implement logging of agent executions with phase, status, complete LLM input/output, tokens, model, provider
    - Store links to affected products, categories, and schemas
    - Add methods for marking executions as reviewed (is_correct, reviewer_notes)
    - Add query methods for execution history (by phase, status, model, affected entities)
    - Add method to calculate accuracy statistics per model
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 15.3_

- [x] 4. Implement Category Discovery Agent

  - [x] 4.1 Create Category Discovery Agent class

    - Implement discoverCategories method
    - Design LLM prompt for category discovery
    - Parse and validate LLM response
    - Handle errors and retries
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [x] 4.2 Implement product data preparation

    - Query products filtered by "Gemüse" or "Früchte" in categories array
    - Create ProductSummary objects with essential fields
    - Batch products for LLM context window limits
    - _Requirements: 1.1, 10.2_

  - [x] 4.3 Implement category validation and storage
    - Validate discovered categories against expected schema
    - Store categories in Category Registry
    - Assign products to categories
    - Log execution with model and provider info
    - _Requirements: 1.4, 2.2, 2.3_

- [ ] 5. Implement Schema Generation Agent

  - [ ] 5.1 Create Schema Generation Agent class

    - Implement generateSchema method
    - Design LLM prompt for schema generation
    - Parse and validate JSONSchema output
    - Handle errors and retries
    - _Requirements: 3.1, 3.4, 3.5_

  - [ ] 5.2 Implement attribute discovery and registration

    - Check Global Attribute Registry for existing attributes
    - Register new attributes with normalized names (snake_case)
    - Validate attribute definitions
    - _Requirements: 3.2, 3.3, 4.1, 4.2_

  - [ ] 5.3 Implement schema storage
    - Validate generated JSONSchema
    - Store schema in Schema Repository
    - Link schema to category
    - Log execution with model and provider info
    - _Requirements: 3.5, 11.2, 11.4_

- [ ] 6. Implement Attribute Extraction Agent

  - [ ] 6.1 Create Attribute Extraction Agent class

    - Implement extractAttributes method
    - Implement extractBatch method for efficient processing
    - Design LLM prompt for attribute extraction
    - Parse and validate extracted attributes
    - _Requirements: 5.1, 5.2, 5.3_

  - [ ] 6.2 Implement attribute validation and storage

    - Validate extracted attributes against category JSONSchema
    - Store attributes in product JSONB column
    - Update attributes_extracted_at timestamp
    - Handle validation errors
    - _Requirements: 5.3, 7.1, 7.2_

  - [ ] 6.3 Implement batch processing
    - Process products in configurable batch sizes
    - Manage LLM API rate limits
    - Provide progress reporting
    - Handle errors without stopping entire batch
    - _Requirements: 10.3, 10.4, 10.5_

- [ ] 7. Implement Agent Orchestrator

  - [ ] 7.1 Create Agent Orchestrator class

    - Implement runFullPipeline method
    - Implement runPhase method for individual phases
    - Coordinate between agents (Category Discovery → Schema Generation → Attribute Extraction)
    - _Requirements: 6.1, 6.2, 6.3_

  - [ ] 7.2 Implement pipeline execution flow

    - Execute Phase 1: Category Discovery with all products
    - Execute Phase 2: Schema Generation per category
    - Execute Phase 3: Attribute Extraction per product
    - Track overall progress and errors
    - _Requirements: 6.1, 6.2, 6.3_

  - [ ] 7.3 Add error handling and recovery
    - Log errors at each phase
    - Continue processing on non-fatal errors
    - Provide summary report at completion
    - _Requirements: 8.3, 10.5_

- [ ] 8. Implement Model Comparison Tool

  - [ ] 8.1 Create Model Comparison class

    - Implement compareModels method
    - Run same operation with multiple models in parallel (e.g., gpt-4 vs claude-3-opus)
    - Collect and compare results
    - _Requirements: 15.4_

  - [ ] 8.2 Implement comparison metrics
    - Calculate token usage, duration, cost per model
    - Track success rates
    - Generate comparison report
    - _Requirements: 15.5_

- [ ] 9. Implement Review and Statistics Tools

  - [ ] 9.1 Create review CLI commands

    - Add command to list executions for review (with filtering)
    - Add command to mark execution as reviewed
    - Add command to view execution details (full input/output)
    - _Requirements: 8.5, 8.6_

  - [ ] 9.2 Implement accuracy statistics

    - Calculate accuracy rates overall and per model
    - Calculate accuracy per phase
    - Generate review reports
    - _Requirements: 8.5, 8.6_

  - [ ] 9.3 Implement export functionality
    - Export executions to JSON/CSV for external review
    - Include product/category context in exports
    - Support filtering exports by phase, model, review status
    - _Requirements: 8.6_

- [ ] 10. Implement CLI commands

  - [ ] 10.1 Create CLI for running full pipeline

    - Add command to run complete categorization pipeline
    - Add options for model selection (e.g., --model gpt-4)
    - Add progress output
    - _Requirements: 10.1, 15.2_

  - [ ] 10.2 Create CLI for model comparison

    - Add command to compare models on sample data (e.g., --compare gpt-4,claude-3-opus)
    - Display comparison metrics
    - _Requirements: 15.4, 15.5_

  - [ ] 10.3 Create CLI for reviewing executions
    - Add command to list executions for review
    - Add command to mark executions as reviewed
    - Add command to export executions
    - Add command to view accuracy statistics
    - _Requirements: 8.5, 8.6_

- [ ] 11. Implement product querying and filtering

  - [ ] 11.1 Create product query service

    - Implement filtering by category
    - Implement filtering by single attribute
    - Implement multi-attribute filtering (AND logic)
    - _Requirements: 12.1, 12.2, 12.3_

  - [ ] 11.2 Optimize JSONB queries
    - Test query performance with sample data
    - Verify GIN index usage
    - Optimize slow queries if needed
    - _Requirements: 12.5_

- [ ] 12. Create integration tests

  - [ ] 12.1 Test end-to-end pipeline with sample data

    - Create test dataset with ~50 products from "Gemüse" and "Früchte"
    - Run full pipeline
    - Validate categories, schemas, and extracted attributes
    - _Requirements: 1.1, 3.1, 5.1_

  - [ ] 12.2 Test model comparison

    - Run same operation with multiple models
    - Verify metrics collection
    - _Requirements: 15.4, 15.5_

  - [ ] 12.3 Test review workflow
    - Mark executions as reviewed
    - Verify statistics calculation
    - Test export functionality
    - _Requirements: 8.5, 8.6_

- [ ] 13. Documentation and deployment

  - [ ] 13.1 Create README for categorization system

    - Document system architecture
    - Document CLI commands
    - Document configuration options
    - Provide usage examples

  - [ ] 13.2 Create migration guide

    - Document how to run database migrations
    - Document how to configure API keys for different providers
    - Document how to select models for different phases
    - Document how to run the pipeline on existing data

  - [ ] 13.3 Create review guide
    - Document how to review executions
    - Document how to interpret accuracy metrics
    - Provide best practices for quality assurance
    - Document how to query executions by affected entities
