# Database Repository Integration Tests

## Summary

Integration test suite for the four database repositories:

- ProductsRepository
- CategoryRepository
- SchemaRepository
- AgentExecutionRepository

## Test Approach

**Path 1: Integration Tests with Real Database** (Implemented)

Tests run against the actual PostgreSQL database with transaction-based isolation for test data cleanup.

### Key Features

- Real database operations (no mocking)
- Transaction rollback for test isolation
- Validates actual SQL queries and Zapatos type generation
- Tests database constraints and relationships
- High confidence in production behavior

### Test Structure

```typescript
describe("Repository Integration Tests", () => {
  let pool: Pool;
  let repository: Repository;

  beforeAll(() => {
    pool = new Pool({ connectionString: process.env.DATABASE_URL });
    repository = new Repository(pool);
  });

  afterAll(async () => {
    await pool.end();
  });

  it("should test repository method", async () => {
    await withTransaction(pool, async (client) => {
      // Create test data using helper functions
      const testData = await createTestData(client);

      // Test repository method
      const result = await repository.method(testData.id);

      // Assert results
      expect(result).toBeDefined();

      // Transaction automatically rolls back after test
    });
  });
});
```

### Test Helpers

Located in `test-helpers.ts`:

- `withTransaction()` - Wraps test in a transaction that rolls back
- `createTestProduct()` - Creates test product data
- `createTestCategory()` - Creates test category data
- `createTestSchema()` - Creates test schema data
- `createTestAttribute()` - Creates test attribute data
- `createTestExecution()` - Creates test execution log data

### Known Issues & Solutions

#### Zapatos Return Types

Zapatos behaves differently based on input:

- Single object insert: Returns single object
- Array insert: Returns array of objects

When using PoolClient in transactions, always handle results as arrays:

```typescript
const results = await db.insert("table", data).run(client);
const item = results[0]; // Always access first element
```

#### Unique Constraints

Test data must have unique values for constrained fields. Use timestamps or random strings:

```typescript
const uniqueName = `test_${Date.now()}_${Math.random().toString(36).substring(7)}`;
```

#### Transaction Isolation

The `withTransaction` helper ensures:

1. Each test runs in its own transaction
2. All database changes are rolled back after the test
3. No test data pollution between tests
4. Tests can run in parallel safely

### Running Tests

```bash
# Run all repository tests
yarn test

# Run specific repository tests
yarn test products.repository.spec.ts
yarn test category.repository.spec.ts
yarn test schema.repository.spec.ts
yarn test agent-execution.repository.spec.ts

# Run with coverage
yarn test:cov
```

### Test Coverage

Each repository has comprehensive tests covering:

**ProductsRepository** (9 tests):

- getProductsByCategories - Filter by multiple categories
- getProductsByCategory - Filter by single category
- updateProductCategory - Assign category with confidence
- updateProductAttributes - Merge JSONB attributes
- getProductById - Retrieve single product
- getUncategorizedProducts - Find products needing categorization

**CategoryRepository** (11 tests):

- createCategory - Create with all/minimal fields
- getCategory - Retrieve by ID
- getCategoryByName - Retrieve by name
- getAllCategories - List all ordered by name
- assignProducts - Bulk assignment with transaction
- updateCategorySchema - Link to schema
- updateProductCount - Recalculate counts

**SchemaRepository** (15 tests):

- saveSchema - Create with auto-versioning
- getSchema - Retrieve by ID
- getLatestSchemaForCategory - Get highest version
- getSchemasForCategory - List all versions
- registerAttribute - Create/update with usage tracking
- getAttributeByName - Retrieve by name
- getGlobalAttributes - List all ordered by usage
- getAttributesByType - Filter by type

**AgentExecutionRepository** (23 tests):

- logExecution - Log complete LLM interactions
- markAsReviewed - Human review tracking
- getExecution - Retrieve by ID
- queryExecutions - Flexible filtering (phase, status, model, entities)
- getExecutionsByPhase/Status/Model - Convenience methods
- getUnreviewedExecutions - Find pending reviews
- getAccuracyStatsByModel - Calculate model accuracy metrics
- getExecutionsForProduct/Category - Entity-based queries

### Future Improvements

1. **Performance Tests**: Add tests for query performance with large datasets
2. **Concurrent Operations**: Test race conditions and locking
3. **Error Scenarios**: More comprehensive error handling tests
4. **Data Validation**: Test constraint violations and edge cases
5. **Migration Tests**: Verify schema migrations work correctly

### Database Setup

Tests require a running PostgreSQL database:

```bash
# Start database
docker-compose up -d

# Run migrations
# (migrations are applied automatically on container start)

# Verify database is ready
docker exec -it pricecomp-db psql -U pricecomp_user -d pricecomp_db -c "SELECT 1"
```

### Troubleshooting

**Tests fail with connection errors**:

- Ensure database is running: `docker ps | grep postgres`
- Check DATABASE_URL environment variable
- Verify port 5532 is not in use

**Tests fail with unique constraint violations**:

- Ensure test helpers generate unique names
- Check that transactions are rolling back properly
- Clear test data manually if needed: `DELETE FROM table WHERE name LIKE 'test_%'`

**Tests are slow**:

- Database connection overhead is normal for integration tests
- Consider running fewer tests during development
- Use `yarn test:watch` for faster feedback loop

## Conclusion

The integration test suite provides high confidence that the database repositories work correctly with the actual PostgreSQL database. The transaction-based isolation ensures tests are independent and don't pollute the database with test data.
