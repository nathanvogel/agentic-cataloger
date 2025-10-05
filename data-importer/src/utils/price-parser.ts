/**
 * Parses price strings from various formats into numeric values
 *
 * Supported formats:
 * - "CHF 3.95" -> 3.95
 * - "4.95" -> 4.95
 * - "–.70 (per Stück)" -> 0.70
 * - "–.70" -> 0.70
 *
 * @param priceStr - The price string to parse
 * @returns The numeric price value or null if invalid
 */
export function parsePrice(priceStr: string | null | undefined): number | null {
  if (!priceStr || typeof priceStr !== "string") {
    return null;
  }

  // Remove common prefixes and suffixes
  let cleaned = priceStr.trim();

  // Remove "CHF" prefix (case insensitive)
  cleaned = cleaned.replace(/^CHF\s*/i, "");

  // Remove parenthetical suffixes like "(per Stück)"
  cleaned = cleaned.replace(/\s*\([^)]*\)\s*$/, "");

  // Replace en-dash or em-dash with regular dash
  cleaned = cleaned.replace(/[–—]/, "-");

  // Handle negative numbers or numbers starting with dash (like "–.70")
  // If it starts with a dash followed by a dot, add a leading zero
  cleaned = cleaned.replace(/^-\./, "0.");

  // Extract the first number (integer or decimal)
  const match = cleaned.match(/-?\d+\.?\d*/);

  if (!match) {
    return null;
  }

  const parsed = parseFloat(match[0]);

  // Validate the result
  if (isNaN(parsed) || !isFinite(parsed)) {
    return null;
  }

  return parsed;
}
