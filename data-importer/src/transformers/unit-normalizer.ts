import { UnitInfo, NormalizedUnit, StandardUnit } from "../models/unit.model";

/**
 * Handles extraction and normalization of product units
 */
export class UnitNormalizer {
  /**
   * Extract quantity and unit from a unit string
   * @param unitField - The unit field from CSV (e.g., "500g", "1 Stk", "2x200ml")
   * @returns UnitInfo object or null if no unit detected
   */
  extractUnit(unitField?: string): UnitInfo | null {
    if (!unitField || typeof unitField !== "string") {
      return null;
    }

    const trimmed = unitField.trim();
    if (!trimmed) {
      return null;
    }

    // Try multi-pack pattern first: 2x200g, 3x1kg, 6x500ml, 2x 50cl
    const multiPackMatch = trimmed.match(
      /(\d+)x\s*(\d+(?:[.,]\d+)?)\s*(g|kg|mg|ml|cl|l|m)/i
    );
    if (multiPackMatch) {
      const packCount = parseInt(multiPackMatch[1], 10);
      const packSize = parseFloat(multiPackMatch[2].replace(",", "."));
      const unit = multiPackMatch[3];
      const totalQuantity = packCount * packSize;
      return { quantity: totalQuantity, unit };
    }

    // Try weight pattern: 500g, 1kg, 1,5kg, 600mg
    const weightMatch = trimmed.match(/(\d+(?:[.,]\d+)?)\s*(mg|g|kg)/i);
    if (weightMatch) {
      const quantity = parseFloat(weightMatch[1].replace(",", "."));
      const unit = weightMatch[2];
      return { quantity, unit };
    }

    // Try volume pattern: 500ml, 1l, 1,5L, 50cl
    const volumeMatch = trimmed.match(/(\d+(?:[.,]\d+)?)\s*(ml|cl|l)/i);
    if (volumeMatch) {
      const quantity = parseFloat(volumeMatch[1].replace(",", "."));
      const unit = volumeMatch[2];
      return { quantity, unit };
    }

    // Try length pattern: 50m, 100m (for dental floss, string, etc.)
    const lengthMatch = trimmed.match(/(\d+(?:[.,]\d+)?)\s*m(?!g|l|2)/i);
    if (lengthMatch) {
      const quantity = parseFloat(lengthMatch[1].replace(",", "."));
      return { quantity, unit: "m" };
    }

    // Try area pattern: 9m2, 14.5m2 (for foil, paper)
    const areaMatch = trimmed.match(/(\d+(?:[.,]\d+)?)\s*m2/i);
    if (areaMatch) {
      const quantity = parseFloat(areaMatch[1].replace(",", "."));
      return { quantity, unit: "m2" };
    }

    // Try count pattern: 1 Stk, 3 Stk., 2 Stück, 10ST, 50ST, 4Rol, 8PAAR, 100BLT, 15WG, 1Bd
    const countMatch = trimmed.match(
      /(\d+)\s*(Stk\.?|Stück|ST|POR|Rol|PAAR|BLT|WG|Bd)/i
    );
    if (countMatch) {
      const quantity = parseInt(countMatch[1], 10);
      const unit = countMatch[2];
      return { quantity, unit };
    }

    return null;
  }

  /**
   * Normalize a unit to standard units (kg, L, unit)
   * @param unitInfo - The extracted unit information
   * @returns NormalizedUnit object or null if unit cannot be normalized
   */
  normalize(unitInfo: UnitInfo): NormalizedUnit | null {
    const unitLower = unitInfo.unit.toLowerCase();

    // Weight conversions - normalize to grams
    if (unitLower === "mg") {
      return {
        originalQuantity: unitInfo.quantity,
        originalUnit: unitInfo.unit,
        normalizedQuantity: unitInfo.quantity / 1000,
        normalizedUnit: StandardUnit.GRAM,
      };
    }

    if (unitLower === "g") {
      return {
        originalQuantity: unitInfo.quantity,
        originalUnit: unitInfo.unit,
        normalizedQuantity: unitInfo.quantity,
        normalizedUnit: StandardUnit.GRAM,
      };
    }

    if (unitLower === "kg") {
      return {
        originalQuantity: unitInfo.quantity,
        originalUnit: unitInfo.unit,
        normalizedQuantity: unitInfo.quantity * 1000,
        normalizedUnit: StandardUnit.GRAM,
      };
    }

    // Volume conversions - normalize to liters
    if (unitLower === "ml") {
      return {
        originalQuantity: unitInfo.quantity,
        originalUnit: unitInfo.unit,
        normalizedQuantity: unitInfo.quantity / 1000,
        normalizedUnit: StandardUnit.LITER,
      };
    }

    if (unitLower === "cl") {
      return {
        originalQuantity: unitInfo.quantity,
        originalUnit: unitInfo.unit,
        normalizedQuantity: unitInfo.quantity / 100,
        normalizedUnit: StandardUnit.LITER,
      };
    }

    if (unitLower === "l") {
      return {
        originalQuantity: unitInfo.quantity,
        originalUnit: unitInfo.unit,
        normalizedQuantity: unitInfo.quantity,
        normalizedUnit: StandardUnit.LITER,
      };
    }

    // Length conversions - normalize to meters
    if (unitLower === "m") {
      return {
        originalQuantity: unitInfo.quantity,
        originalUnit: unitInfo.unit,
        normalizedQuantity: unitInfo.quantity,
        normalizedUnit: StandardUnit.METER,
      };
    }

    // Area conversions - normalize to square meters
    if (unitLower === "m2") {
      return {
        originalQuantity: unitInfo.quantity,
        originalUnit: unitInfo.unit,
        normalizedQuantity: unitInfo.quantity,
        normalizedUnit: StandardUnit.SQUARE_METER,
      };
    }

    // Count conversions - normalize to units (Stk, ST, POR, Rol, PAAR, BLT, WG, Bd)
    if (
      unitLower === "stk" ||
      unitLower === "stk." ||
      unitLower === "stück" ||
      unitLower === "st" ||
      unitLower === "por" ||
      unitLower === "rol" ||
      unitLower === "paar" ||
      unitLower === "blt" ||
      unitLower === "wg" ||
      unitLower === "bd"
    ) {
      return {
        originalQuantity: unitInfo.quantity,
        originalUnit: unitInfo.unit,
        normalizedQuantity: unitInfo.quantity,
        normalizedUnit: StandardUnit.UNIT,
      };
    }

    // Unknown unit
    return null;
  }

  /**
   * Calculate the normalized price per standard unit
   * @param price - The product price (or null/undefined)
   * @param normalized - The normalized unit information
   * @returns The price per normalized unit, or null if price is null/undefined
   */
  calculateNormalizedPrice(
    price: number | null | undefined,
    normalized: NormalizedUnit
  ): number | null {
    if (price === null || price === undefined) {
      return null;
    }

    return price / normalized.normalizedQuantity;
  }
}
