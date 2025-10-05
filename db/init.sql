-- Create products table
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    price DECIMAL(10, 2),
    price_text TEXT,
    currency VARCHAR(3) DEFAULT 'CHF',
    unit TEXT,
    unit_price TEXT,
    original_quantity DECIMAL(10, 3),
    original_unit VARCHAR(20),
    normalized_quantity DECIMAL(10, 3),
    normalized_unit VARCHAR(10),
    normalized_price DECIMAL(10, 2),
    is_discounted BOOLEAN DEFAULT FALSE,
    discount_info TEXT,
    supermarket TEXT NOT NULL,
    categories TEXT[] DEFAULT '{}',
    attributes JSONB DEFAULT '{}',
    image_url TEXT,
    product_url TEXT,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_supermarket CHECK (supermarket IN ('migros', 'lidl', 'coop', 'denner')),
    CONSTRAINT valid_normalized_unit CHECK (normalized_unit IS NULL OR normalized_unit IN ('kg', 'L', 'unit'))
);

-- Create indexes for fast queries
CREATE INDEX idx_products_supermarket ON products(supermarket);
CREATE INDEX idx_products_price ON products(price) WHERE price IS NOT NULL;
CREATE INDEX idx_products_categories ON products USING GIN(categories);
CREATE INDEX idx_products_attributes ON products USING GIN(attributes);
CREATE INDEX idx_products_name_search ON products USING GIN(to_tsvector('german', name));
CREATE INDEX idx_products_is_discounted ON products(is_discounted) WHERE is_discounted = TRUE;
CREATE INDEX idx_products_normalized_unit ON products(normalized_unit) WHERE normalized_unit IS NOT NULL;
CREATE INDEX idx_products_normalized_price ON products(normalized_price) WHERE normalized_price IS NOT NULL;
CREATE INDEX idx_products_normalized_unit_price ON products(normalized_unit, normalized_price) WHERE normalized_unit IS NOT NULL AND normalized_price IS NOT NULL;

-- Create a view for easy price comparisons
CREATE VIEW cheapest_products AS
SELECT 
    name,
    supermarket,
    price,
    unit_price,
    is_discounted,
    categories,
    attributes,
    product_url,
    RANK() OVER (PARTITION BY name ORDER BY price) as price_rank
FROM products
WHERE price IS NOT NULL;

-- Create a materialized view for category analysis
CREATE MATERIALIZED VIEW category_price_stats AS
SELECT 
    unnest(categories) as category,
    supermarket,
    COUNT(*) as product_count,
    AVG(price) as avg_price,
    MIN(price) as min_price,
    MAX(price) as max_price
FROM products
WHERE price IS NOT NULL
GROUP BY unnest(categories), supermarket;

CREATE INDEX idx_category_stats ON category_price_stats(category, supermarket);
