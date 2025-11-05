import { describe, it, expect, beforeAll, afterAll, afterEach } from "vitest";
import { Pool } from "pg";
import { SchemaRepository } from "./schema.repository";
import {
  cleanupTestData,
  createTestCategory,
  createTestSchema,
  createTestAttribute,
} from "./test-helpers";

describe("SchemaRepository Integration Tests", () => {
  let pool: Pool;
  let repository: SchemaRepository;

  beforeAll(() => {
    pool = new Pool({
      connectionString: process.env.DATABASE_URL,
    });
    repository = new SchemaRepository(pool);
  });

  afterEach(async () => {
    await cleanupTestData(pool);
  });

  afterAll(async () => {
    await pool.end();
  });

  describe("saveSchema", () => {
    it("should create a new schema with version 1", async () => {
      await withTransaction(pool, async (client) => {
        const category = await createTestCategory(client);

        const schema = await repository.saveSchema({
          category_id: category.id,
          schema: {
            type: "object",
            properties: {
              weight: { type: "number", unit: "g" },
            },
          },
        });

        expect(schema.id).toBeDefined();
        expect(schema.category_id).toBe(category.id);
        expect(schema.version).toBe(1);
        expect(schema.schema).toEqual({
          type: "object",
          properties: {
            weight: { type: "number", unit: "g" },
          },
        });
      });
    });

    it("should auto-increment version for existing category", async () => {
      await withTransaction(pool, async (client) => {
        const category = await createTestCategory(client);

        // Create first schema
        await createTestSchema(client, category.id, { version: 1 });

        // Create second schema (should be version 2)
        const schema2 = await repository.saveSchema({
          category_id: category.id,
          schema: { type: "object", properties: { color: { type: "string" } } },
        });

        expect(schema2.version).toBe(2);
      });
    });

    it("should allow manual version specification", async () => {
      await withTransaction(pool, async (client) => {
        const category = await createTestCategory(client);

        const schema = await repository.saveSchema({
          category_id: category.id,
          schema: { type: "object" },
          version: 5,
        });

        expect(schema.version).toBe(5);
      });
    });
  });

  describe("getSchema", () => {
    it("should return schema by ID", async () => {
      await withTransaction(pool, async (client) => {
        const category = await createTestCategory(client);
        const created = await createTestSchema(client, category.id, {
          schema: { test: "data" },
        });

        const schema = await repository.getSchema(created.id);

        expect(schema).toBeTruthy();
        expect(schema?.schema).toEqual({ test: "data" });
      });
    });

    it("should return null for non-existent schema", async () => {
      await withTransaction(pool, async () => {
        const schema = await repository.getSchema(999999);
        expect(schema).toBeNull();
      });
    });
  });

  describe("getLatestSchemaForCategory", () => {
    it("should return the highest version schema", async () => {
      await withTransaction(pool, async (client) => {
        const category = await createTestCategory(client);

        await createTestSchema(client, category.id, {
          version: 1,
          schema: { v: 1 },
        });
        await createTestSchema(client, category.id, {
          version: 2,
          schema: { v: 2 },
        });
        const latest = await createTestSchema(client, category.id, {
          version: 3,
          schema: { v: 3 },
        });

        const result = await repository.getLatestSchemaForCategory(category.id);

        expect(result?.id).toBe(latest.id);
        expect(result?.version).toBe(3);
        expect(result?.schema).toEqual({ v: 3 });
      });
    });

    it("should return null when no schemas exist", async () => {
      await withTransaction(pool, async (client) => {
        const category = await createTestCategory(client);

        const schema = await repository.getLatestSchemaForCategory(category.id);

        expect(schema).toBeNull();
      });
    });
  });

  describe("getSchemasForCategory", () => {
    it("should return all schemas ordered by version", async () => {
      await withTransaction(pool, async (client) => {
        const category = await createTestCategory(client);

        await createTestSchema(client, category.id, { version: 3 });
        await createTestSchema(client, category.id, { version: 1 });
        await createTestSchema(client, category.id, { version: 2 });

        const schemas = await repository.getSchemasForCategory(category.id);

        expect(schemas).toHaveLength(3);
        expect(schemas[0].version).toBe(1);
        expect(schemas[1].version).toBe(2);
        expect(schemas[2].version).toBe(3);
      });
    });
  });

  describe("registerAttribute", () => {
    it("should create a new attribute", async () => {
      await withTransaction(pool, async () => {
        const attribute = await repository.registerAttribute({
          name: "test_weight",
          display_name: "Weight",
          type: "number",
          unit: "g",
          description: "Product weight in grams",
        });

        expect(attribute.id).toBeDefined();
        expect(attribute.name).toBe("test_weight");
        expect(attribute.display_name).toBe("Weight");
        expect(attribute.type).toBe("number");
        expect(attribute.unit).toBe("g");
        expect(attribute.usage_count).toBe(1);
      });
    });

    it("should increment usage count for existing attribute", async () => {
      await withTransaction(pool, async (client) => {
        const existing = await createTestAttribute(client, {
          name: "existing_attr",
          usage_count: 5,
        });

        const updated = await repository.registerAttribute({
          name: "existing_attr",
          display_name: "Updated",
          type: "string",
        });

        expect(updated.id).toBe(existing.id);
        expect(updated.usage_count).toBe(6);
      });
    });

    it("should handle enum type with values", async () => {
      await withTransaction(pool, async () => {
        const attribute = await repository.registerAttribute({
          name: "color",
          display_name: "Color",
          type: "enum",
          enum_values: ["red", "green", "blue"],
        });

        expect(attribute.type).toBe("enum");
        expect(attribute.enum_values).toEqual(["red", "green", "blue"]);
      });
    });
  });

  describe("getAttributeByName", () => {
    it("should return attribute by name", async () => {
      await withTransaction(pool, async (client) => {
        await createTestAttribute(client, {
          name: "unique_attr",
          display_name: "Unique",
        });

        const attribute = await repository.getAttributeByName("unique_attr");

        expect(attribute).toBeTruthy();
        expect(attribute?.display_name).toBe("Unique");
      });
    });

    it("should return null for non-existent attribute", async () => {
      await withTransaction(pool, async () => {
        const attribute = await repository.getAttributeByName("nonexistent");
        expect(attribute).toBeNull();
      });
    });
  });

  describe("getGlobalAttributes", () => {
    it("should return all attributes ordered by usage count", async () => {
      await withTransaction(pool, async (client) => {
        await createTestAttribute(client, {
          name: "low_usage",
          usage_count: 1,
        });
        await createTestAttribute(client, {
          name: "high_usage",
          usage_count: 100,
        });
        await createTestAttribute(client, {
          name: "mid_usage",
          usage_count: 50,
        });

        const attributes = await repository.getGlobalAttributes();

        expect(attributes.length).toBeGreaterThanOrEqual(3);
        // Check that our test attributes are ordered by usage
        const testAttrs = attributes.filter((a) =>
          ["low_usage", "high_usage", "mid_usage"].includes(a.name),
        );
        expect(testAttrs[0].name).toBe("high_usage");
        expect(testAttrs[1].name).toBe("mid_usage");
        expect(testAttrs[2].name).toBe("low_usage");
      });
    });
  });

  describe("getAttributesByType", () => {
    it("should return attributes of specified type", async () => {
      await withTransaction(pool, async (client) => {
        await createTestAttribute(client, {
          name: "num1",
          type: "number",
          usage_count: 10,
        });
        await createTestAttribute(client, {
          name: "num2",
          type: "number",
          usage_count: 5,
        });
        await createTestAttribute(client, {
          name: "str1",
          type: "string",
        });

        const numberAttrs = await repository.getAttributesByType("number");

        const testNumbers = numberAttrs.filter((a) =>
          ["num1", "num2"].includes(a.name),
        );
        expect(testNumbers).toHaveLength(2);
        expect(testNumbers.every((a) => a.type === "number")).toBe(true);
        // Should be ordered by usage count
        expect(testNumbers[0].name).toBe("num1");
        expect(testNumbers[1].name).toBe("num2");
      });
    });
  });
});
