-- Easily list categories coming from the datasets

SELECT 
    category,
    COUNT(*) AS product_count,
    COUNT(DISTINCT supermarket) AS supermarket_count
FROM (
    SELECT unnest(categories) AS category, supermarket
    FROM products
    WHERE categories IS NOT NULL 
      AND array_length(categories, 1) > 0
) AS category_products
GROUP BY category
ORDER BY category ASC
LIMIT 1000;