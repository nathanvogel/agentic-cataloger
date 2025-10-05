import { describe, it, expect } from "vitest";
import { UnitNormalizer } from "./unit-normalizer";
import { StandardUnit } from "../models/unit.model";

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

    it("should extract volume in centiliters", () => {
      const result = normalizer.extractUnit("50cl");
      expect(result).toEqual({ quantity: 50, unit: "cl" });
    });

    it("should extract volume in centiliters with decimal", () => {
      const result = normalizer.extractUnit("33,5cl");
      expect(result).toEqual({ quantity: 33.5, unit: "cl" });
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

    it("should extract count with ST", () => {
      const result = normalizer.extractUnit("10ST");
      expect(result).toEqual({ quantity: 10, unit: "ST" });
    });

    it("should extract count with POR (portions)", () => {
      const result = normalizer.extractUnit("12POR");
      expect(result).toEqual({ quantity: 12, unit: "POR" });
    });

    it("should extract count with Rol (rolls)", () => {
      const result = normalizer.extractUnit("10Rol");
      expect(result).toEqual({ quantity: 10, unit: "Rol" });
    });

    it("should extract count with PAAR (pairs)", () => {
      const result = normalizer.extractUnit("8PAAR");
      expect(result).toEqual({ quantity: 8, unit: "PAAR" });
    });

    it("should extract count with BLT (sheets)", () => {
      const result = normalizer.extractUnit("500BLT");
      expect(result).toEqual({ quantity: 500, unit: "BLT" });
    });

    it("should extract count with WG (washes)", () => {
      const result = normalizer.extractUnit("15WG");
      expect(result).toEqual({ quantity: 15, unit: "WG" });
    });

    it("should extract count with Bd (bunch)", () => {
      const result = normalizer.extractUnit("1Bd");
      expect(result).toEqual({ quantity: 1, unit: "Bd" });
    });

    it("should extract length in meters", () => {
      const result = normalizer.extractUnit("50m");
      expect(result).toEqual({ quantity: 50, unit: "m" });
    });

    it("should extract length in meters with decimal", () => {
      const result = normalizer.extractUnit("100m");
      expect(result).toEqual({ quantity: 100, unit: "m" });
    });

    it("should extract area in square meters", () => {
      const result = normalizer.extractUnit("9m2");
      expect(result).toEqual({ quantity: 9, unit: "m2" });
    });

    it("should extract area in square meters with decimal", () => {
      const result = normalizer.extractUnit("14.5m2");
      expect(result).toEqual({ quantity: 14.5, unit: "m2" });
    });

    it("should extract weight in milligrams", () => {
      const result = normalizer.extractUnit("600mg");
      expect(result).toEqual({ quantity: 600, unit: "mg" });
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

    it("should extract multi-pack volume (centiliters)", () => {
      const result = normalizer.extractUnit("6x50cl");
      expect(result).toEqual({ quantity: 300, unit: "cl" });
    });

    it("should extract multi-pack with spaces", () => {
      const result = normalizer.extractUnit("2x 50cl");
      expect(result).toEqual({ quantity: 100, unit: "cl" });
    });

    it("should extract multi-pack with spaces (grams)", () => {
      const result = normalizer.extractUnit("4x 200g");
      expect(result).toEqual({ quantity: 800, unit: "g" });
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
    it("should keep grams as grams", () => {
      const unitInfo = { quantity: 500, unit: "g" };
      const result = normalizer.normalize(unitInfo);
      expect(result).toEqual({
        originalQuantity: 500,
        originalUnit: "g",
        normalizedQuantity: 500,
        normalizedUnit: "g",
      });
    });

    it("should convert kilograms to grams", () => {
      const unitInfo = { quantity: 1, unit: "kg" };
      const result = normalizer.normalize(unitInfo);
      expect(result).toEqual({
        originalQuantity: 1,
        originalUnit: "kg",
        normalizedQuantity: 1000,
        normalizedUnit: "g",
      });
    });

    it("should convert milligrams to grams", () => {
      const unitInfo = { quantity: 600, unit: "mg" };
      const result = normalizer.normalize(unitInfo);
      expect(result).toEqual({
        originalQuantity: 600,
        originalUnit: "mg",
        normalizedQuantity: 0.6,
        normalizedUnit: "g",
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

    it("should convert ST to unit", () => {
      const unitInfo = { quantity: 10, unit: "ST" };
      const result = normalizer.normalize(unitInfo);
      expect(result).toEqual({
        originalQuantity: 10,
        originalUnit: "ST",
        normalizedQuantity: 10,
        normalizedUnit: "unit",
      });
    });

    it("should convert POR to unit", () => {
      const unitInfo = { quantity: 12, unit: "POR" };
      const result = normalizer.normalize(unitInfo);
      expect(result).toEqual({
        originalQuantity: 12,
        originalUnit: "POR",
        normalizedQuantity: 12,
        normalizedUnit: "unit",
      });
    });

    it("should convert centiliters to liters", () => {
      const unitInfo = { quantity: 50, unit: "cl" };
      const result = normalizer.normalize(unitInfo);
      expect(result).toEqual({
        originalQuantity: 50,
        originalUnit: "cl",
        normalizedQuantity: 0.5,
        normalizedUnit: "L",
      });
    });

    it("should convert centiliters to liters (large quantity)", () => {
      const unitInfo = { quantity: 300, unit: "cl" };
      const result = normalizer.normalize(unitInfo);
      expect(result).toEqual({
        originalQuantity: 300,
        originalUnit: "cl",
        normalizedQuantity: 3,
        normalizedUnit: "L",
      });
    });

    it("should keep meters as meters", () => {
      const unitInfo = { quantity: 50, unit: "m" };
      const result = normalizer.normalize(unitInfo);
      expect(result).toEqual({
        originalQuantity: 50,
        originalUnit: "m",
        normalizedQuantity: 50,
        normalizedUnit: "m",
      });
    });

    it("should keep square meters as square meters", () => {
      const unitInfo = { quantity: 9, unit: "m2" };
      const result = normalizer.normalize(unitInfo);
      expect(result).toEqual({
        originalQuantity: 9,
        originalUnit: "m2",
        normalizedQuantity: 9,
        normalizedUnit: "m2",
      });
    });

    it("should convert Rol to unit", () => {
      const unitInfo = { quantity: 10, unit: "Rol" };
      const result = normalizer.normalize(unitInfo);
      expect(result).toEqual({
        originalQuantity: 10,
        originalUnit: "Rol",
        normalizedQuantity: 10,
        normalizedUnit: "unit",
      });
    });

    it("should convert PAAR to unit", () => {
      const unitInfo = { quantity: 8, unit: "PAAR" };
      const result = normalizer.normalize(unitInfo);
      expect(result).toEqual({
        originalQuantity: 8,
        originalUnit: "PAAR",
        normalizedQuantity: 8,
        normalizedUnit: "unit",
      });
    });

    it("should convert BLT to unit", () => {
      const unitInfo = { quantity: 500, unit: "BLT" };
      const result = normalizer.normalize(unitInfo);
      expect(result).toEqual({
        originalQuantity: 500,
        originalUnit: "BLT",
        normalizedQuantity: 500,
        normalizedUnit: "unit",
      });
    });

    it("should convert WG to unit", () => {
      const unitInfo = { quantity: 15, unit: "WG" };
      const result = normalizer.normalize(unitInfo);
      expect(result).toEqual({
        originalQuantity: 15,
        originalUnit: "WG",
        normalizedQuantity: 15,
        normalizedUnit: "unit",
      });
    });

    it("should convert Bd to unit", () => {
      const unitInfo = { quantity: 1, unit: "Bd" };
      const result = normalizer.normalize(unitInfo);
      expect(result).toEqual({
        originalQuantity: 1,
        originalUnit: "Bd",
        normalizedQuantity: 1,
        normalizedUnit: "unit",
      });
    });

    it("should handle case insensitive units (G to g)", () => {
      const unitInfo = { quantity: 250, unit: "G" };
      const result = normalizer.normalize(unitInfo);
      expect(result).toEqual({
        originalQuantity: 250,
        originalUnit: "G",
        normalizedQuantity: 250,
        normalizedUnit: "g",
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
        normalizedQuantity: 500,
        normalizedUnit: StandardUnit.GRAM,
      };
      const result = normalizer.calculateNormalizedPrice(2.5, normalized);
      expect(result).toBe(0.005);
    });

    it("should handle decimal prices", () => {
      const normalized = {
        originalQuantity: 250,
        originalUnit: "g",
        normalizedQuantity: 250,
        normalizedUnit: StandardUnit.GRAM,
      };
      const result = normalizer.calculateNormalizedPrice(1.99, normalized);
      expect(result).toBeCloseTo(0.00796, 5);
    });

    it("should handle volume normalization", () => {
      const normalized = {
        originalQuantity: 500,
        originalUnit: "ml",
        normalizedQuantity: 0.5,
        normalizedUnit: StandardUnit.LITER,
      };
      const result = normalizer.calculateNormalizedPrice(3.0, normalized);
      expect(result).toBe(6.0);
    });

    it("should handle unit count", () => {
      const normalized = {
        originalQuantity: 1,
        originalUnit: "Stk",
        normalizedQuantity: 1,
        normalizedUnit: StandardUnit.UNIT,
      };
      const result = normalizer.calculateNormalizedPrice(0.5, normalized);
      expect(result).toBe(0.5);
    });

    it("should handle length normalization", () => {
      const normalized = {
        originalQuantity: 50,
        originalUnit: "m",
        normalizedQuantity: 50,
        normalizedUnit: StandardUnit.METER,
      };
      const result = normalizer.calculateNormalizedPrice(5.0, normalized);
      expect(result).toBe(0.1);
    });

    it("should handle area normalization", () => {
      const normalized = {
        originalQuantity: 9,
        originalUnit: "m2",
        normalizedQuantity: 9,
        normalizedUnit: StandardUnit.SQUARE_METER,
      };
      const result = normalizer.calculateNormalizedPrice(4.5, normalized);
      expect(result).toBe(0.5);
    });

    it("should return null for null price", () => {
      const normalized = {
        originalQuantity: 500,
        originalUnit: "g",
        normalizedQuantity: 500,
        normalizedUnit: StandardUnit.GRAM,
      };
      const result = normalizer.calculateNormalizedPrice(null, normalized);
      expect(result).toBeNull();
    });

    it("should return null for undefined price", () => {
      const normalized = {
        originalQuantity: 500,
        originalUnit: "g",
        normalizedQuantity: 500,
        normalizedUnit: StandardUnit.GRAM,
      };
      const result = normalizer.calculateNormalizedPrice(undefined, normalized);
      expect(result).toBeNull();
    });
  });
});
