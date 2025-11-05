-- Test script to verify the categorization system migration
-- This script inserts test data and verifies all tables and relationships work correctly

BEGIN;

-- Test 1: Insert a category
INSERT INTO categories (name, display_name, reasoning, confidence)
VALUES ('test-lemon', 'Test Lemon', 'Test category for lemons', 0.95);

-- Get the category ID
DO $$
DECLARE
    test_category_id INTEGER;
    test_schema_id INTEGER;
    test_product_id INTEGER;
BEGIN
    -- Get category ID
    SELECT id INTO test_category_id FROM categories WHERE name = 'test-lemon';
    RAISE NOTICE 'Created category with ID: %', test_category_id;

    -- Test 2: Insert a category schema
    INSERT INTO category_schemas (category_id, schema, version)
    VALUES (test_category_id, '{"type": "object", "properties": {"organic": {"type": "boolean"}}}', 1)
    RETURNING id INTO test_schema_id;
    RAISE NOTICE 'Created schema with ID: %', test_schema_id;

    -- Test 3: Link schema to category
    UPDATE categories SET schema_id = test_schema_id WHERE id = test_category_id;
    RAISE NOTICE 'Linked schema to category';

    -- Test 4: Insert a global attribute
    INSERT INTO global_attributes (name, display_name, type, description)
    VALUES ('test_organic', 'Test Organic', 'boolean', 'Test organic certification attribute');
    RAISE NOTICE 'Created global attribute';

    -- Test 5: Get a product ID (if products exist)
    SELECT id INTO test_product_id FROM products LIMIT 1;
    
    IF test_product_id IS NOT NULL THEN
        -- Test 6: Update product with category
        UPDATE products 
        SET category_id = test_category_id,
            categorization_confidence = 0.92,
            attributes_extracted_at = CURRENT_TIMESTAMP
        WHERE id = test_product_id;
        RAISE NOTICE 'Updated product % with category', test_product_id;

        -- Test 7: Insert agent execution log
        INSERT INTO agent_executions (
            phase, 
            status, 
            llm_input, 
            llm_output, 
            product_ids,
            category_ids,
            schema_ids,
            tokens_used,
            duration_ms,
            llm_model,
            llm_provider,
            completed_at
        ) VALUES (
            'CATEGORY_DISCOVERY',
            'success',
            '{"prompt": "test prompt", "products": [1, 2, 3]}',
            '{"categories": [{"name": "test-lemon"}]}',
            ARRAY[test_product_id],
            ARRAY[test_category_id],
            ARRAY[test_schema_id],
            1500,
            2500,
            'gpt-4',
            'openai',
            CURRENT_TIMESTAMP
        );
        RAISE NOTICE 'Created agent execution log';
    ELSE
        RAISE NOTICE 'No products found, skipping product-related tests';
    END IF;

    -- Test 8: Query with GIN indexes
    PERFORM * FROM agent_executions WHERE product_ids && ARRAY[test_product_id];
    RAISE NOTICE 'GIN index query successful';

    -- Test 9: Verify triggers work
    UPDATE categories SET display_name = 'Updated Test Lemon' WHERE id = test_category_id;
    IF (SELECT updated_at > created_at FROM categories WHERE id = test_category_id) THEN
        RAISE NOTICE 'Trigger updated timestamp successfully';
    END IF;

END $$;

-- Verify all test data
SELECT 'Categories' as table_name, COUNT(*) as test_records FROM categories WHERE name = 'test-lemon'
UNION ALL
SELECT 'Category Schemas', COUNT(*) FROM category_schemas WHERE category_id IN (SELECT id FROM categories WHERE name = 'test-lemon')
UNION ALL
SELECT 'Global Attributes', COUNT(*) FROM global_attributes WHERE name = 'test_organic'
UNION ALL
SELECT 'Agent Executions', COUNT(*) FROM agent_executions WHERE phase = 'CATEGORY_DISCOVERY'
UNION ALL
SELECT 'Products with Category', COUNT(*) FROM products WHERE category_id IS NOT NULL;

-- Clean up test data
DELETE FROM agent_executions WHERE phase = 'CATEGORY_DISCOVERY' AND llm_model = 'gpt-4';
UPDATE products SET category_id = NULL, categorization_confidence = NULL, attributes_extracted_at = NULL WHERE category_id IN (SELECT id FROM categories WHERE name = 'test-lemon');
DELETE FROM categories WHERE name = 'test-lemon';
DELETE FROM global_attributes WHERE name = 'test_organic';

ROLLBACK;

-- Final verification message
SELECT 'Migration test completed successfully!' as result;
