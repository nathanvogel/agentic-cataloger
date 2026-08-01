import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { runImport, ImportStats } from "./import";
import * as fileScanner from "./parsers/file-scanner";
import * as csvParser from "./parsers/csv-parser";
import { ProductRepository } from "./repositories/product-repository";
import { Pool } from "pg";

// Mock modules
vi.mock("./parsers/file-scanner");
vi.mock("./parsers/csv-parser");
vi.mock("pg");

describe("Import Script", () => {
  let mockPool: any;
  let mockRepository: any;

  beforeEach(() => {
    // Reset all mocks
    vi.clearAllMocks();

    // Mock Pool
    mockPool = {
      connect: vi.fn(),
      end: vi.fn(),
    };
    vi.mocked(Pool).mockImplementation(() => mockPool);

    // Mock ProductRepository
    mockRepository = {
      upsertBatch: vi.fn(),
      close: vi.fn(),
    };
    vi.spyOn(ProductRepository.prototype, "upsertBatch").mockImplementation(
      mockRepository.upsertBatch
    );
    vi.spyOn(ProductRepository.prototype, "close").mockImplementation(
      mockRepository.close
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("runImport", () => {
    it("should process CSV files and return statistics", async () => {
      // Mock file scanner to return test files
      const mockFiles = [
        {
          filePath: "/data/coop-ch-products/2025/08/22-16:00.csv",
          supermarket: "coop",
          timestamp: new Date("2025-08-22T16:00:00"),
        },
      ];
      vi.mocked(fileScanner.scanDirectory).mockResolvedValue(mockFiles);

      // Mock CSV parser to yield test rows
      const mockCsvRows = [
        {
          name: "Bio Apfel",
          url: "https://example.com/apfel",
          price: "CHF 3.95",
          unit: "500g",
          has_discount: "false",
          category: "Fruits",
        },
        {
          name: "Bio Milch",
          url: "https://example.com/milch",
          price: "CHF 1.50",
          unit: "1L",
          has_discount: "true",
          category: "Dairy",
        },
      ];

      async function* mockParseFile() {
        for (const row of mockCsvRows) {
          yield row;
        }
      }
      vi.mocked(csvParser.parseFile).mockImplementation(mockParseFile);

      // Mock repository upsert
      mockRepository.upsertBatch.mockResolvedValue({
        inserted: 2,
        updated: 0,
        failed: 0,
      });

      // Run import
      const stats = await runImport({
        dataDir: "/data",
        batchSize: 10,
      });

      // Verify results
      expect(stats.filesProcessed).toBe(1);
      expect(stats.totalRecords).toBe(2);
      expect(stats.inserted).toBe(2);
      expect(stats.updated).toBe(0);
      expect(stats.failed).toBe(0);
      expect(stats.duration).toBeGreaterThan(0);

      // Verify file scanner was called
      expect(fileScanner.scanDirectory).toHaveBeenCalledWith(
        "/data",
        undefined
      );

      // Verify CSV parser was called
      expect(csvParser.parseFile).toHaveBeenCalledWith(
        "/data/coop-ch-products/2025/08/22-16:00.csv",
        "coop"
      );

      // Verify repository was called
      expect(mockRepository.upsertBatch).toHaveBeenCalledTimes(1);
      expect(mockRepository.close).toHaveBeenCalled();
    });

    it("should filter by supermarket when specified", async () => {
      const mockFiles = [
        {
          filePath: "/data/lidl-ch-products/2025/08/01.csv",
          supermarket: "lidl",
          timestamp: new Date("2025-08-01T00:00:00"),
        },
      ];
      vi.mocked(fileScanner.scanDirectory).mockResolvedValue(mockFiles);

      async function* mockParseFile() {
        yield {
          name: "Test Product",
          url: "https://example.com/test",
          price: "5.00",
        };
      }
      vi.mocked(csvParser.parseFile).mockImplementation(mockParseFile);

      mockRepository.upsertBatch.mockResolvedValue({
        inserted: 1,
        updated: 0,
        failed: 0,
      });

      await runImport({
        dataDir: "/data",
        supermarket: "lidl",
      });

      // Verify file scanner was called with supermarket filter
      expect(fileScanner.scanDirectory).toHaveBeenCalledWith("/data", "lidl");
    });

    it("should process records in batches", async () => {
      const mockFiles = [
        {
          filePath: "/data/coop-ch-products/2025/08/22-16:00.csv",
          supermarket: "coop",
          timestamp: new Date("2025-08-22T16:00:00"),
        },
      ];
      vi.mocked(fileScanner.scanDirectory).mockResolvedValue(mockFiles);

      // Create 5 mock rows
      const mockCsvRows = Array.from({ length: 5 }, (_, i) => ({
        name: `Product ${i}`,
        url: `https://example.com/product${i}`,
        price: "1.00",
      }));

      async function* mockParseFile() {
        for (const row of mockCsvRows) {
          yield row;
        }
      }
      vi.mocked(csvParser.parseFile).mockImplementation(mockParseFile);

      mockRepository.upsertBatch.mockResolvedValue({
        inserted: 2,
        updated: 0,
        failed: 0,
      });

      // Use batch size of 2
      await runImport({
        dataDir: "/data",
        batchSize: 2,
      });

      // Should be called 3 times: 2 full batches + 1 partial batch
      expect(mockRepository.upsertBatch).toHaveBeenCalledTimes(3);

      // First two calls should have 2 products each
      expect(mockRepository.upsertBatch.mock.calls[0][0]).toHaveLength(2);
      expect(mockRepository.upsertBatch.mock.calls[1][0]).toHaveLength(2);
      // Last call should have 1 product
      expect(mockRepository.upsertBatch.mock.calls[2][0]).toHaveLength(1);
    });

    it("should skip records with missing required fields", async () => {
      const mockFiles = [
        {
          filePath: "/data/coop-ch-products/2025/08/22-16:00.csv",
          supermarket: "coop",
          timestamp: new Date("2025-08-22T16:00:00"),
        },
      ];
      vi.mocked(fileScanner.scanDirectory).mockResolvedValue(mockFiles);

      const mockCsvRows = [
        {
          name: "Valid Product",
          url: "https://example.com/valid",
          price: "1.00",
        },
        {
          // Missing name
          url: "https://example.com/invalid1",
          price: "2.00",
        },
        {
          name: "Another Valid",
          url: "https://example.com/valid2",
          price: "3.00",
        },
        {
          name: "Missing URL",
          // Missing url
          price: "4.00",
        },
      ];

      async function* mockParseFile() {
        for (const row of mockCsvRows) {
          yield row as any;
        }
      }
      vi.mocked(csvParser.parseFile).mockImplementation(mockParseFile);

      mockRepository.upsertBatch.mockResolvedValue({
        inserted: 2,
        updated: 0,
        failed: 0,
      });

      const stats = await runImport({
        dataDir: "/data",
        batchSize: 10,
      });

      // Only 2 valid records should be processed
      expect(stats.totalRecords).toBe(2);
      expect(stats.failed).toBe(2); // 2 records skipped due to validation
    });

    it("should handle file processing errors gracefully", async () => {
      const mockFiles = [
        {
          filePath: "/data/coop-ch-products/2025/08/22-16:00.csv",
          supermarket: "coop",
          timestamp: new Date("2025-08-22T16:00:00"),
        },
        {
          filePath: "/data/lidl-ch-products/2025/08/01.csv",
          supermarket: "lidl",
          timestamp: new Date("2025-08-01T00:00:00"),
        },
      ];
      vi.mocked(fileScanner.scanDirectory).mockResolvedValue(mockFiles);

      // First file throws error, second file succeeds
      vi.mocked(csvParser.parseFile)
        .mockImplementationOnce(async function* () {
          throw new Error("File read error");
        })
        .mockImplementationOnce(async function* () {
          yield {
            name: "Valid Product",
            url: "https://example.com/valid",
            price: "1.00",
          };
        });

      mockRepository.upsertBatch.mockResolvedValue({
        inserted: 1,
        updated: 0,
        failed: 0,
      });

      const stats = await runImport({
        dataDir: "/data",
        batchSize: 10,
      });

      // Only 1 file should be processed successfully
      expect(stats.filesProcessed).toBe(1);
      expect(stats.totalRecords).toBe(1);
    });

    it("should handle empty file list", async () => {
      vi.mocked(fileScanner.scanDirectory).mockResolvedValue([]);

      const stats = await runImport({
        dataDir: "/data",
      });

      expect(stats.filesProcessed).toBe(0);
      expect(stats.totalRecords).toBe(0);
      expect(mockRepository.close).toHaveBeenCalled();
    });

    it("should track insert and update statistics separately", async () => {
      const mockFiles = [
        {
          filePath: "/data/coop-ch-products/2025/08/22-16:00.csv",
          supermarket: "coop",
          timestamp: new Date("2025-08-22T16:00:00"),
        },
      ];
      vi.mocked(fileScanner.scanDirectory).mockResolvedValue(mockFiles);

      async function* mockParseFile() {
        yield {
          name: "Product 1",
          url: "https://example.com/1",
          price: "1.00",
        };
        yield {
          name: "Product 2",
          url: "https://example.com/2",
          price: "2.00",
        };
      }
      vi.mocked(csvParser.parseFile).mockImplementation(mockParseFile);

      // Mock some inserts and some updates
      mockRepository.upsertBatch.mockResolvedValue({
        inserted: 1,
        updated: 1,
        failed: 0,
      });

      const stats = await runImport({
        dataDir: "/data",
        batchSize: 10,
      });

      expect(stats.inserted).toBe(1);
      expect(stats.updated).toBe(1);
      expect(stats.failed).toBe(0);
    });

    it("should always close database connection", async () => {
      vi.mocked(fileScanner.scanDirectory).mockRejectedValue(
        new Error("Scan failed")
      );

      await expect(
        runImport({
          dataDir: "/data",
        })
      ).rejects.toThrow("Scan failed");

      // Connection should still be closed
      expect(mockRepository.close).toHaveBeenCalled();
    });
  });
});
