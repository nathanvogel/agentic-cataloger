import { describe, it, expect } from "vitest";
import { parsePrice } from "./price-parser";

describe("parsePrice", () => {
  describe("valid price formats", () => {
    it('should parse "CHF 3.95" format', () => {
      expect(parsePrice("CHF 3.95")).toBe(3.95);
    });

    it('should parse "CHF 3.95" with lowercase', () => {
      expect(parsePrice("chf 3.95")).toBe(3.95);
    });

    it('should parse plain numeric string "4.95"', () => {
      expect(parsePrice("4.95")).toBe(4.95);
    });

    it('should parse "–.70 (per Stück)" format', () => {
      expect(parsePrice("–.70 (per Stück)")).toBe(0.7);
    });

    it('should parse "–.70" without parenthetical', () => {
      expect(parsePrice("–.70")).toBe(0.7);
    });

    it("should parse integer prices", () => {
      expect(parsePrice("5")).toBe(5);
      expect(parsePrice("CHF 10")).toBe(10);
    });

    it("should parse prices with extra whitespace", () => {
      expect(parsePrice("  CHF 3.95  ")).toBe(3.95);
      expect(parsePrice("  4.95  ")).toBe(4.95);
    });

    it("should parse prices with different dash characters", () => {
      expect(parsePrice("–.70")).toBe(0.7); // en-dash
      expect(parsePrice("—.70")).toBe(0.7); // em-dash
      expect(parsePrice("-.70")).toBe(0.7); // regular dash
    });

    it("should parse zero prices", () => {
      expect(parsePrice("0")).toBe(0);
      expect(parsePrice("0.00")).toBe(0);
      expect(parsePrice("CHF 0.00")).toBe(0);
    });
  });

  describe("invalid inputs", () => {
    it("should return null for null input", () => {
      expect(parsePrice(null)).toBe(null);
    });

    it("should return null for undefined input", () => {
      expect(parsePrice(undefined)).toBe(null);
    });

    it("should return null for empty string", () => {
      expect(parsePrice("")).toBe(null);
    });

    it("should return null for whitespace-only string", () => {
      expect(parsePrice("   ")).toBe(null);
    });

    it("should return null for non-numeric strings", () => {
      expect(parsePrice("abc")).toBe(null);
      expect(parsePrice("CHF")).toBe(null);
      expect(parsePrice("(per Stück)")).toBe(null);
    });

    it("should return null for invalid number formats", () => {
      expect(parsePrice("CHF abc")).toBe(null);
    });
  });

  describe("edge cases", () => {
    it("should handle very large prices", () => {
      expect(parsePrice("CHF 9999.99")).toBe(9999.99);
    });

    it("should handle very small prices", () => {
      expect(parsePrice("CHF 0.01")).toBe(0.01);
    });

    it("should extract first number if multiple present", () => {
      expect(parsePrice("CHF 3.95 or 4.95")).toBe(3.95);
    });
  });
});
