import { parse } from "csv-parse";
import { createReadStream } from "fs";

/**
 * Represents a row from a CSV file with all possible columns.
 * Optional fields may be undefined or empty strings depending on the CSV structure.
 */
export interface CsvRow {
  store?: string;
  name: string;
  url: string;
  price?: string;
  unit?: string;
  unit_price?: string;
  price_text?: string;
  has_discount?: string | boolean;
  discount_info?: string;
  image_url?: string;
  scraped_from?: string;
  category?: string;
}

/**
 * Parses a CSV file and yields rows as typed objects.
 * Uses streaming to handle large files efficiently without loading entire file into memory.
 *
 * @param filePath - Path to the CSV file to parse
 * @param supermarket - Supermarket name to use if "store" column is missing
 * @yields Normalized CSV rows with store field populated
 *
 * @example
 * ```typescript
 * for await (const row of parseFile('data.csv', 'coop')) {
 *   console.log(row.name, row.price);
 * }
 * ```
 */
export async function* parseFile(
  filePath: string,
  supermarket: string
): AsyncGenerator<CsvRow> {
  const parser = createReadStream(filePath).pipe(
    parse({
      columns: true,
      skip_empty_lines: true,
      trim: true,
      relax_quotes: true,
    })
  );

  for await (const record of parser) {
    yield normalizeRow(record, supermarket);
  }
}

/**
 * Normalizes a raw CSV row by ensuring the store field is populated.
 * If the CSV doesn't have a "store" column, uses the supermarket parameter.
 *
 * @param row - Raw row object from CSV parser
 * @param supermarket - Supermarket name to use as fallback
 * @returns Normalized CSV row with store field
 */
function normalizeRow(row: any, supermarket: string): CsvRow {
  return {
    store: row.store || supermarket,
    name: row.name,
    url: row.url,
    price: row.price,
    unit: row.unit,
    unit_price: row.unit_price,
    price_text: row.price_text,
    has_discount: row.has_discount,
    discount_info: row.discount_info,
    image_url: row.image_url,
    scraped_from: row.scraped_from,
    category: row.category,
  };
}
