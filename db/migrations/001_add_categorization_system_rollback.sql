-- Rollback Migration: Remove Product Categorization System Tables
-- Description: Removes all tables and columns added for the categorization system

-- ============================================================================
-- Drop Triggers
-- ============================================================================
DROP TRIGGER IF EXISTS update_categories_updated_at ON categories;
DROP TRIGGER IF EXISTS update_global_attributes_updated_at ON global_attributes;
DROP FUNCTION IF EXISTS update_updated_at_column();

-- ============================================================================
-- Remove Products Table Extensions
-- ============================================================================
ALTER TABLE products
DROP COLUMN IF EXISTS category_id,
DROP COLUMN IF EXISTS categorization_confidence,
DROP COLUMN IF EXISTS attributes_extracted_at;

-- ============================================================================
-- Drop Tables (in reverse order of dependencies)
-- ============================================================================
DROP TABLE IF EXISTS agent_executions;
DROP TABLE IF EXISTS category_schemas;
DROP TABLE IF EXISTS global_attributes;
DROP TABLE IF EXISTS categories;
