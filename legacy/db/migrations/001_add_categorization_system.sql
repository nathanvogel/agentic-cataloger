-- Migration: Add Product Categorization System Tables
-- Description: Adds tables for LLM-powered product categorization, schema generation, and attribute extraction
-- Requirements: 2.1, 7.1, 8.1, 8.2

-- ============================================================================
-- Categories Table
-- ============================================================================
-- Stores discovered product categories based on consumer substitutability
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    product_count INTEGER DEFAULT 0,
    schema_id INTEGER,
    reasoning TEXT,
    confidence DECIMAL(3, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_categories_name ON categories(name);
CREATE INDEX idx_categories_created_at ON categories(created_at);

-- ============================================================================
-- Category Schemas Table
-- ============================================================================
-- Stores JSONSchema definitions for each category's attributes
CREATE TABLE category_schemas (
    id SERIAL PRIMARY KEY,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    schema JSONB NOT NULL,
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(category_id, version)
);

CREATE INDEX idx_category_schemas_category ON category_schemas(category_id);
CREATE INDEX idx_category_schemas_version ON category_schemas(category_id, version);

-- ============================================================================
-- Global Attributes Registry
-- ============================================================================
-- Centralized registry of all attributes used across categories
CREATE TABLE global_attributes (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    type TEXT NOT NULL,
    enum_values TEXT[],
    description TEXT,
    unit TEXT,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_attribute_type CHECK (type IN ('string', 'number', 'boolean', 'enum', 'array'))
);

CREATE INDEX idx_global_attributes_name ON global_attributes(name);
CREATE INDEX idx_global_attributes_type ON global_attributes(type);

-- ============================================================================
-- Agent Execution Log
-- ============================================================================
-- Stores all LLM agent interactions for review, debugging, and quality assurance
CREATE TABLE agent_executions (
    id SERIAL PRIMARY KEY,
    phase TEXT NOT NULL,
    status TEXT NOT NULL,
    
    -- Full LLM interaction
    llm_input JSONB NOT NULL,
    llm_output JSONB NOT NULL,
    
    -- Affected entities (for linking and filtering)
    product_ids INTEGER[],
    category_ids INTEGER[],
    schema_ids INTEGER[],
    
    -- Execution metadata
    error_message TEXT,
    tokens_used INTEGER,
    duration_ms INTEGER,
    llm_model TEXT NOT NULL,
    llm_provider TEXT NOT NULL,
    
    -- Human review (optional)
    is_reviewed BOOLEAN DEFAULT FALSE,
    is_correct BOOLEAN,
    reviewer_notes TEXT,
    reviewed_at TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    
    CONSTRAINT valid_phase CHECK (phase IN ('CATEGORY_DISCOVERY', 'SCHEMA_GENERATION', 'ATTRIBUTE_EXTRACTION')),
    CONSTRAINT valid_status CHECK (status IN ('success', 'error', 'partial'))
);

CREATE INDEX idx_agent_executions_phase ON agent_executions(phase);
CREATE INDEX idx_agent_executions_status ON agent_executions(status);
CREATE INDEX idx_agent_executions_created_at ON agent_executions(created_at);
CREATE INDEX idx_agent_executions_model ON agent_executions(llm_model);
CREATE INDEX idx_agent_executions_reviewed ON agent_executions(is_reviewed, reviewed_at);
CREATE INDEX idx_agent_executions_product_ids ON agent_executions USING GIN(product_ids);
CREATE INDEX idx_agent_executions_category_ids ON agent_executions USING GIN(category_ids);
CREATE INDEX idx_agent_executions_schema_ids ON agent_executions USING GIN(schema_ids);

-- ============================================================================
-- Extend Products Table
-- ============================================================================
-- Add category_id foreign key and extraction metadata
ALTER TABLE products
ADD COLUMN category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
ADD COLUMN categorization_confidence DECIMAL(3, 2),
ADD COLUMN attributes_extracted_at TIMESTAMP;

CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_products_attributes_extracted ON products(attributes_extracted_at) WHERE attributes_extracted_at IS NOT NULL;

-- ============================================================================
-- Add Foreign Key Constraint to Categories
-- ============================================================================
-- Link categories to their schemas (added after category_schemas table exists)
ALTER TABLE categories
ADD CONSTRAINT fk_categories_schema
FOREIGN KEY (schema_id) REFERENCES category_schemas(id) ON DELETE SET NULL;

-- ============================================================================
-- Triggers for Updated Timestamps
-- ============================================================================
-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for categories table
CREATE TRIGGER update_categories_updated_at
    BEFORE UPDATE ON categories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for global_attributes table
CREATE TRIGGER update_global_attributes_updated_at
    BEFORE UPDATE ON global_attributes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Comments for Documentation
-- ============================================================================
COMMENT ON TABLE categories IS 'Stores discovered product categories based on consumer substitutability';
COMMENT ON TABLE category_schemas IS 'Stores JSONSchema definitions for category attributes';
COMMENT ON TABLE global_attributes IS 'Centralized registry of all attributes used across categories';
COMMENT ON TABLE agent_executions IS 'Logs all LLM agent interactions for review and debugging';
COMMENT ON COLUMN products.category_id IS 'Links product to its discovered category';
COMMENT ON COLUMN products.categorization_confidence IS 'Confidence score for category assignment';
COMMENT ON COLUMN products.attributes_extracted_at IS 'Timestamp when attributes were last extracted';
