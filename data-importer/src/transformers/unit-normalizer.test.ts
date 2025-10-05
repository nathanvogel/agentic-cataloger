import { describe, it, expect } from "vitest";
import { UnitNormalizer } from "./unit-normalizer";

describe("UnitNormalizer", () => {
  const normalizer = new UnitNormalizer();

  describe("extractUnit", () => {
    it("should extract weight in grams", () => {
      const result = normalizer.extractUnit("500g");
      expect(result).toEqual({ quantity: 500, unit: "g" });
    });

    it("should extract weight in kilograms", () => {
      const result = normalizer.extractUnit("1kg");
      expect(result).toEqual({ quantity: 1, unit: "kg" });
    });

    it("should extract weight with decimal (European format)", () => {
      const result = normalizer.extractUnit("1,5kg");
      expect(result).toEqual({ quantity: 1.5, unit: "kg" });
    });

    it("should extract weight with decimal (dot format)", () => {
      const result = normalizer.extractUnit("0.5kg");
      expect(result).toEqual({ quantity: 0.5, unit: "kg" });
    });

    it("should extract volume in milliliters", () => {
      const result = normalizer.extractUnit("500ml");
      expect(result).toEqual({ quantity: 500, unit: "ml" });
    });

    it("should extract volume in liters", () => {
      const result = normalizer.extractUnit("1l");
      expect(result).toEqual({ quantity: 1, unit: "l" });
    });

    it("should extract volume with decimal", () => {
      const result = normalizer.extractUnit("1,5L");
      expect(result).toEqual({ quantity: 1.5, unit: "L" });
    });

    it("should extract count with Stk", () => {
      const result = normalizer.extractUnit("1 Stk");
      expect(result).toEqual({ quantity: 1, unit: "Stk" });
    });

    it("should extract count with Stk.", () => {
      const result = normalizer.extractUnit("3 Stk.");
      expect(result).toEqual({ quantity: 3, unit: "Stk." });
    });

    it("should extract count with Stück", () => {
      const result = normalizer.extractUnit("2 Stück");
      expect(result).toEqual({ quantity: 2, unit: "Stück" });
    });

    it("should extract multi-pack weight (grams)", () => {
      const result = normalizer.extractUnit("2x200g");
      expect(result).toEqual({ quantity: 400, unit: "g" });
    });

    it("should extract multi-pack weight (kilograms)", () => {
      const result = normalizer.extractUnit("3x1kg");
      expect(result).toEqual({ quantity: 3, unit: "kg" });
    });

    it("should extract multi-pack volume (milliliters)", () => {
      const result = normalizer.extractUnit("6x500ml");
      expect(result).toEqual({ quantity: 3000, unit: "ml" });
    });

    it("should extract multi-pack volume (liters)", () => {
      const result = normalizer.extractUnit("4x1l");
      expect(result).toEqual({ quantity: 4, unit: "l" });
    });

    it("should handle weight with spaces", () => {
      const result = normalizer.extractUnit("500 g");
      expect(result).toEqual({ quantity: 500, unit: "g" });
    });

    it("should handle case insensitive units", () => {
      const result = normalizer.extractUnit("500G");
      expect(result).toEqual({ quantity: 500, unit: "G" });
    });

    it("should return null for no unit detected", () => {
      const result = normalizer.extractUnit("some product");
      expect(result).toBeNull();
    });

    it("should return null for empty string", () => {
      const result = normalizer.extractUnit("");
      expect(result).toBeNull();
    });

    it("should return null for undefined", () => {
      const result = normalizer.extractUnit(undefined);
      expect(result).toBeNull();
    });
  });

  describe("normalize", () => {
    it("should convert grams to kilograms", () => {
      const unitInfo = { quantity: 500, unit: "g" };
      const result = normalizer.normalize(unitInfo);
      expect(result).toEqual({
        originalQuantity: 500,
        originalUnit: "g",
        normalizedQuantity: 0.5,
        normalizedUnit: "kg",
      });
    });

    it("should keep kilograms as kilograms", () => {
      const unitInfo = { quantity: 1, unit: "kg" };
      const result = normalizer.normalize(unitInfo);
      expect(result).toEqual({
        originalQuantity: 1,
        originalUnit: "kg",
        normalizedQuantity: 1,
        normalizedUnit: "kg",
      });
    });

    it("should convert milliliters to liters", () => {
      const unitInfo = { quantity: 500, unit: "ml" };
      const result = normalizer.normalize(unitInfo);
      expect(result).toEqual({
        originalQuantity: 500,
        originalUnit: "ml",
        normalizedQuantity: 0.5,
        normalizedUnit: "L",
      });
    });

    it("should keep liters as liters", () => {
      const unitInfo = { quantity: 1, unit: "l" };
      const result = normalizer.normalize(unitInfo);
      expect(result).toEqual({
        originalQuantity: 1,
        originalUnit: "l",
        normalizedQuantity: 1,
        normalizedUnit: "L",
      });
    });

    it("should convert Stk to unit", () => {
      const unitInfo = { quantity: 1, unit: "Stk" };
      const result = normalizer.normalize(unitInfo);
      expect(result).toEqual({
        originalQuantity: 1,
        originalUnit: "Stk",
        normalizedQuantity: 1,
        normalizedUnit: "unit",
      });
    });

    it("should convert Stk. to unit", () => {
      const unitInfo = { quantity: 3, unit: "Stk." };
      const result = normalizer.normalize(unitInfo);
      expect(result).toEqual({
        originalQuantity: 3,
        originalUnit: "Stk.",
        normalizedQuantity: 3,
        normalizedUnit: "unit",
      });
    });

    it("should convert Stück to unit", () => {
      const unitInfo = { quantity: 2, unit: "Stück" };
      const result = normalizer.normalize(unitInfo);
      expect(result).toEqual({
        originalQuantity: 2,
        originalUnit: "Stück",
        normalizedQuantity: 2,
        normalizedUnit: "unit",
      });
    });

    it("should handle case insensitive units (G to kg)", () => {
      const unitInfo = { quantity: 250, unit: "G" };
      const result = normalizer.normalize(unitInfo);
      expect(result).toEqual({
        originalQuantity: 250,
        originalUnit: "G",
        normalizedQuantity: 0.25,
        normalizedUnit: "kg",
      });
    });

    it("should handle case insensitive units (ML to L)", () => {
      const unitInfo = { quantity: 750, unit: "ML" };
      const result = normalizer.normalize(unitInfo);
      expect(result).toEqual({
        originalQuantity: 750,
        originalUnit: "ML",
        normalizedQuantity: 0.75,
        normalizedUnit: "L",
      });
    });

    it("should return null for unknown unit", () => {
      const unitInfo = { quantity: 100, unit: "unknown" };
      const result = normalizer.normalize(unitInfo);
      expect(result).toBeNull();
    });
  });

  describe("calculateNormalizedPrice", () => {
    it("should calculate normalized price correctly", () => {
      const normalized = {
        originalQuantity: 500,
        originalUnit: "g",
        normalizedQuantity: 0.5,
        normalizedUnit: "kg" as const,
      };
      const result = normalizer.calculateNormalizedPrice(2.5, normalized);
      expect(result).toBe(5.0);
    });

    it("should handle decimal prices", () => {
      const normalized = {
        originalQuantity: 250,
        originalUnit: "g",
        normalizedQuantity: 0.25,
        normalizedUnit: "kg" as const,
      };
      const result = normalizer.calculateNormalizedPrice(1.99, normalized);
      expect(result).toBeCloseTo(7.96, 2);
    });

    it("should handle volume normalization", () => {
      const normalized = {
        originalQuantity: 500,
        originalUnit: "ml",
        normalizedQuantity: 0.5,
        normalizedUnit: "L" as const,
      };
      const result = normalizer.calculateNormalizedPrice(3.0, normalized);
      expect(result).toBe(6.0);
    });

    it("should handle unit count", () => {
      const normalized = {
        originalQuantity: 1,
        originalUnit: "Stk",
        normalizedQuantity: 1,
        normalizedUnit: "unit" as const,
      };
      const result = normalizer.calculateNormalizedPrice(0.5, normalized);
      expect(result).toBe(0.5);
    });

    it("should return null for null price", () => {
      const normalized = {
        originalQuantity: 500,
        originalUnit: "g",
        normalizedQuantity: 0.5,
        normalizedUnit: "kg" as const,
      };
      const result = normalizer.calculateNormalizedPrice(null, normalized);
      expect(result).toBeNull();
    });

    it("should return null for undefined price", () => {
      const normalized = {
        originalQuantity: 500,
        originalUnit: "g",
        normalizedQuantity: 0.5,
        normalizedUnit: "kg" as const,
      };
      const result = normalizer.calculateNormalizedPrice(undefined, normalized);
      expect(result).toBeNull();
    });
  });
});
