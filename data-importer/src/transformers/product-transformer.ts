import type { CsvRow } from "../parsers/csv-parser";
import { parsePrice } from "../utils/price-parser";
import { UnitNormalizer } from "./unit-normalizer";
import { info, warn } from "../utils/logger";

/**
 * Represents a product ready for database insertion
 */
export interface Product {
  name: string;
  price: number | null;
  price_text: string | null;
  currency: string;
  unit: string | null;
  unit_price: string | null;
  original_quantity: number | null;
  original_unit: string | null;
  normalized_quantity: number | null;
  normalized_unit: string | null;
  normalized_price: number | null;
  is_discounted: boolean;
  discount_info: string | null;
  supermarket: "migros" | "lidl" | "coop" | "denner";
  categories: string[];
  attributes: Record<string, any>;
  image_url: string | null;
  product_url: string;
  scraped_at: Date;
}

// Create a shared instance of UnitNormalizer
const unitNormalizer = new UnitNormalizer();

/**
 * Transforms a CSV row into a database-ready product object.
 * Extracts attributes from product name, parses price, converts discount flag,
 * normalizes categories, and normalizes units.
 *
 * @param csvRow - Raw CSV row data
 * @param supermarket - Supermarket identifier
 * @param scrapedAt - Timestamp when the data was scraped
 * @returns Database-ready product object
 *
 * @example
 * ```typescript
 * const csvRow = {
 *   name: "Naturaplan Bio Apfel",
 *   url: "https://example.com/product",
 *   price: "CHF 3.95",
 *   unit: "500g",
 *   has_discount: "true",
 *   category: "Fruits"
 * };
 * const product = transform(csvRow, "coop", new Date());
 * // product.attributes.bio === true
 * // product.price === 3.95
 * // product.normalized_quantity === 0.5
 * // product.normalized_unit === "kg"
 * // product.normalized_price === 7.90
 * // product.categories === ["Fruits"]
 * ```
 */
export function transform(
  csvRow: CsvRow,
  supermarket: "migros" | "lidl" | "coop" | "denner",
  scrapedAt: Date
): Product {
  const price = parsePrice(csvRow.price);
  const currency = extractCurrency(csvRow.price_text || csvRow.price);

  // Extract and normalize unit information
  const unitInfo = unitNormalizer.extractUnit(csvRow.unit);
  const normalized = unitInfo ? unitNormalizer.normalize(unitInfo) : null;
  const normalizedPrice =
    normalized && price !== null
      ? unitNormalizer.calculateNormalizedPrice(price, normalized)
      : null;

  // Log warning if unit extraction fails but unit field exists
  if (csvRow.unit && !unitInfo) {
    warn(
      `Failed to extract unit from: "${csvRow.unit}" for product: ${csvRow.name}`
    );
  }

  return {
    name: csvRow.name,
    price,
    price_text: csvRow.price_text || null,
    currency,
    unit: csvRow.unit || null,
    unit_price: csvRow.unit_price || null,
    original_quantity: normalized?.originalQuantity || null,
    original_unit: normalized?.originalUnit || null,
    normalized_quantity: normalized?.normalizedQuantity || null,
    normalized_unit: normalized?.normalizedUnit || null,
    normalized_price: normalizedPrice,
    is_discounted: parseBoolean(csvRow.has_discount),
    discount_info: csvRow.discount_info || null,
    supermarket,
    categories: extractCategories(csvRow.category),
    attributes: extractAttributes(csvRow.name),
    image_url: csvRow.image_url || null,
    product_url: csvRow.url,
    scraped_at: scrapedAt,
  };
}

/**
 * Extracts currency code from price text.
 * Defaults to "CHF" for Swiss products.
 *
 * @param priceText - Price text that may contain currency code
 * @returns Currency code (e.g., "CHF", "EUR")
 *
 * @example
 * ```typescript
 * extractCurrency("CHF 3.95")  // "CHF"
 * extractCurrency("3.95")      // "CHF"
 * extractCurrency("EUR 5.00")  // "EUR"
 * ```
 */
function extractCurrency(priceText: string | undefined): string {
  if (!priceText) {
    return "CHF";
  }

  // Try to extract currency code (3 uppercase letters)
  const match = priceText.match(/\b([A-Z]{3})\b/);
  return match ? match[1] : "CHF";
}

/**
 * Extracts product attributes from the product name using regex patterns.
 * Detects: Bio, Fairtrade, Max Havelaar, Demeter, Knospe
 *
 * @param name - Product name to analyze
 * @returns Object with detected attributes as boolean flags
 *
 * @example
 * ```typescript
 * extractAttributes("Bio Fairtrade Kaffee")
 * // Returns: { bio: true, fairtrade: true }
 * ```
 */
function extractAttributes(name: string): Record<string, any> {
  const attributes: Record<string, any> = {};

  // Bio detection (including "Naturaplan Bio")
  if (/\b(bio|naturaplan bio)\b/i.test(name)) {
    attributes.bio = true;
  }

  // Fairtrade detection
  if (/\bfairtrade\b/i.test(name)) {
    attributes.fairtrade = true;
  }

  // Max Havelaar detection
  if (/\bmax havelaar\b/i.test(name)) {
    attributes.max_havelaar = true;
  }

  // Demeter detection
  if (/\bdemeter\b/i.test(name)) {
    attributes.demeter = true;
  }

  // Knospe detection
  if (/\bknospe\b/i.test(name)) {
    attributes.knospe = true;
  }

  return attributes;
}

/**
 * Converts various boolean representations to actual boolean values.
 * Handles: "true"/"false", "1"/"0", "yes"/"no", true/false, undefined
 *
 * @param value - Value to convert to boolean
 * @returns Boolean representation, defaults to false for undefined/invalid values
 *
 * @example
 * ```typescript
 * parseBoolean("true")  // true
 * parseBoolean("1")     // true
 * parseBoolean("yes")   // true
 * parseBoolean(false)   // false
 * parseBoolean(undefined) // false
 * ```
 */
function parseBoolean(value: string | boolean | undefined): boolean {
  if (typeof value === "boolean") {
    return value;
  }

  if (typeof value === "string") {
    const normalized = value.toLowerCase().trim();
    return normalized === "true" || normalized === "1" || normalized === "yes";
  }

  return false;
}

/**
 * Parses category string into an array of normalized category names.
 * Handles comma-separated categories and trims whitespace.
 *
 * @param category - Category string (may be comma-separated)
 * @returns Array of normalized category names
 *
 * @example
 * ```typescript
 * extractCategories("Fruits, Organic, Fresh")
 * // Returns: ["Fruits", "Organic", "Fresh"]
 *
 * extractCategories("  Fruits  ")
 * // Returns: ["Fruits"]
 *
 * extractCategories(undefined)
 * // Returns: []
 * ```
 */
function extractCategories(category: string | undefined): string[] {
  if (!category || category.trim() === "") {
    return [];
  }

  return category
    .split(",")
    .map((cat) => cat.trim())
    .filter((cat) => cat.length > 0);
}
