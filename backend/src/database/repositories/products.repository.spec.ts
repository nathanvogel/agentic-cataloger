import { describe, it, expect, beforeAll, afterAll, afterEach } from "vitest";
import { Pool } from "pg";
import { ProductsRepository } from "./products.repository";
import {
  cleanupTestData,
  createTestProduct,
  createTestCategory,
} from "./test-helpers";

describe("ProductsRepository Integration Tests", () => {
  let pool: Pool;
  let repository: ProductsRepository;

  beforeAll(() => {
    pool = new Pool({
      connectionString:
        process.env.DATABASE_URL ||
        "postgresql://pricecomp_user:abc@localhost:5532/pricecomp_db",
    });
    repository = new ProductsRepository(pool);
  });

  afterEach(async () => {
    await cleanupTestData(pool);
  });

  afterAll(async () => {
    await pool.end();
  });

  describe("getProductsByCategories", () => {
    it("should return products matching any of the specified categories", async () => {
      // Create test products with different categories
      await createTestProduct(pool, {
        name: "Apple",
        categories: ["Früchte", "Bio"],
      });
      await createTestProduct(pool, {
        name: "Carrot",
        categories: ["Gemüse"],
      });
      await createTestProduct(pool, {
        name: "Banana",
        categories: ["Früchte"],
      });
      await createTestProduct(pool, {
        name: "Milk",
        categories: ["Milchprodukte"],
      });

      // Query for products in Früchte or Gemüse
      const products = await repository.getProductsByCategories([
        "Früchte",
        "Gemüse",
      ]);

      const testProducts = products.filter((p) =>
        ["Apple", "Carrot", "Banana"].includes(p.name),
      );
      expect(testProducts.length).toBe(3);
    });

    it("should return empty array when no products match", async () => {
      await createTestProduct(pool, {
        name: "Test",
        categories: ["Other"],
      });

      const products = await repository.getProductsByCategories([
        "NonExistent",
      ]);

      const testProducts = products.filter((p) => p.name === "Test");
      expect(testProducts).toHaveLength(0);
    });
  });

  describe("getProductsByCategory", () => {
    it("should return products assigned to a specific category", async () => {
      const category = await createTestCategory(pool, {
        name: "vegetables",
      });

      await createTestProduct(pool, {
        name: "Carrot",
        category_id: category.id,
        categorization_confidence: 0.95,
      });
      await createTestProduct(pool, {
        name: "Potato",
        category_id: category.id,
        categorization_confidence: 0.88,
      });
      await createTestProduct(pool, {
        name: "Apple",
        category_id: null,
      });

      const products = await repository.getProductsByCategory(category.id);

      expect(products).toHaveLength(2);
      expect(products.every((p) => p.category_id === category.id)).toBe(true);
    });
  });

  describe("updateProductCategory", () => {
    it("should assign category and confidence to a product", async () => {
      const product = await createTestProduct(pool, { name: "Test" });
      const category = await createTestCategory(pool);

      await repository.updateProductCategory(product.id, category.id, 0.92);

      const updated = await repository.getProductById(product.id);
      expect(updated?.category_id).toBe(category.id);
      expect(updated?.categorization_confidence).toBe(0.92);
    });
  });

  describe("updateProductAttributes", () => {
    it("should merge new attributes with existing ones", async () => {
      const product = await createTestProduct(pool, {
        name: "Test",
        attributes: { color: "red", size: "large" },
      });

      await repository.updateProductAttributes(product.id, {
        weight: 500,
        organic: true,
      });

      const updated = await repository.getProductById(product.id);
      expect(updated?.attributes).toEqual({
        color: "red",
        size: "large",
        weight: 500,
        organic: true,
      });
      expect(updated?.attributes_extracted_at).toBeTruthy();
    });
  });

  describe("getProductById", () => {
    it("should return product when it exists", async () => {
      const created = await createTestProduct(pool, {
        name: "Test Product",
      });

      const product = await repository.getProductById(created.id);

      expect(product).toBeTruthy();
      expect(product?.name).toBe("Test Product");
    });

    it("should return null when product does not exist", async () => {
      const product = await repository.getProductById(999999);
      expect(product).toBeNull();
    });
  });

  describe("getUncategorizedProducts", () => {
    it("should return products without category assignment", async () => {
      const category = await createTestCategory(pool);

      const p1 = await createTestProduct(pool, {
        name: "Uncategorized 1",
        category_id: null,
      });
      const p2 = await createTestProduct(pool, {
        name: "Uncategorized 2",
        category_id: null,
      });
      const p3 = await createTestProduct(pool, {
        name: "Categorized",
        category_id: category.id,
      });

      // Verify the uncategorized products have null category_id
      const p1Check = await repository.getProductById(p1.id);
      const p2Check = await repository.getProductById(p2.id);
      const p3Check = await repository.getProductById(p3.id);

      expect(p1Check?.category_id).toBeNull();
      expect(p2Check?.category_id).toBeNull();
      expect(p3Check?.category_id).toBe(category.id);

      // Verify getUncategorizedProducts returns results
      const products = await repository.getUncategorizedProducts(10);
      expect(products.length).toBeGreaterThan(0);
      expect(products.every((p) => p.category_id === null)).toBe(true);
    });

    it("should respect limit parameter", async () => {
      for (let i = 0; i < 5; i++) {
        await createTestProduct(pool, {
          name: `Product ${i}`,
          category_id: null,
        });
      }

      const products = await repository.getUncategorizedProducts(3);

      expect(products.length).toBeLessThanOrEqual(3);
    });
  });
});
