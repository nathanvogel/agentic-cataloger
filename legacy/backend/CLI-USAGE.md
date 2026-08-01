# CLI Usage Guide

## Category Discovery Command

The CLI exposes the `discoverCategoriesFromFilter` method from the CategoryDiscoveryAgent.

### Prerequisites

1. Build the project:

```bash
yarn build
```

2. Ensure your database is running and populated with products.

### Usage Options

#### Option 1: Standalone CLI (Recommended)

```bash
# Basic usage - discover categories for specific product categories
yarn cli:standalone discover-categories Gemüse Früchte

# Multiple categories
yarn cli:standalone discover-categories "Milch & Eier" Fleisch Getränke

# Single category
yarn cli:standalone discover-categories Gemüse
```

#### Option 2: NestJS CLI (May have dependency issues)

```bash
# Alternative approach using full NestJS DI container
yarn cli discover-categories Gemüse Früchte
```

### Examples

```bash
# Discover categories for vegetables and fruits
yarn cli:standalone discover-categories Gemüse Früchte

# Discover categories for dairy and meat products
yarn cli:standalone discover-categories "Milch & Eier" Fleisch

# Get help
yarn cli:standalone help
```

### Output

The command will:

1. Query products matching the specified categories
2. Analyze them using the LLM
3. Create new precise categories in the database
4. Assign products to the discovered categories
5. Display a summary of results

Example output:

```
✅ Discovery completed successfully!
📊 Results:
   - Categories discovered: 5
   - Products analyzed: 127
   - Execution ID: 42

📋 Discovered Categories:
1. Lemon (lemon)
   Products: 8
   Reasoning: All citrus lemon products that consumers would substitute

2. Apple (apple)
   Products: 15
   Reasoning: Various apple varieties that serve the same consumer need
```

### Error Handling

- If no products are found for the specified categories, the command will exit with an error
- If the LLM fails to analyze products, the error will be logged and the command will exit
- All executions (successful and failed) are logged in the database for debugging

### Notes

- Category names are case-sensitive and should match existing categories in your database
- The command creates new categories - it doesn't update existing ones
- Each execution is logged with a unique execution ID for tracking
