# Product Overview

Swiss Grocery Price Comparison - a price comparison tool for Swiss supermarkets (Migros, Lidl, Coop, and Denner).

## Core Functionality

- Import and store product data from CSV files sourced from Hugging Face datasets
- PostgreSQL database with full-text search and price comparison queries
- Support for multi-language product names (German)
- Track pricing, discounts, categories, and product attributes
- Enable price comparisons across supermarkets and categories

## Data Sources

All datasets are from Hugging Face (Yelinz) for Swiss supermarkets:

- Migros CH Products
- Lidl CH Products
- Coop CH Products
- Denner CH Products

## Key Features

- Price ranking and comparison views
- Category-based price statistics
- Full-text search with German language support
- Discount tracking
- JSONB attributes for flexible product metadata
