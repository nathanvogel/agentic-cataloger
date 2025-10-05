# Swiss Grocery Price Comparison

Compare prices across Swiss supermarkets: Migros, Lidl, Coop, and Denner.

## Quick Start

### 1. Start the Database

```bash
docker-compose up -d
```

Wait for PostgreSQL to be ready (about 5-10 seconds):

```bash
docker-compose logs -f postgres
```

### 2. Load the Data

```bash
python scripts/import_data.py
```

### 3. Query Examples

Connect to the database:

```bash
docker exec -it grocery-prices-db psql -U grocery_user -d grocery_prices
```

Or use any PostgreSQL client:

- Host: localhost
- Port: 5432
- Database: grocery_prices
- User: grocery_user
- Password: grocery_pass

## Example Queries

### Find cheapest lemons

```sql
SELECT name, supermarket, price, unit_price, product_url
FROM products
WHERE name ILIKE '%lemon%' OR name ILIKE '%zitrone%'
ORDER BY price;
```

### Find cheapest Bio lemons

```sql
SELECT name, supermarket, price, unit_price, product_url
FROM products
WHERE (name ILIKE '%lemon%' OR name ILIKE '%zitrone%')
  AND (name ILIKE '%bio%' OR attributes->>'bio' = 'true')
ORDER BY price;
```

### Compare prices across supermarkets for a product

```sql
SELECT supermarket, AVG(price) as avg_price, MIN(price) as min_price, COUNT(*) as products
FROM products
WHERE name ILIKE '%milch%'
GROUP BY supermarket
ORDER BY avg_price;
```

### Find cheapest supermarket by category

```sql
SELECT supermarket, AVG(price) as avg_price
FROM products
WHERE 'Früchte' = ANY(categories)
GROUP BY supermarket
ORDER BY avg_price;
```

### Full-text search for products

```sql
SELECT name, supermarket, price
FROM products
WHERE to_tsvector('german', name) @@ to_tsquery('german', 'bio & käse')
ORDER BY price;
```

## Stopping the Database

```bash
docker-compose down
```

To remove all data:

```bash
docker-compose down -v
```

## Database Schema

- **products**: Main table with all product information
- **cheapest_products**: View showing price rankings
- **category_price_stats**: Materialized view with category statistics

## Data Sources

- Migros CH Products
- Lidl CH Products
- Coop CH Products
- Denner CH Products

All datasets from Hugging Face (Yelinz).
