import { describe, it, expect } from "vitest";
import { transform } from "./product-transformer";
import type { CsvRow } from "../parsers/csv-parser";

describe("ProductTransformer", () => {
  describe("transform", () => {
    it("should transform a complete CSV row into a product", () => {
      const csvRow: CsvRow = {
        store: "coop",
        name: "Naturaplan Bio Apfel",
        url: "https://example.com/product/123",
        price: "CHF 3.95",
        unit: "kg",
        unit_price: "3.95/kg",
        price_text: "CHF 3.95",
        has_discount: "true",
        discount_info: "20% off",
        image_url: "https://example.com/image.jpg",
        scraped_from: "https://example.com",
        category: "Fruits",
      };

      const product = transform(csvRow, "coop", new Date("2025-01-15"));

      expect(product.name).toBe("Naturaplan Bio Apfel");
      expect(product.price).toBe(3.95);
      expect(product.price_text).toBe("CHF 3.95");
      expect(product.unit).toBe("kg");
      expect(product.unit_price).toBe("3.95/kg");
      expect(product.is_discounted).toBe(true);
      expect(product.discount_info).toBe("20% off");
      expect(product.supermarket).toBe("coop");
      expect(product.categories).toEqual(["Fruits"]);
      expect(product.attributes.bio).toBe(true);
      expect(product.image_url).toBe("https://example.com/image.jpg");
      expect(product.product_url).toBe("https://example.com/product/123");
      expect(product.scraped_at).toEqual(new Date("2025-01-15"));
    });

    it("should extract Bio attribute from product name", () => {
      const testCases = [
        { name: "Naturaplan Bio Apfel", expected: true },
        { name: "Bio Milch", expected: true },
        { name: "BIO Eier", expected: true },
        { name: "Organic Bananas", expected: false },
        { name: "Antibiotic Free Chicken", expected: false },
      ];

      testCases.forEach(({ name, expected }) => {
        const csvRow: CsvRow = {
          name,
          url: "https://example.com/product",
          store: "coop",
        };

        const product = transform(csvRow, "coop", new Date());
        expect(product.attributes.bio).toBe(expected ? true : undefined);
      });
    });

    it("should extract Fairtrade attribute from product name", () => {
      const testCases = [
        { name: "Fairtrade Kaffee", expected: true },
        { name: "FAIRTRADE Schokolade", expected: true },
        { name: "Fair Trade Coffee", expected: false },
        { name: "Regular Coffee", expected: false },
      ];

      testCases.forEach(({ name, expected }) => {
        const csvRow: CsvRow = {
          name,
          url: "https://example.com/product",
          store: "coop",
        };

        const product = transform(csvRow, "coop", new Date());
        expect(product.attributes.fairtrade).toBe(expected ? true : undefined);
      });
    });

    it("should extract Max Havelaar attribute from product name", () => {
      const csvRow: CsvRow = {
        name: "Max Havelaar Kaffee",
        url: "https://example.com/product",
        store: "coop",
      };

      const product = transform(csvRow, "coop", new Date());
      expect(product.attributes.max_havelaar).toBe(true);
    });

    it("should extract Demeter attribute from product name", () => {
      const csvRow: CsvRow = {
        name: "Demeter Karotten",
        url: "https://example.com/product",
        store: "coop",
      };

      const product = transform(csvRow, "coop", new Date());
      expect(product.attributes.demeter).toBe(true);
    });

    it("should extract Knospe attribute from product name", () => {
      const csvRow: CsvRow = {
        name: "Knospe Tomaten",
        url: "https://example.com/product",
        store: "coop",
      };

      const product = transform(csvRow, "coop", new Date());
      expect(product.attributes.knospe).toBe(true);
    });

    it("should extract multiple attributes from product name", () => {
      const csvRow: CsvRow = {
        name: "Bio Fairtrade Kaffee",
        url: "https://example.com/product",
        store: "coop",
      };

      const product = transform(csvRow, "coop", new Date());
      expect(product.attributes.bio).toBe(true);
      expect(product.attributes.fairtrade).toBe(true);
    });

    it("should return empty attributes object when no attributes found", () => {
      const csvRow: CsvRow = {
        name: "Regular Apples",
        url: "https://example.com/product",
        store: "coop",
      };

      const product = transform(csvRow, "coop", new Date());
      expect(product.attributes).toEqual({});
    });

    it("should parse price using price parser utility", () => {
      const testCases = [
        { price: "CHF 3.95", expected: 3.95 },
        { price: "4.95", expected: 4.95 },
        { price: "–.70", expected: 0.7 },
        { price: "invalid", expected: null },
        { price: undefined, expected: null },
      ];

      testCases.forEach(({ price, expected }) => {
        const csvRow: CsvRow = {
          name: "Test Product",
          url: "https://example.com/product",
          store: "coop",
          price,
        };

        const product = transform(csvRow, "coop", new Date());
        expect(product.price).toBe(expected);
      });
    });

    it("should convert has_discount string to boolean", () => {
      const testCases = [
        { has_discount: "true", expected: true },
        { has_discount: "false", expected: false },
        { has_discount: "1", expected: true },
        { has_discount: "0", expected: false },
        { has_discount: "yes", expected: true },
        { has_discount: "no", expected: false },
        { has_discount: true, expected: true },
        { has_discount: false, expected: false },
        { has_discount: undefined, expected: false },
      ];

      testCases.forEach(({ has_discount, expected }) => {
        const csvRow: CsvRow = {
          name: "Test Product",
          url: "https://example.com/product",
          store: "coop",
          has_discount,
        };

        const product = transform(csvRow, "coop", new Date());
        expect(product.is_discounted).toBe(expected);
      });
    });

    it("should parse single category into array", () => {
      const csvRow: CsvRow = {
        name: "Test Product",
        url: "https://example.com/product",
        store: "coop",
        category: "Fruits",
      };

      const product = transform(csvRow, "coop", new Date());
      expect(product.categories).toEqual(["Fruits"]);
    });

    it("should parse multiple categories separated by comma", () => {
      const csvRow: CsvRow = {
        name: "Test Product",
        url: "https://example.com/product",
        store: "coop",
        category: "Fruits, Organic, Fresh",
      };

      const product = transform(csvRow, "coop", new Date());
      expect(product.categories).toEqual(["Fruits", "Organic", "Fresh"]);
    });

    it("should trim whitespace from categories", () => {
      const csvRow: CsvRow = {
        name: "Test Product",
        url: "https://example.com/product",
        store: "coop",
        category: "  Fruits  ,  Organic  ",
      };

      const product = transform(csvRow, "coop", new Date());
      expect(product.categories).toEqual(["Fruits", "Organic"]);
    });

    it("should handle empty category as empty array", () => {
      const csvRow: CsvRow = {
        name: "Test Product",
        url: "https://example.com/product",
        store: "coop",
        category: "",
      };

      const product = transform(csvRow, "coop", new Date());
      expect(product.categories).toEqual([]);
    });

    it("should handle undefined category as empty array", () => {
      const csvRow: CsvRow = {
        name: "Test Product",
        url: "https://example.com/product",
        store: "coop",
      };

      const product = transform(csvRow, "coop", new Date());
      expect(product.categories).toEqual([]);
    });

    it("should handle null values for optional fields", () => {
      const csvRow: CsvRow = {
        name: "Test Product",
        url: "https://example.com/product",
        store: "coop",
      };

      const product = transform(csvRow, "coop", new Date());
      expect(product.price).toBe(null);
      expect(product.price_text).toBe(null);
      expect(product.unit).toBe(null);
      expect(product.unit_price).toBe(null);
      expect(product.discount_info).toBe(null);
      expect(product.image_url).toBe(null);
    });

    it("should use provided supermarket parameter", () => {
      const csvRow: CsvRow = {
        name: "Test Product",
        url: "https://example.com/product",
        store: "different",
      };

      const product = transform(csvRow, "migros", new Date());
      expect(product.supermarket).toBe("migros");
    });

    it("should use provided scraped_at timestamp", () => {
      const scrapedAt = new Date("2025-01-15T10:30:00Z");
      const csvRow: CsvRow = {
        name: "Test Product",
        url: "https://example.com/product",
        store: "coop",
      };

      const product = transform(csvRow, "coop", scrapedAt);
      expect(product.scraped_at).toEqual(scrapedAt);
    });
  });
});
