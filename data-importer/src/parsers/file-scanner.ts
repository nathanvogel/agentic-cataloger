import * as fs from "fs/promises";
import * as path from "path";

export interface CsvFileInfo {
  filePath: string;
  supermarket: string;
  timestamp?: Date;
}

/**
 * Recursively scans a directory for CSV files and extracts metadata
 * @param rootDir - Root directory to scan
 * @param supermarketFilter - Optional filter to only include specific supermarket
 * @returns Array of CSV file information
 */
export async function scanDirectory(
  rootDir: string,
  supermarketFilter?: string
): Promise<CsvFileInfo[]> {
  const results: CsvFileInfo[] = [];

  async function scan(dir: string): Promise<void> {
    const entries = await fs.readdir(dir, { withFileTypes: true });

    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);

      if (entry.isDirectory()) {
        // Recursively scan subdirectories
        await scan(fullPath);
      } else if (entry.isFile() && entry.name.endsWith(".csv")) {
        // Extract supermarket from path
        const supermarket = extractSupermarket(fullPath);

        // Skip if supermarket filter is specified and doesn't match
        if (supermarketFilter && supermarket !== supermarketFilter) {
          continue;
        }

        // Extract timestamp from filename and path
        const timestamp = extractTimestamp(fullPath);

        results.push({
          filePath: fullPath,
          supermarket,
          timestamp,
        });
      }
    }
  }

  await scan(rootDir);
  return results;
}

/**
 * Extracts supermarket name from file path
 * @param filePath - Full file path
 * @returns Supermarket name (e.g., "coop", "lidl", "denner", "migros")
 */
function extractSupermarket(filePath: string): string {
  // Match pattern: {supermarket}-ch-products
  const match = filePath.match(/([a-z]+)-ch-products/i);

  if (match) {
    return match[1].toLowerCase();
  }

  // Fallback: return "unknown" if pattern not found
  return "unknown";
}

/**
 * Extracts timestamp from file path and filename
 * Expected patterns:
 * - Directory structure: YYYY/MM/
 * - Filename: DD-HH:MM.csv
 * @param filePath - Full file path
 * @returns Date object or undefined if timestamp cannot be extracted
 */
function extractTimestamp(filePath: string): Date | undefined {
  // Try to match pattern: /YYYY/MM/DD-HH:MM.csv
  const match = filePath.match(
    /\/(\d{4})\/(\d{2})\/(\d{2})-(\d{2}):(\d{2})\.csv$/
  );

  if (match) {
    const [, year, month, day, hour, minute] = match;
    return new Date(
      parseInt(year),
      parseInt(month) - 1, // Month is 0-indexed
      parseInt(day),
      parseInt(hour),
      parseInt(minute)
    );
  }

  return undefined;
}
