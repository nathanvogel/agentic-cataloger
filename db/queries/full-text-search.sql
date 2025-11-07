
-- Full-text search for products

SELECT name, supermarket, price
FROM products
WHERE to_tsvector('german', name) @@ to_tsquery('german', 'bio & käse')
ORDER BY price;