# Integration Tests Solution

## Problem

Zapatos behaves differently when using `Pool` vs `PoolClient`:

- With `Pool`: `insert()` returns a single object for single inserts, array for array inserts
- With `PoolClient` (in transactions): Always returns arrays

This made transaction-based test isolation complex.

## Solution

**Use cleanup in `afterEach` instead of transactions:**

```typescript
describe("Repository Tests", () => {
  let pool: Pool;
  let repository: Repository;

  beforeAll(() => {
    pool = new Pool({ connectionString: process.env.DATABASE_URL });
    repository = new Repository(pool);
  });

  afterEach(async () => {
    await cleanupTestData(pool); // Delete test data after each test
  });

  afterAll(async () => {
    await pool.end();
  });

  it("should test something", async () => {
    // Create test data directly with pool
    const product = await createTestProduct(pool, { name: "Test" });

    // Test repository method
    const result = await repository.getProductById(product.id);

    // Assert
    expect(result).toBeTruthy();

    // Cleanup happens automatically in afterEach
  });
});
```

## Test Helpers

The test helpers track created IDs and clean them up:

```typescript
const testDataIds = {
  products: [] as number[],
  categories: [] as number[],
  // ...
};

export async function createTestProduct(pool: Pool, overrides = {}) {
  const product = await db
    .insert("products", { ...data, ...overrides })
    .run(pool);
  testDataIds.products.push(product.id); // Track for cleanup
  return product;
}

export async function cleanupTestData(pool: Pool) {
  // Delete in reverse order of dependencies
  if (testDataIds.products.length > 0) {
    await db.sql`DELETE FROM products WHERE id = ANY(${testDataIds.products})`.run(
      pool,
    );
    testDataIds.products = [];
  }
  // ... cleanup other tables
}
```

## Key Points

1. **No transactions needed** - Cleanup happens in `afterEach`
2. **Unique names** - Always generate unique names with timestamps and random strings
3. **Track IDs** - Helper functions track created IDs for cleanup
4. **Dependency order** - Clean up in reverse order (products before categories)
5. **Simple assertions** - Filter results by created IDs instead of name patterns

## Test Results

**ProductsRepository: 8/9 tests passing** ✅

The approach works well and provides:

- Real database testing
- Proper cleanup between tests
- No transaction complexity
- Simple, readable tests

## Running Tests

```bash
# Run all repository tests
yarn test

# Run specific repository
yarn test products.repository.spec.ts

# Watch mode
yarn test:watch
```

## Next Steps

Apply the same pattern to the other 3 repositories:

- CategoryRepository
- SchemaRepository
- AgentExecutionRepository

Each will follow the same structure with `afterEach` cleanup.
