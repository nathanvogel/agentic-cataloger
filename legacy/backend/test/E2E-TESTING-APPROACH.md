# Alternative E2E Testing Approach

## Overview

This document describes an alternative **complete database reset** approach suitable for future E2E tests, which differs from our current integration test strategy.

## E2E Testing Approach

### Strategy: Complete Database Reset

For E2E tests that validate the full application stack through HTTP endpoints, a different approach is recommended:

1. **Separate Test Database** - Use dedicated test database
2. **Complete Schema Reset** - Drop and recreate all tables before each test
3. **Seed Data** - Load consistent fixture data for each test
4. **Full Stack Testing** - Test through HTTP layer, not direct method calls

### 1. Test Database Configuration

```typescript
// Override database configuration to use test database
const moduleRef = await Test.createTestingModule({
  imports: [AppModule],
})
  .overrideProvider(ConfigService)
  .useValue({
    get: (key: string) => {
      if (key === "DATABASE_URL") {
        return "postgresql://pricecomp_user:abc@localhost:5532/pricecomp_test";
      }
      return process.env[key];
    },
  })
  .compile();
```

**Key Point:** Use a **completely separate test database** (`pricecomp_test` vs `pricecomp_db`)

### 2. Database Cleanup Strategy

```typescript
beforeEach(async () => {
  // Clean database and seed with fresh test data before each test
  await seedDatabase(pool);
});
```

The `seedDatabase` function:

1. **Drops ALL tables** with CASCADE
2. **Recreates schema** from SQL files
3. **Seeds test data** from fixture files

```typescript
// test/helpers/db.helper.ts
import { readFileSync } from "fs";
import { Pool } from "pg";

export async function seedDatabase(pool: Pool): Promise<void> {
  const client = await pool.connect();

  try {
    // Drop existing tables first to ensure clean state
    await client.query(`
      DROP TABLE IF EXISTS agent_executions CASCADE;
      DROP TABLE IF EXISTS category_schemas CASCADE;
      DROP TABLE IF EXISTS global_attributes CASCADE;
      DROP TABLE IF EXISTS categories CASCADE;
      DROP TABLE IF EXISTS products CASCADE;
      DROP VIEW IF EXISTS cheapest_products CASCADE;
      DROP MATERIALIZED VIEW IF EXISTS category_price_stats CASCADE;
      DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;
    `);

    // Apply schema from db/init.sql and migrations
    const initSQL = readFileSync("db/init.sql", "utf8");
    await client.query(initSQL);

    const migrationSQL = readFileSync(
      "db/migrations/001_add_categorization_system.sql",
      "utf8",
    );
    await client.query(migrationSQL);

    // Apply seed data for tests
    const seedSQL = readFileSync("test/fixtures/seed.sql", "utf8");
    await client.query(seedSQL);
  } finally {
    client.release();
  }
}
```

### 3. E2E Test Structure

```typescript
// test/products.e2e-spec.ts
import { Test } from "@nestjs/testing";
import { INestApplication } from "@nestjs/common";
import { Pool } from "pg";
import request from "supertest";
import { AppModule } from "../src/app.module";
import { seedDatabase } from "./helpers/db.helper";

describe("Product API E2E Tests", () => {
  let app: INestApplication;
  let pool: Pool;

  beforeAll(async () => {
    // Create test module with test database
    const moduleRef = await Test.createTestingModule({
      imports: [AppModule],
    })
      .overrideProvider(ConfigService)
      .useValue({
        get: (key: string) => {
          if (key === "DATABASE_URL") {
            return "postgresql://pricecomp_user:abc@localhost:5532/pricecomp_test";
          }
          return process.env[key];
        },
      })
      .compile();

    app = moduleRef.createNestApplication();
    await app.init();

    pool = new Pool({
      connectionString:
        "postgresql://pricecomp_user:abc@localhost:5532/pricecomp_test",
    });
  });

  beforeEach(async () => {
    // Complete database reset before EACH test
    await seedDatabase(pool);
  });

  afterAll(async () => {
    await pool.end();
    await app.close();
  });

  it("should create a product via API", async () => {
    // Test with fresh database state
    const response = await request(app.getHttpServer())
      .post("/api/products")
      .send({
        name: "Test Product",
        price: 9.99,
        supermarket: "migros",
      })
      .expect(201);

    expect(response.body.id).toBeDefined();
    expect(response.body.name).toBe("Test Product");
  });

  it("should list products via API", async () => {
    const response = await request(app.getHttpServer())
      .get("/api/products")
      .expect(200);

    expect(response.body).toBeInstanceOf(Array);
    expect(response.body.length).toBeGreaterThan(0);
  });
});
```

## Implementation Guide

### Step 1: Create Test Database

```bash
# Create separate test database
docker exec -it pricecomp-db psql -U pricecomp_user -c "CREATE DATABASE pricecomp_test;"
```

### Step 2: Create Seed Data File

```sql
-- test/fixtures/seed.sql
-- Insert minimal test data needed for E2E tests
INSERT INTO products (name, price, supermarket, categories, attributes) VALUES
  ('Seed Product 1', 9.99, 'migros', ARRAY['Test'], '{}'),
  ('Seed Product 2', 19.99, 'coop', ARRAY['Test'], '{}');

INSERT INTO categories (name, display_name, product_count) VALUES
  ('test_category', 'Test Category', 0);

INSERT INTO global_attributes (name, display_name, type, usage_count) VALUES
  ('test_attr', 'Test Attribute', 'string', 0);
```

