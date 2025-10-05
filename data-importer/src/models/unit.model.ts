/**
 * Standard unit types for normalization
 */
export enum StandardUnit {
  KILOGRAM = "kg",
  LITER = "L",
  UNIT = "unit",
}

/**
 * Represents extracted quantity and unit information from product data
 */
export interface UnitInfo {
  quantity: number;
  unit: string;
}

/**
 * Represents normalized unit data with both original and converted values
 */
export interface NormalizedUnit {
  originalQuantity: number;
  originalUnit: string;
  normalizedQuantity: number;
  normalizedUnit: StandardUnit;
}
