import * as dotenv from "dotenv";
import { Pool } from "pg";
import { scanDirectory, CsvFileInfo } from "./parsers/file-scanner";
import { parseFile } from "./parsers/csv-parser";
import { transform } from "./transformers/product-transformer";
import { ProductRepository } from "./repositories/product-repository";
import { info, warn, error as logError } from "./utils/logger";
import * as path from "path";

/**
 * Statistics tracked during the import process
 */
export interface ImportStats {
  filesProcessed: number;
  totalRecords: number;
  inserted: number;
  updated: number;
  failed: number;
  duration: number;
}

/**
 * Configuration options for the import process
 */
export interface ImportOptions {
  dataDir: string;
  supermarket?: string;
  batchSize?: number;
}

/**
 * Main import function that orchestrates the entire CSV import process.
 * Scans for CSV files, parses them, transforms the data, and upserts to database.
 *
 * @param options - Import configuration options
 * @returns Statistics about the import process
 *
 * @example
 * ```typescript
 * const stats = await runImport({
 *   dataDir: '../data',
 *   supermarket: 'coop',
 *   batchSize: 500
 * });
 * console.log(`Processed ${stats.filesProcessed} files`);
 * ```
 */
export async function runImport(options: ImportOptions): Promise<ImportStats> {
  const startTime = Date.now();
  const batchSize = options.batchSize || 500;

  const stats: ImportStats = {
    filesProcessed: 0,
    totalRecords: 0,
    inserted: 0,
    updated: 0,
    failed: 0,
    duration: 0,
  };

  // Initialize database connection
  const pool = new Pool({
    connectionString: process.env.DATABASE_URL,
  });

  const repository = new ProductRepository(pool);

  try {
    info("Starting CSV import process...");
    info(`Data directory: ${options.dataDir}`);
    if (options.supermarket) {
      info(`Filtering by supermarket: ${options.supermarket}`);
    }
    info(`Batch size: ${batchSize}`);

    // Scan for CSV files
    info("Scanning for CSV files...");
    const files = await scanDirectory(options.dataDir, options.supermarket);
    info(`Found ${files.length} CSV files to process`);

    if (files.length === 0) {
      warn("No CSV files found. Exiting.");
      return stats;
    }

    // Process each file
    for (const fileInfo of files) {
      try {
        await processFile(fileInfo, repository, batchSize, stats);
        stats.filesProcessed++;
      } catch (err) {
        logError(
          `Failed to process file ${fileInfo.filePath}`,
          err instanceof Error ? err : undefined
        );
        // Continue processing other files
      }
    }

    // Calculate duration
    stats.duration = Date.now() - startTime;

    // Log final summary
    info("=".repeat(60));
    info("Import completed!");
    info(`Files processed: ${stats.filesProcessed}`);
    info(`Total records: ${stats.totalRecords}`);
    info(`Inserted: ${stats.inserted}`);
    info(`Updated: ${stats.updated}`);
    info(`Failed: ${stats.failed}`);
    info(`Duration: ${(stats.duration / 1000).toFixed(2)}s`);
    info("=".repeat(60));

    return stats;
  } finally {
    // Always close database connection
    await repository.close();
  }
}

/**
 * Processes a single CSV file: parses rows, transforms them, and upserts in batches.
 *
 * @param fileInfo - Information about the CSV file to process
 * @param repository - Database repository for upserting products
 * @param batchSize - Number of records to process in each batch
 * @param stats - Statistics object to update
 */
async function processFile(
  fileInfo: CsvFileInfo,
  repository: ProductRepository,
  batchSize: number,
  stats: ImportStats
): Promise<void> {
  info(`Processing file: ${fileInfo.filePath}`);
  info(`  Supermarket: ${fileInfo.supermarket}`);
  if (fileInfo.timestamp) {
    info(`  Timestamp: ${fileInfo.timestamp.toISOString()}`);
  }

  let batch: any[] = [];
  let recordCount = 0;

  try {
    // Parse CSV file and process in batches
    for await (const csvRow of parseFile(
      fileInfo.filePath,
      fileInfo.supermarket
    )) {
      // Validate required fields
      if (!csvRow.name || !csvRow.url) {
        warn(
          `Skipping record with missing required fields (name or url) in ${fileInfo.filePath}`
        );
        stats.failed++;
        continue;
      }

      // Transform CSV row to product
      const scrapedAt = fileInfo.timestamp || new Date();
      const product = transform(
        csvRow,
        fileInfo.supermarket as "migros" | "lidl" | "coop" | "denner",
        scrapedAt
      );

      batch.push(product);
      recordCount++;

      // Process batch when it reaches the batch size
      if (batch.length >= batchSize) {
        const result = await repository.upsertBatch(batch);
        stats.inserted += result.inserted;
        stats.updated += result.updated;
        stats.failed += result.failed;
        stats.totalRecords += batch.length;
        batch = [];
      }
    }

    // Process remaining records in the final batch
    if (batch.length > 0) {
      const result = await repository.upsertBatch(batch);
      stats.inserted += result.inserted;
      stats.updated += result.updated;
      stats.failed += result.failed;
      stats.totalRecords += batch.length;
    }

    info(`  Completed: ${recordCount} records processed`);
  } catch (err) {
    logError(
      `Error processing file ${fileInfo.filePath}`,
      err instanceof Error ? err : undefined
    );
    throw err;
  }
}

/**
 * Main entry point when running as a script
 */
async function main() {
  // Load environment variables
  dotenv.config();

  // Validate environment
  if (!process.env.DATABASE_URL) {
    logError("DATABASE_URL environment variable is required");
    process.exit(1);
  }

  // Determine data directory (relative to project root)
  const dataDir = path.resolve(__dirname, "../../data");

  // Run import
  try {
    const stats = await runImport({
      dataDir,
      batchSize: 500,
    });

    // Exit with success code
    process.exit(0);
  } catch (err) {
    logError("Import failed", err instanceof Error ? err : undefined);
    process.exit(1);
  }
}

// Run main function if this file is executed directly
if (require.main === module) {
  main();
}
