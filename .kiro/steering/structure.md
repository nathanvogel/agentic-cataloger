---
inclusion: always
---

# Project Structure

## Project Description

This application is a price comparison tool for groceries with AI-powered analysis. It initially focuses on the Swiss market, with datasets covering `migros`, `lidl`, `coop` and `denner`.

It enables shoppers to:

- Upload receipts of their past purchase.
- Get exhaustive suggestions on where they could save the most money by buying alternatives.
- Answer questions such as:
  - "What would be my monthly cost if I shopped at another supermarket?"
  - "How much would it cost to buy exclusively organic food where possible?"
  - "What are the top contributors to the fat intake of my household?"
- Get a precise breakdown of their groceries expenses, per category and per product.
- Get personalized suggestions for healthier shopping.

This is enabled by a structured dataset comprising:

- Exhaustive product information from supermarket, including prices.
- A precise AI-powered categorization system of products based on consumer substituability and cost comparability.
- Exhaustive tagging of product attributes by LLMs.

## Main Components

The components will ultimately include:

- data [DONE]: Copy of https://huggingface.co/datasets/Yelinz/coop-ch-products and related datasets
- data-scraper [currently omitted as Yelinz's dataset are enough for MVP]
- data-importer [DONE]
- backend [IN PROGRESS]
- db [IN PROGRESS]
- frontend [TODO]
- cicd & infra [TODO]

## Root Directories

### `/data/`

CSV data files organized by supermarket and timestamp:

- Pattern: `{supermarket}-ch-products/YYYY/MM/DD-HH:MM.csv`
- Supermarkets: migros, lidl, coop, denner

### `/data-importer/`

Standalone TypeScript application for processing CSV files:

- Parses CSV data and imports to PostgreSQL
- Built with tsc, run with `yarn run import`

### `/backend/`

NestJS application with AI-powered categorization:

- **Phase 1**: LLM discovers categories based on consumer substitutability
- **Phase 2**: LLM generates JSONSchema and attribute registry per category
- **Phase 3**: LLM extracts structured attributes into product JSONB

### `/db/`

Database initialization and migration scripts:

- PostgreSQL schema definitions
- Seed data and initial setup
- Docker Compose configuration

## Data Importer Modules

- `/parsers/` - CSV parsing and file scanning
- `/transformers/` - Data validation and transformation
- `/repositories/` - Database operations

## Backend Modules

- `/agents/` - Agentic AI data manipulation services
- `/cli/` - Command-line interfaces
- `/database/` - Database configuration, connection and operations through Zapatos
- `/llm/` - LLM client integration

## Database Schema

- `products` table with supermarket constraint
- `agent_executions` for tracking AI operations
- `categories`: Discovered product categories
- `category_schemas`: JSONSchema definitions per category
- `global_attributes`: Centralized attribute registry
- `agent_executions`: LLM interaction logs
