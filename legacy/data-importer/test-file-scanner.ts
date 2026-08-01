import { scanDirectory } from "./src/parsers/file-scanner";

async function test() {
  console.log("Scanning data directory...\n");

  const files = await scanDirectory("../../../data");

  console.log(`Found ${files.length} CSV files\n`);

  // Group by supermarket
  const bySupermarket = files.reduce((acc, file) => {
    if (!acc[file.supermarket]) {
      acc[file.supermarket] = [];
    }
    acc[file.supermarket].push(file);
    return acc;
  }, {} as Record<string, typeof files>);

  for (const [supermarket, fileList] of Object.entries(bySupermarket)) {
    console.log(`${supermarket}: ${fileList.length} files`);
  }

  console.log("\nSample files:");
  files.slice(0, 3).forEach((file) => {
    console.log(`  - ${file.filePath}`);
    console.log(`    Supermarket: ${file.supermarket}`);
    console.log(`    Timestamp: ${file.timestamp?.toISOString() || "N/A"}`);
  });
}

test().catch(console.error);
