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
      const uniqueName = `vegetables_${Date.now()}_${Math.random().toString(36).substring(7)}`;
      const category = await repository.createCategory({
        name: uniqueName,
        display_name: "Gemüse",
        reasoning: "Products that are vegetables",
        confidence: 0.95,
      });

      expect(category.id).toBeDefined();
      expect(category.name).toBe(uniqueName);
      expect(category.display_name).toBe("Gemüse");
      expect(category.reasoning).toBe("Products that are vegetables");
      expect(category.confidence).toBe(0.95);
      expect(category.product_count).toBe(0);
    });

    it("should create category with minimal fields", async () => {
      const uniqueName = `fruits_${Date.now()}_${Math.random().toString(36).substring(7)}`;
      const category = await repository.createCategory({
        name: uniqueName,
        display_name: "Früchte",
      });

      expect(category.id).toBeDefined();
      expect(category.name).toBe(uniqueName);
      expect(category.display_name).toBe("Früchte");
    });
  });

  describe("getCategory", () => {
    it("should return category by ID", async () => {
      const created = await createTestCategory(pool, {
        display_name: "Test Category",
      });

      const category = await repository.getCategory(created.id);

      expect(category).toBeTruthy();
      expect(category?.name).toBe(created.name);
      expect(category?.display_name).toBe("Test Category");
    });

    it("should return null for non-existent category", async () => {
      const category = await repository.getCategory(999999);
      expect(category).toBeNull();
    });
  });

  describe("getCategoryByName", () => {
    it("should return category by name", async () => {
      const created = await createTestCategory(pool, {
        display_name: "Unique",
      });

      const category = await repository.getCategoryByName(created.name);

      expect(category).toBeTruthy();
      expect(category?.display_name).toBe("Unique");
    });

    it("should return null for non-existent name", async () => {
      const category = await repository.getCategoryByName("nonexistent");
      expect(category).toBeNull();
    });
  });

  describe("getAllCategories", () => {
    it("should return all categories ordered by name", async () => {
      const cat1 = await createTestCategory(pool, {
        display_name: "Z",
      });
      const cat2 = await createTestCategory(pool, {
        display_name: "A",
      });
      const cat3 = await createTestCategory(pool, {
        display_name: "M",
      });

      const categories = await repository.getAllCategories();

      expect(categories.length).toBeGreaterThanOrEqual(3);
      // Check that our test categories exist and are ordered by name
      const testCatNames = [cat1.name, cat2.name, cat3.name];
      const testCats = categories.filter((c) => testCatNames.includes(c.name));
      expect(testCats.length).toBe(3);
      // Verify they are in alphabetical order
      const sortedNames = [...testCatNames].sort();
      expect(testCats[0].name).toBe(sortedNames[0]);
      expect(testCats[1].name).toBe(sortedNames[1]);
      expect(testCats[2].name).toBe(sortedNames[2]);
    });
  });

  describe("assignProducts", () => {
    it("should assign multiple products to a category and update count", async () => {
      const category = await createTestCategory(pool);
      const product1 = await createTestProduct(pool, { name: "P1" });
      const product2 = await createTestProduct(pool, { name: "P2" });
      const product3 = await createTestProduct(pool, { name: "P3" });

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

    it("should handle transaction rollback on error", async () => {
      const category = await createTestCategory(pool);

      // Try to assign to non-existent category (should fail with foreign key constraint)
      await expect(
        repository.assignProducts(999999, [1], 0.9),
      ).rejects.toThrow();

      // Original category count should remain 0
      const updatedCategory = await repository.getCategory(category.id);
      expect(updatedCategory?.product_count).toBe(0);
    });
  });

  describe("updateCategorySchema", () => {
    it("should link a schema to a category", async () => {
      const category = await createTestCategory(pool);
      const schema = await createTestSchema(pool, category.id);

      await repository.updateCategorySchema(category.id, schema.id);

      const updated = await repository.getCategory(category.id);
      expect(updated?.schema_id).toBe(schema.id);
    });
  });

  describe("updateProductCount", () => {
    it("should recalculate product count for a category", async () => {
      const category = await createTestCategory(pool, {
        product_count: 0,
      });

      // Manually create products with this category
      await createTestProduct(pool, {
        name: "P1",
        category_id: category.id,
      });
      await createTestProduct(pool, {
        name: "P2",
        category_id: category.id,
      });

      await repository.updateProductCount(category.id);

      const updated = await repository.getCategory(category.id);
      expect(updated?.product_count).toBe(2);
    });
  });
});