### Step 3: Create Database Helper

```typescript
// test/helpers/db.helper.ts
import { readFileSync } from "fs";
import { join } from "path";
import { Pool } from "pg";

export async function seedDatabase(pool: Pool): Promise<void> {
  const client = await pool.connect();

  try {
    // Drop all tables
    await client.query(`
      DROP TABLE IF EXISTS agent_executions CASCADE;
      DROP TABLE IF EXISTS category_schemas CASCADE;
      DROP TABLE IF EXISTS global_attributes CASCADE;
      DROP TABLE IF EXISTS categories CASCADE;
      DROP TABLE IF EXISTS products CASCADE;
      DROP VIEW IF EXISTS cheapest_products CASCADE;
      DROP MATERIALIZED VIEW IF EXISTS category_price_stats CASCADE;
      DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;
    `);

    // Recreate schema
    const initSQL = readFileSync(join(__dirname, "../../db/init.sql"), "utf8");
    await client.query(initSQL);

    const migrationSQL = readFileSync(
      join(__dirname, "../../db/migrations/001_add_categorization_system.sql"),
      "utf8",
    );
    await client.query(migrationSQL);

    // Seed test data
    const seedSQL = readFileSync(
      join(__dirname, "../fixtures/seed.sql"),
      "utf8",
    );
    await client.query(seedSQL);
  } catch (error) {
    console.error("Failed to seed database:", error);
    throw error;
  } finally {
    client.release();
  }
}
```

### Step 4: Configure Package.json

```json
{
  "scripts": {
    "test:e2e": "jest --config ./test/jest-e2e.json",
    "test:e2e:watch": "jest --config ./test/jest-e2e.json --watch"
  }
}
```

### Step 5: Create Jest E2E Config

```json
// test/jest-e2e.json
{
  "moduleFileExtensions": ["js", "json", "ts"],
  "rootDir": ".",
  "testEnvironment": "node",
  "testRegex": ".e2e-spec.ts$",
  "transform": {
    "^.+\\.(t|j)s$": "ts-jest"
  }
}
```

## Comparison: E2E vs Integration Testing

| Aspect               | E2E Approach (Future)      | Integration Approach (Current) |
| -------------------- | -------------------------- | ------------------------------ |
| **Database**         | Separate test database     | Same development database      |
| **Cleanup**          | Drop all tables + recreate | Delete specific test data      |
| **When**             | Before each test           | After each test                |
| **Scope**            | Full application stack     | Repository layer only          |
| **Speed**            | Slower (full reset)        | Faster (targeted cleanup)      |
| **Isolation**        | Complete                   | Per-test data tracking         |
| **Testing Level**    | HTTP endpoints             | Direct method calls            |
| **Setup Complexity** | Higher                     | Lower                          |

## When to Use E2E Approach

**Best for:**

- ✅ Full application testing through HTTP endpoints
- ✅ API contract validation
- ✅ Authentication/authorization testing
- ✅ Complete user workflow testing
- ✅ Integration between all layers
- ✅ Testing middleware, guards, interceptors

**Advantages:**

- Complete isolation between tests
- No need to track created IDs
- Tests realistic user scenarios
- Catches integration issues
- Validates full stack behavior
- Consistent starting state

**Disadvantages:**

- Slower execution (schema recreation)
- Requires separate test database
- More complex setup
- Higher maintenance overhead

## When to Use Integration Approach (Current)

**Best for:**

- ✅ Repository layer testing
- ✅ Fast feedback during development
- ✅ Targeted method validation
- ✅ TDD workflow
- ✅ Granular component testing

**Advantages:**

- Faster execution
- Simpler setup
- No separate database needed
- Can test against real data
- Targeted cleanup

**Disadvantages:**

- Requires ID tracking
- Doesn't test full stack
- Potential for test pollution
- Manual cleanup management

## Recommendation

### Current State: Integration Tests ✅

**Keep using** the cleanup-based approach for repository tests:

- Fast execution for TDD workflow
- Works with development database
- No separate infrastructure needed
- Sufficient for repository layer

### Future: Add E2E Tests

**Consider implementing** the full reset approach when:

- Building API endpoints (REST/GraphQL)
- Need to test authentication flows
- Validating complete user journeys
- Testing API contracts
- Need integration testing across all layers

### Hybrid Strategy

```
Repository Tests (Current)
├── Fast integration tests
├── Cleanup-based isolation
├── Direct method testing
└── Run frequently during development

API E2E Tests (Future)
├── Full application tests
├── Schema reset isolation
├── HTTP endpoint testing
└── Run before deployment
```

## Summary

**E2E Approach (For Future API Tests):**

- Separate test database (`pricecomp_test`)
- Complete schema reset before each test
- Testing through HTTP endpoints
- Seed data for consistent state
- Slower but complete isolation

**Integration Approach (Current Repository Tests):**

- Same development database
- Track and delete created test data
- Direct repository method testing
- No seed data dependency
- Faster with targeted cleanup

**Both approaches are valid and serve different purposes:**

- Use **integration tests** for repository layer (current)
- Add **E2E tests** when building API layer (future)

This document serves as a guide for implementing E2E tests when the time comes to test the full application stack through HTTP endpoints.
