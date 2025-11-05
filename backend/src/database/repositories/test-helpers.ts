import { Pool } from "pg";
import * as db from "zapatos/db";
import type * as s from "zapatos/schema";

/**
 * Test helper utilities for database integration tests.
 * Provides test data creation and cleanup utilities.
 */

// Track created test data for cleanup
const testDataIds = {
  products: [] as number[],
  categories: [] as number[],
  schemas: [] as number[],
  attributes: [] as number[],
  executions: [] as number[],
};

/**
 * Clean up all test data created during tests.
 * Should be called in afterEach hooks.
 *
 * @param pool - Database connection pool
 */
export async function cleanupTestData(pool: Pool): Promise<void> {
  // Delete in reverse order of dependencies
  if (testDataIds.executions.length > 0) {
    await db.sql`DELETE FROM ${"agent_executions"} WHERE id = ANY(${db.param(testDataIds.executions)})`.run(
      pool,
    );
    testDataIds.executions = [];
  }

  if (testDataIds.products.length > 0) {
    await db.sql`DELETE FROM ${"products"} WHERE id = ANY(${db.param(testDataIds.products)})`.run(
      pool,
    );
    testDataIds.products = [];
  }

  if (testDataIds.schemas.length > 0) {
    await db.sql`DELETE FROM ${"category_schemas"} WHERE id = ANY(${db.param(testDataIds.schemas)})`.run(
      pool,
    );
    testDataIds.schemas = [];
  }

  if (testDataIds.categories.length > 0) {
    await db.sql`DELETE FROM ${"categories"} WHERE id = ANY(${db.param(testDataIds.categories)})`.run(
      pool,
    );
    testDataIds.categories = [];
  }

  if (testDataIds.attributes.length > 0) {
    await db.sql`DELETE FROM ${"global_attributes"} WHERE id = ANY(${db.param(testDataIds.attributes)})`.run(
      pool,
    );
    testDataIds.attributes = [];
  }
}

/**
 * Create a test product in the database.
 *
 * @param pool - Database connection pool
 * @param overrides - Optional field overrides
 * @returns Created product
 */
export async function createTestProduct(
  pool: Pool,
  overrides: Partial<s.products.Insertable> = {},
) {
  const uniqueName =
    overrides.name ||
    `Test Product ${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;

  const insertData: s.products.Insertable = {
    name: uniqueName,
    price: 5.99,
    supermarket: "migros",
    categories: ["Test Category"],
    attributes: {},
    ...overrides,
  };

  const product = await db.insert("products", insertData).run(pool);
  testDataIds.products.push(product.id);
  return product;
}

/**
 * Create a test category in the database.
 *
 * @param pool - Database connection pool
 * @param overrides - Optional field overrides
 * @returns Created category
 */
export async function createTestCategory(
  pool: Pool,
  overrides: Partial<s.categories.Insertable> = {},
) {
  // Always generate unique name by appending timestamp and random string
  const baseName =
    typeof overrides.name === "string" ? overrides.name : "test_category";
  const uniqueName = `${baseName}_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;

  const insertData: s.categories.Insertable = {
    display_name: "Test Category",
    product_count: 0,
    ...overrides,
    name: uniqueName, // Always use unique name
  };

  const category = await db.insert("categories", insertData).run(pool);
  testDataIds.categories.push(category.id);
  return category;
}

/**
 * Create a test schema in the database.
 *
 * @param pool - Database connection pool
 * @param categoryId - Category ID to link to
 * @param overrides - Optional field overrides
 * @returns Created schema
 */
export async function createTestSchema(
  pool: Pool,
  categoryId: number,
  overrides: Partial<s.category_schemas.Insertable> = {},
) {
  const insertData: s.category_schemas.Insertable = {
    category_id: categoryId,
    schema: { type: "object", properties: {} },
    version: 1,
    ...overrides,
  };

  const schema = await db.insert("category_schemas", insertData).run(pool);
  testDataIds.schemas.push(schema.id);
  return schema;
}

/**
 * Create a test global attribute in the database.
 *
 * @param pool - Database connection pool
 * @param overrides - Optional field overrides
 * @returns Created attribute
 */
export async function createTestAttribute(
  pool: Pool,
  overrides: Partial<s.global_attributes.Insertable> = {},
) {
  const uniqueName = `test_attr_${Date.now()}_${Math.random().toString(36).substring(7)}`;

  const insertData: s.global_attributes.Insertable = {
    name: uniqueName,
    display_name: "Test Attribute",
    type: "string",
    usage_count: 0,
    ...overrides,
  };

  const attribute = await db.insert("global_attributes", insertData).run(pool);
  testDataIds.attributes.push(attribute.id);
  return attribute;
}

/**
 * Create a test agent execution in the database.
 *
 * @param pool - Database connection pool
 * @param overrides - Optional field overrides
 * @returns Created execution
 */
export async function createTestExecution(
  pool: Pool,
  overrides: Partial<s.agent_executions.Insertable> = {},
) {
  const insertData: s.agent_executions.Insertable = {
    phase: "CATEGORY_DISCOVERY",
    status: "success",
    llm_input: { test: "input" },
    llm_output: { test: "output" },
    llm_model: "gpt-4",
    llm_provider: "openai",
    product_ids: [],
    category_ids: [],
    schema_ids: [],
    completed_at: new Date(),
    ...overrides,
  };

  const execution = await db.insert("agent_executions", insertData).run(pool);
  testDataIds.executions.push(execution.id);
  return execution;
}
