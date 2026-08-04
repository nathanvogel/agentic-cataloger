import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { ProductRepository } from "./product-repository";
import type { Product } from "../transformers/product-transformer";
import type { Pool, PoolClient } from "pg";

describe("ProductRepository", () => {
  let repository: ProductRepository;
  let mockPool: Pool;
  let mockClient: Partial<PoolClient>;
  let mockQuery: ReturnType<typeof vi.fn>;
  let mockRelease: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    // Create mock functions
    mockQuery = vi.fn();
    mockRelease = vi.fn();

    // Create mock client
    mockClient = {
      query: mockQuery,
      release: mockRelease,
    };

    // Create mock pool
    mockPool = {
      connect: vi.fn().mockResolvedValue(mockClient),
      end: vi.fn().mockResolvedValue(undefined),
    } as any;

    repository = new ProductRepository(mockPool);
  });

  afterEach(async () => {
    await repository.close();
  });

  describe("upsertBatch", () => {
    it("should insert new products successfully", async () => {
      const products: Product[] = [
        {
          name: "Bio Apfel",
          price: 3.95,
          price_text: "CHF 3.95",
          currency: "CHF",
          unit: "500g",
          unit_price: "CHF 7.90/kg",
          original_quantity: 500,
          original_unit: "g",
          normalized_quantity: 0.5,
          normalized_unit: "kg",
          normalized_price: 7.9,
          is_discounted: false,
          discount_info: null,
          supermarket: "coop",
          categories: ["Fruits"],
          attributes: { bio: true },
          image_url: "https://example.com/image.jpg",
          product_url: "https://example.com/product",
          scraped_at: new Date("2025-01-01"),
        },
      ];

      // Mock BEGIN transaction
      mockQuery.mockResolvedValueOnce({ rows: [] });
      // Mock INSERT query - xmax = 0 means it was an insert
      mockQuery.mockResolvedValueOnce({ rows: [{ inserted: true }] });
      // Mock COMMIT transaction
      mockQuery.mockResolvedValueOnce({ rows: [] });

      const result = await repository.upsertBatch(products);

      expect(result.inserted).toBe(1);
      expect(result.updated).toBe(0);
      expect(result.failed).toBe(0);
      expect(mockQuery).toHaveBeenCalledTimes(3); // BEGIN, INSERT, COMMIT
      expect(mockRelease).toHaveBeenCalled();
    });

    it("should update existing products", async () => {
      const products: Product[] = [
        {
          name: "Bio Apfel",
          price: 4.5,
          price_text: "CHF 4.50",
          currency: "CHF",
          unit: "500g",
          unit_price: "CHF 9.00/kg",
          original_quantity: 500,
          original_unit: "g",
          normalized_quantity: 0.5,
          normalized_unit: "kg",
          normalized_price: 9.0,
          is_discounted: false,
          discount_info: null,
          supermarket: "coop",
          categories: ["Fruits"],
          attributes: { bio: true },
          image_url: "https://example.com/image.jpg",
          product_url: "https://example.com/product",
          scraped_at: new Date("2025-01-02"),
        },
      ];

      // Mock BEGIN transaction
      mockQuery.mockResolvedValueOnce({ rows: [] });
      // Mock INSERT query - xmax > 0 means it was an update
      mockQuery.mockResolvedValueOnce({ rows: [{ inserted: false }] });
      // Mock COMMIT transaction
      mockQuery.mockResolvedValueOnce({ rows: [] });

      const result = await repository.upsertBatch(products);

      expect(result.inserted).toBe(0);
      expect(result.updated).toBe(1);
      expect(result.failed).toBe(0);
    });

    it("should handle empty batch", async () => {
      const result = await repository.upsertBatch([]);

      expect(result.inserted).toBe(0);
      expect(result.updated).toBe(0);
      expect(result.failed).toBe(0);
      expect(mockQuery).not.toHaveBeenCalled();
    });

    it("should handle database errors gracefully", async () => {
      const products: Product[] = [
        {
          name: "Test Product",
          price: 1.0,
          price_text: "CHF 1.00",
          currency: "CHF",
          unit: null,
          unit_price: null,
          original_quantity: null,
          original_unit: null,
          normalized_quantity: null,
          normalized_unit: null,
          normalized_price: null,
          is_discounted: false,
          discount_info: null,
          supermarket: "coop",
          categories: [],
          attributes: {},
          image_url: null,
          product_url: "https://example.com/test",
          scraped_at: new Date(),
        },
      ];

      // Mock BEGIN transaction
      mockQuery.mockResolvedValueOnce({ rows: [] });
      // Mock INSERT query - simulate error
      mockQuery.mockRejectedValueOnce(new Error("Database error"));
      // Mock COMMIT transaction
      mockQuery.mockResolvedValueOnce({ rows: [] });

      const result = await repository.upsertBatch(products);

      expect(result.inserted).toBe(0);
      expect(result.updated).toBe(0);
      expect(result.failed).toBe(1);
      expect(mockRelease).toHaveBeenCalled();
    });

    it("should handle products with null values", async () => {
      const products: Product[] = [
        {
          name: "Simple Product",
          price: null,
          price_text: null,
          currency: "CHF",
          unit: null,
          unit_price: null,
          original_quantity: null,
          original_unit: null,
          normalized_quantity: null,
          normalized_unit: null,
          normalized_price: null,
          is_discounted: false,
          discount_info: null,
          supermarket: "migros",
          categories: [],
          attributes: {},
          image_url: null,
          product_url: "https://example.com/simple",
          scraped_at: new Date(),
        },
      ];

      // Mock BEGIN transaction
      mockQuery.mockResolvedValueOnce({ rows: [] });
      // Mock INSERT query
      mockQuery.mockResolvedValueOnce({ rows: [{ inserted: true }] });
      // Mock COMMIT transaction
      mockQuery.mockResolvedValueOnce({ rows: [] });

      const result = await repository.upsertBatch(products);

      expect(result.inserted).toBe(1);
      expect(result.failed).toBe(0);
    });

    it("should handle batch with multiple products", async () => {
      const products: Product[] = [
        {
          name: "Product 1",
          price: 1.0,
          price_text: "CHF 1.00",
          currency: "CHF",
          unit: "1kg",
          unit_price: null,
          original_quantity: 1,
          original_unit: "kg",
          normalized_quantity: 1,
          normalized_unit: "kg",
          normalized_price: 1.0,
          is_discounted: false,
          discount_info: null,
          supermarket: "coop",
          categories: ["Category1"],
          attributes: {},
          image_url: null,
          product_url: "https://example.com/p1",
          scraped_at: new Date(),
        },
        {
          name: "Product 2",
          price: 2.0,
          price_text: "CHF 2.00",
          currency: "CHF",
          unit: "500ml",
          unit_price: null,
          original_quantity: 500,
          original_unit: "ml",
          normalized_quantity: 0.5,
          normalized_unit: "L",
          normalized_price: 4.0,
          is_discounted: true,
          discount_info: "20% off",
          supermarket: "lidl",
          categories: ["Category2"],
          attributes: { bio: true },
          image_url: "https://example.com/img2.jpg",
          product_url: "https://example.com/p2",
          scraped_at: new Date(),
        },
      ];

      // Mock BEGIN transaction
      mockQuery.mockResolvedValueOnce({ rows: [] });
      // Mock first INSERT query
      mockQuery.mockResolvedValueOnce({ rows: [{ inserted: true }] });
      // Mock second INSERT query
      mockQuery.mockResolvedValueOnce({ rows: [{ inserted: false }] });
      // Mock COMMIT transaction
      mockQuery.mockResolvedValueOnce({ rows: [] });

      const result = await repository.upsertBatch(products);

      expect(result.inserted).toBe(1);
      expect(result.updated).toBe(1);
      expect(result.failed).toBe(0);
    });

    it("should rollback transaction on critical error", async () => {
      const products: Product[] = [
        {
          name: "Test Product",
          price: 1.0,
          price_text: "CHF 1.00",
          currency: "CHF",
          unit: null,
          unit_price: null,
          original_quantity: null,
          original_unit: null,
          normalized_quantity: null,
          normalized_unit: null,
          normalized_price: null,
          is_discounted: false,
          discount_info: null,
          supermarket: "coop",
          categories: [],
          attributes: {},
          image_url: null,
          product_url: "https://example.com/test",
          scraped_at: new Date(),
        },
      ];

      // Mock BEGIN transaction to fail
      mockQuery.mockRejectedValueOnce(new Error("Connection lost"));

      const result = await repository.upsertBatch(products);

      expect(result.inserted).toBe(0);
      expect(result.updated).toBe(0);
      expect(result.failed).toBe(1);
      expect(mockQuery).toHaveBeenCalledWith("ROLLBACK");
      expect(mockRelease).toHaveBeenCalled();
    });
  });

  describe("close", () => {
    it("should close the database connection", async () => {
      await repository.close();

      expect(mockPool.end).toHaveBeenCalled();
    });
  });
});
