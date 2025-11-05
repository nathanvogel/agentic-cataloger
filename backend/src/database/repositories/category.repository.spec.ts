import { describe, it, expect, beforeAll, afterAll, afterEach } from "vitest";
import { Pool } from "pg";
import { CategoryRepository } from "./category.repository";
import {
  cleanupTestData,
  createTestCategory,
  createTestProduct,
  createTestSchema,
} from "./test-helpers";

describe("CategoryRepository Integration Tests", () => {
  let pool: Pool;
  let repository: CategoryRepository;

  beforeAll(() => {
    pool = new Pool({
      connectionString: process.env.DATABASE_URL,
    });
    repository = new CategoryRepository(pool);
  });

  afterEach(async () => {
    await cleanupTestData(pool);
  });

  afterAll(async () => {
    await pool.end();
  });

  describe("createCategory", () => {
    it("should create a new category with all fields", async () => {
      await withTransaction(pool, async () => {
        const category = await repository.createCategory({
          name: "vegetables",
          display_name: "Gemüse",
          reasoning: "Products that are vegetables",
          confidence: 0.95,
        });

        expect(category.id).toBeDefined();
        expect(category.name).toBe("vegetables");
        expect(category.display_name).toBe("Gemüse");
        expect(category.reasoning).toBe("Products that are vegetables");
        expect(category.confidence).toBe(0.95);
        expect(category.product_count).toBe(0);
      });
    });

    it("should create category with minimal fields", async () => {
      await withTransaction(pool, async () => {
        const category = await repository.createCategory({
          name: "fruits",
          display_name: "Früchte",
        });

        expect(category.id).toBeDefined();
        expect(category.name).toBe("fruits");
        expect(category.display_name).toBe("Früchte");
      });
    });
  });

  describe("getCategory", () => {
    it("should return category by ID", async () => {
      await withTransaction(pool, async (client) => {
        const created = await createTestCategory(client, {
          name: "test_cat",
          display_name: "Test Category",
        });

        const category = await repository.getCategory(created.id);

        expect(category).toBeTruthy();
        expect(category?.name).toBe("test_cat");
      });
    });

    it("should return null for non-existent category", async () => {
      await withTransaction(pool, async () => {
        const category = await repository.getCategory(999999);
        expect(category).toBeNull();
      });
    });
  });

  describe("getCategoryByName", () => {
    it("should return category by name", async () => {
      await withTransaction(pool, async (client) => {
        await createTestCategory(client, {
          name: "unique_name",
          display_name: "Unique",
        });

        const category = await repository.getCategoryByName("unique_name");

        expect(category).toBeTruthy();
        expect(category?.display_name).toBe("Unique");
      });
    });

    it("should return null for non-existent name", async () => {
      await withTransaction(pool, async () => {
        const category = await repository.getCategoryByName("nonexistent");
        expect(category).toBeNull();
      });
    });
  });

  describe("getAllCategories", () => {
    it("should return all categories ordered by name", async () => {
      await withTransaction(pool, async (client) => {
        await createTestCategory(client, {
          name: "zebra",
          display_name: "Z",
        });
        await createTestCategory(client, {
          name: "apple",
          display_name: "A",
        });
        await createTestCategory(client, {
          name: "middle",
          display_name: "M",
        });

        const categories = await repository.getAllCategories();

        expect(categories.length).toBeGreaterThanOrEqual(3);
        // Check that our test categories are in alphabetical order
        const testCats = categories.filter((c) =>
          ["zebra", "apple", "middle"].includes(c.name),
        );
        expect(testCats[0].name).toBe("apple");
        expect(testCats[1].name).toBe("middle");
        expect(testCats[2].name).toBe("zebra");
      });
    });
  });

  describe("assignProducts", () => {
    it("should assign multiple products to a category and update count", async () => {
      await withTransaction(pool, async (client) => {
        const category = await createTestCategory(client);
        const product1 = await createTestProduct(client, { name: "P1" });
        const product2 = await createTestProduct(client, { name: "P2" });
        const product3 = await createTestProduct(client, { name: "P3" });

        await repository.assignProducts(
          category.id,
          [product1.id, product2.id, product3.id],
          0.88,
        );

        // Check products were assigned
        const updatedCategory = await repository.getCategory(category.id);
        expect(updatedCategory?.product_count).toBe(3);

        // Verify products have correct category_id and confidence
        const products = await Promise.all([
          repository.getCategory(product1.id),
          repository.getCategory(product2.id),
          repository.getCategory(product3.id),
        ]);

        // Note: We're checking the category was updated, products check would need ProductsRepository
      });
    });

    it("should handle transaction rollback on error", async () => {
      await withTransaction(pool, async (client) => {
        const category = await createTestCategory(client);

        // Try to assign non-existent product (should fail)
        await expect(
          repository.assignProducts(category.id, [999999], 0.9),
        ).rejects.toThrow();

        // Category count should remain 0
        const updatedCategory = await repository.getCategory(category.id);
        expect(updatedCategory?.product_count).toBe(0);
      });
    });
  });

  describe("updateCategorySchema", () => {
    it("should link a schema to a category", async () => {
      await withTransaction(pool, async (client) => {
        const category = await createTestCategory(client);
        const schema = await createTestSchema(client, category.id);

        await repository.updateCategorySchema(category.id, schema.id);

        const updated = await repository.getCategory(category.id);
        expect(updated?.schema_id).toBe(schema.id);
      });
    });
  });

  describe("updateProductCount", () => {
    it("should recalculate product count for a category", async () => {
      await withTransaction(pool, async (client) => {
        const category = await createTestCategory(client, {
          product_count: 0,
        });

        // Manually create products with this category
        await createTestProduct(client, {
          name: "P1",
          category_id: category.id,
        });
        await createTestProduct(client, {
          name: "P2",
          category_id: category.id,
        });

        await repository.updateProductCount(category.id);

        const updated = await repository.getCategory(category.id);
        expect(updated?.product_count).toBe(2);
      });
    });
  });
});
