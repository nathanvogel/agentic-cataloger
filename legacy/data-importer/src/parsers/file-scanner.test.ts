import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { scanDirectory } from "./file-scanner";
import * as fs from "fs/promises";
import * as path from "path";

// Mock fs/promises
vi.mock("fs/promises");

describe("file-scanner", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("scanDirectory", () => {
    it("should find CSV files recursively", async () => {
      // Mock directory structure
      const mockReaddir = vi.mocked(fs.readdir);

      // Root directory
      mockReaddir.mockResolvedValueOnce([
        {
          name: "coop-ch-products",
          isDirectory: () => true,
          isFile: () => false,
        } as any,
      ]);

      // coop-ch-products directory
      mockReaddir.mockResolvedValueOnce([
        { name: "2025", isDirectory: () => true, isFile: () => false } as any,
      ]);

      // 2025 directory
      mockReaddir.mockResolvedValueOnce([
        { name: "08", isDirectory: () => true, isFile: () => false } as any,
      ]);

      // 08 directory
      mockReaddir.mockResolvedValueOnce([
        {
          name: "22-16:00.csv",
          isDirectory: () => false,
          isFile: () => true,
        } as any,
        {
          name: "23-10:59.csv",
          isDirectory: () => false,
          isFile: () => true,
        } as any,
      ]);

      const results = await scanDirectory("data");

      expect(results).toHaveLength(2);
      expect(results[0]).toMatchObject({
        filePath: path.join(
          "data",
          "coop-ch-products",
          "2025",
          "08",
          "22-16:00.csv"
        ),
        supermarket: "coop",
      });
      expect(results[1]).toMatchObject({
        filePath: path.join(
          "data",
          "coop-ch-products",
          "2025",
          "08",
          "23-10:59.csv"
        ),
        supermarket: "coop",
      });
    });

    it("should extract supermarket name from directory path", async () => {
      const mockReaddir = vi.mocked(fs.readdir);

      // Root directory with multiple supermarkets
      mockReaddir.mockResolvedValueOnce([
        {
          name: "coop-ch-products",
          isDirectory: () => true,
          isFile: () => false,
        } as any,
        {
          name: "lidl-ch-products",
          isDirectory: () => true,
          isFile: () => false,
        } as any,
      ]);

      // coop-ch-products
      mockReaddir.mockResolvedValueOnce([
        {
          name: "test.csv",
          isDirectory: () => false,
          isFile: () => true,
        } as any,
      ]);

      // lidl-ch-products
      mockReaddir.mockResolvedValueOnce([
        {
          name: "test.csv",
          isDirectory: () => false,
          isFile: () => true,
        } as any,
      ]);

      const results = await scanDirectory("data");

      expect(results).toHaveLength(2);
      expect(results[0].supermarket).toBe("coop");
      expect(results[1].supermarket).toBe("lidl");
    });

    it("should extract timestamp from filename", async () => {
      const mockReaddir = vi.mocked(fs.readdir);

      mockReaddir.mockResolvedValueOnce([
        {
          name: "coop-ch-products",
          isDirectory: () => true,
          isFile: () => false,
        } as any,
      ]);

      mockReaddir.mockResolvedValueOnce([
        { name: "2025", isDirectory: () => true, isFile: () => false } as any,
      ]);

      mockReaddir.mockResolvedValueOnce([
        { name: "08", isDirectory: () => true, isFile: () => false } as any,
      ]);

      mockReaddir.mockResolvedValueOnce([
        {
          name: "22-16:00.csv",
          isDirectory: () => false,
          isFile: () => true,
        } as any,
      ]);

      const results = await scanDirectory("data");

      expect(results).toHaveLength(1);
      expect(results[0].timestamp).toBeInstanceOf(Date);
      expect(results[0].timestamp?.getFullYear()).toBe(2025);
      expect(results[0].timestamp?.getMonth()).toBe(7); // August (0-indexed)
      expect(results[0].timestamp?.getDate()).toBe(22);
      expect(results[0].timestamp?.getHours()).toBe(16);
      expect(results[0].timestamp?.getMinutes()).toBe(0);
    });

    it("should handle files without timestamp in filename", async () => {
      const mockReaddir = vi.mocked(fs.readdir);

      mockReaddir.mockResolvedValueOnce([
        {
          name: "coop-ch-products",
          isDirectory: () => true,
          isFile: () => false,
        } as any,
      ]);

      mockReaddir.mockResolvedValueOnce([
        {
          name: "products.csv",
          isDirectory: () => false,
          isFile: () => true,
        } as any,
      ]);

      const results = await scanDirectory("data");

      expect(results).toHaveLength(1);
      expect(results[0].timestamp).toBeUndefined();
    });

    it("should filter by supermarket when specified", async () => {
      const mockReaddir = vi.mocked(fs.readdir);

      mockReaddir.mockResolvedValueOnce([
        {
          name: "coop-ch-products",
          isDirectory: () => true,
          isFile: () => false,
        } as any,
        {
          name: "lidl-ch-products",
          isDirectory: () => true,
          isFile: () => false,
        } as any,
      ]);

      mockReaddir.mockResolvedValueOnce([
        {
          name: "test.csv",
          isDirectory: () => false,
          isFile: () => true,
        } as any,
      ]);

      mockReaddir.mockResolvedValueOnce([
        {
          name: "test.csv",
          isDirectory: () => false,
          isFile: () => true,
        } as any,
      ]);

      const results = await scanDirectory("data", "coop");

      expect(results).toHaveLength(1);
      expect(results[0].supermarket).toBe("coop");
    });

    it("should skip non-CSV files", async () => {
      const mockReaddir = vi.mocked(fs.readdir);

      mockReaddir.mockResolvedValueOnce([
        {
          name: "coop-ch-products",
          isDirectory: () => true,
          isFile: () => false,
        } as any,
      ]);

      mockReaddir.mockResolvedValueOnce([
        {
          name: "test.csv",
          isDirectory: () => false,
          isFile: () => true,
        } as any,
        {
          name: "test.txt",
          isDirectory: () => false,
          isFile: () => true,
        } as any,
        {
          name: "README.md",
          isDirectory: () => false,
          isFile: () => true,
        } as any,
        {
          name: ".gitattributes",
          isDirectory: () => false,
          isFile: () => true,
        } as any,
      ]);

      const results = await scanDirectory("data");

      expect(results).toHaveLength(1);
      expect(results[0].filePath).toContain("test.csv");
    });

    it("should handle empty directories", async () => {
      const mockReaddir = vi.mocked(fs.readdir);

      mockReaddir.mockResolvedValueOnce([
        { name: "coop-ch-products", isDirectory: () => true } as any,
      ]);

      mockReaddir.mockResolvedValueOnce([]);

      const results = await scanDirectory("data");

      expect(results).toHaveLength(0);
    });

    it("should handle nested directory structures", async () => {
      const mockReaddir = vi.mocked(fs.readdir);

      mockReaddir.mockResolvedValueOnce([
        {
          name: "denner-ch-products",
          isDirectory: () => true,
          isFile: () => false,
        } as any,
      ]);

      mockReaddir.mockResolvedValueOnce([
        { name: "2025", isDirectory: () => true, isFile: () => false } as any,
      ]);

      mockReaddir.mockResolvedValueOnce([
        { name: "08", isDirectory: () => true, isFile: () => false } as any,
        { name: "09", isDirectory: () => true, isFile: () => false } as any,
      ]);

      mockReaddir.mockResolvedValueOnce([
        {
          name: "13-22:57.csv",
          isDirectory: () => false,
          isFile: () => true,
        } as any,
      ]);

      mockReaddir.mockResolvedValueOnce([
        {
          name: "01-22:28.csv",
          isDirectory: () => false,
          isFile: () => true,
        } as any,
      ]);

      const results = await scanDirectory("data");

      expect(results).toHaveLength(2);
      expect(results[0].filePath).toContain(
        path.join("2025", "08", "13-22:57.csv")
      );
      expect(results[1].filePath).toContain(
        path.join("2025", "09", "01-22:28.csv")
      );
    });

    it("should extract all supported supermarkets", async () => {
      const mockReaddir = vi.mocked(fs.readdir);

      mockReaddir.mockResolvedValueOnce([
        {
          name: "coop-ch-products",
          isDirectory: () => true,
          isFile: () => false,
        } as any,
        {
          name: "denner-ch-products",
          isDirectory: () => true,
          isFile: () => false,
        } as any,
        {
          name: "lidl-ch-products",
          isDirectory: () => true,
          isFile: () => false,
        } as any,
        {
          name: "migros-ch-products",
          isDirectory: () => true,
          isFile: () => false,
        } as any,
      ]);

      mockReaddir.mockResolvedValueOnce([
        {
          name: "test.csv",
          isDirectory: () => false,
          isFile: () => true,
        } as any,
      ]);
      mockReaddir.mockResolvedValueOnce([
        {
          name: "test.csv",
          isDirectory: () => false,
          isFile: () => true,
        } as any,
      ]);
      mockReaddir.mockResolvedValueOnce([
        {
          name: "test.csv",
          isDirectory: () => false,
          isFile: () => true,
        } as any,
      ]);
      mockReaddir.mockResolvedValueOnce([
        {
          name: "test.csv",
          isDirectory: () => false,
          isFile: () => true,
        } as any,
      ]);

      const results = await scanDirectory("data");

      expect(results).toHaveLength(4);
      expect(results.map((r) => r.supermarket).sort()).toEqual([
        "coop",
        "denner",
        "lidl",
        "migros",
      ]);
    });
  });
});
