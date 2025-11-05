# Database Module

This module provides database connectivity and repositories for the product categorization system.

## Structure

- `database.module.ts` - NestJS module that provides database connection pool and repositories
- `repositories/` - Repository classes for database operations
- `zapatos/` - Auto-generated Zapatos type definitions (do not edit manually)

## Repositories

### ProductsRepository

Manages product data with categorization support.

**Key Methods:**

- `getProductsByCategories(categories)` - Get products by multiple category names
- `getProductsByCategory(categoryId)` - Get products assigned to a category
- `updateProductCategory(productId, categoryId, confidence)` - Assign category to product
- `updateProductAttributes(productId, attributes)` - Update product attributes
- `getUncategorizedProducts(limit)` - Get products without category assignment

### CategoryRepository

Manages product categories.

**Key Methods:**

- `createCategory(input)` - Create a new category
- `getCategory(categoryId)` - Get category by ID
- `getCategoryByName(name)` - Get category by name
- `getAllCategories()` - Get all categories
- `assignProducts(categoryId, productIds, confidence)` - Assign products to category (with transaction)
- `updateCategorySchema(categoryId, schemaId)` - Link category to schema

### SchemaRepository

Manages category schemas and global attributes.

**Key Methods:**

- `saveSchema(input)` - Save a new schema version for a category
- `getSchema(schemaId)` - Get schema by ID
- `getLatestSchemaForCategory(categoryId)` - Get latest schema for category
- `registerAttribute(input)` - Register or update global attribute
- `getGlobalAttributes()` - Get all global attributes
- `getAttributesByType(type)` - Get attributes by type

### AgentExecutionRepository

Logs and manages LLM agent executions for review and debugging.

**Key Methods:**

- `logExecution(input)` - Log a new agent execution
- `markAsReviewed(executionId, review)` - Mark execution as reviewed
- `queryExecutions(filters, limit)` - Query executions with filters
- `getExecutionsByPhase(phase, limit)` - Get executions by phase
- `getExecutionsByModel(model, limit)` - Get executions by model
- `getAccuracyStatsByModel()` - Calculate accuracy statistics per model
- `getExecutionsForProduct(productId)` - Get executions affecting a product

## Zapatos Type Generation

To regenerate Zapatos types after database schema changes:

```bash
DATABASE_URL="postgresql://pricecomp_user:abc@localhost:5532/pricecomp_db" yarn db:generate-types
```

The types will be generated in `src/database/zapatos/schema.d.ts`.

## Usage Example

```typescript
import { Injectable } from "@nestjs/common";
import {
  ProductsRepository,
  CategoryRepository,
} from "./database/repositories";

@Injectable()
export class MyService {
  constructor(
    private productsRepo: ProductsRepository,
    private categoryRepo: CategoryRepository,
  ) {}

  async categorizeProducts() {
    // Get uncategorized products
    const products = await this.productsRepo.getUncategorizedProducts(100);

    // Create a category
    const category = await this.categoryRepo.createCategory({
      name: "vegetables",
      display_name: "Gemüse",
      reasoning: "Products that are vegetables",
      confidence: 0.95,
    });

    // Assign products to category
    const productIds = products.map((p) => p.id);
    await this.categoryRepo.assignProducts(category.id, productIds, 0.92);
  }
}
```

## Configuration

The database connection is configured via the `DATABASE_URL` environment variable in `.env`:

```
DATABASE_URL=postgresql://pricecomp_user:abc@localhost:5532/pricecomp_db
```
