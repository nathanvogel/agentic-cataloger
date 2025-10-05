import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { parseFile } from "./csv-parser";
import { writeFileSync, mkdirSync, rmSync } from "fs";
import { join } from "path";

describe("CSV Parser", () => {
  const testDir = join(__dirname, "../../test-data");
  const testFile = join(testDir, "test.csv");

  beforeEach(() => {
    mkdirSync(testDir, { recursive: true });
  });

  afterEach(() => {
    rmSync(testDir, { recursive: true, force: true });
  });

  it("should parse CSV file with store column", async () => {
    const csvContent = `store,name,url,price,unit,unit_price,price_text,has_discount,discount_info,image_url,scraped_from,category
Coop,Test Product,https://example.com/product,3.95,1kg,3.95,CHF 3.95,False,,https://example.com/image.jpg,https://example.com,Fruits`;

    writeFileSync(testFile, csvContent);

    const rows = [];
    for await (const row of parseFile(testFile, "coop")) {
      rows.push(row);
    }

    expect(rows).toHaveLength(1);
    expect(rows[0]).toEqual({
      store: "Coop",
      name: "Test Product",
      url: "https://example.com/product",
      price: "3.95",
      unit: "1kg",
      unit_price: "3.95",
      price_text: "CHF 3.95",
      has_discount: "False",
      discount_info: "",
      image_url: "https://example.com/image.jpg",
      scraped_from: "https://example.com",
      category: "Fruits",
    });
  });

  it("should parse CSV file without store column and use supermarket from path", async () => {
    const csvContent = `name,url,price,unit,unit_price,price_text,has_discount,discount_info,image_url,category
Bio Tofu,https://example.com/tofu,1.55,200g,0.78,1.55 CHF,False,,https://example.com/tofu.jpg,Vegan`;

    writeFileSync(testFile, csvContent);

    const rows = [];
    for await (const row of parseFile(testFile, "lidl")) {
      rows.push(row);
    }

    expect(rows).toHaveLength(1);
    expect(rows[0]).toEqual({
      store: "lidl",
      name: "Bio Tofu",
      url: "https://example.com/tofu",
      price: "1.55",
      unit: "200g",
      unit_price: "0.78",
      price_text: "1.55 CHF",
      has_discount: "False",
      discount_info: "",
      image_url: "https://example.com/tofu.jpg",
      scraped_from: undefined,
      category: "Vegan",
    });
  });

  it("should parse multiple rows", async () => {
    const csvContent = `name,url,price,unit
Product 1,https://example.com/1,1.99,100g
Product 2,https://example.com/2,2.99,200g
Product 3,https://example.com/3,3.99,300g`;

    writeFileSync(testFile, csvContent);

    const rows = [];
    for await (const row of parseFile(testFile, "migros")) {
      rows.push(row);
    }

    expect(rows).toHaveLength(3);
    expect(rows[0].name).toBe("Product 1");
    expect(rows[1].name).toBe("Product 2");
    expect(rows[2].name).toBe("Product 3");
    expect(rows[0].store).toBe("migros");
    expect(rows[1].store).toBe("migros");
    expect(rows[2].store).toBe("migros");
  });

  it("should handle empty optional fields", async () => {
    const csvContent = `name,url,price,unit,unit_price,price_text,has_discount,discount_info,image_url,category
Product,https://example.com,,,,,,,,`;

    writeFileSync(testFile, csvContent);

    const rows = [];
    for await (const row of parseFile(testFile, "denner")) {
      rows.push(row);
    }

    expect(rows).toHaveLength(1);
    expect(rows[0]).toEqual({
      store: "denner",
      name: "Product",
      url: "https://example.com",
      price: "",
      unit: "",
      unit_price: "",
      price_text: "",
      has_discount: "",
      discount_info: "",
      image_url: "",
      scraped_from: undefined,
      category: "",
    });
  });

  it("should handle CSV with quoted fields", async () => {
    const csvContent = `name,url,price,category
"Product, with comma","https://example.com",1.99,"Category, with comma"`;

    writeFileSync(testFile, csvContent);

    const rows = [];
    for await (const row of parseFile(testFile, "coop")) {
      rows.push(row);
    }

    expect(rows).toHaveLength(1);
    expect(rows[0].name).toBe("Product, with comma");
    expect(rows[0].category).toBe("Category, with comma");
  });

  it("should stream rows without loading entire file into memory", async () => {
    // Create a CSV with many rows
    const lines = ["name,url,price"];
    for (let i = 0; i < 1000; i++) {
      lines.push(`Product ${i},https://example.com/${i},${i}.99`);
    }
    writeFileSync(testFile, lines.join("\n"));

    let count = 0;
    for await (const row of parseFile(testFile, "coop")) {
      count++;
      expect(row.name).toBe(`Product ${count - 1}`);
      // Only check first few to avoid slow test
      if (count >= 10) break;
    }

    expect(count).toBe(10);
  });
});
