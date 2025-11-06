---
inclusion: always
---

# Project Structure

This application is a price comparison tool for groceries with AI-powered analysis. It initially focuses on the Swiss market, with datasets covering `migros`, `lidl`, `coop` and `denner`.

Components will ultimately include:

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
