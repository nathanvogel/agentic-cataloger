import * as fs from 'fs';
import * as path from 'path';
import { parse } from 'csv-parse/sync';
import { pool } from '../src/database/db';

interface ProductRow {
  name: string;
  price?: string;
  price_text?: string;
  unit?: string;
  unit_price?: string;
  is_discounted?: string;
  discount_info?: string;
  category?: string;
  image_url?: string;
  product_url?: string;
}

const SUPERMARKETS = ['migros', 'lidl', 'coop', 'denner'];

async function getLatestCSV(supermarket: string): Promise<string | null> {
  const dataDir = path.join(__dirname, '../../data', `${supermarket}-ch-products`);
  
  if (!fs.existsSync(dataDir)) {
    console.log(`⚠️  Directory not found: ${dataDir}`);
    return null;
  }

  const years = fs.readdirSync(dataDir).filter(f => f.match(/^\d{4}$/));
  if (years.length === 0) return null;

  const latestYear = years.sort().reverse()[0];
  const yearPath = path.join(dataDir, latestYear);
  
  const months = fs.readdirSync(yearPath).filter(f => f.match(/^\d{2}$/));
  if (months.length === 0) return null;

  const latestMonth = months.sort().reverse()[0];
  const monthPath = path.join(yearPath, latestMonth);
  
  const files = fs.readdirSync(monthPath).filter(f => f.endsWith('.csv'));
  if (files.length === 0) return null;

  const latestFile = files.sort().reverse()[0];
  return path.join(monthPath, latestFile);
}

function parsePrice(priceStr?: string): number | null {
  if (!priceStr) return null;
  const cleaned = priceStr.replace(/[^\d.,]/g, '').replace(',', '.');
  const parsed = parseFloat(cleaned);
  return isNaN(parsed) ? null : parsed;
}

function extractCategories(categoryStr?: string): string[] {
  if (!categoryStr) return [];
  return categoryStr.split(/[,;]/).map(c => c.trim()).filter(Boolean);
}

function extractAttributes(name: string): Record<string, boolean> {
  const attrs: Record<string, boolean> = {};
  const lowerName = name.toLowerCase();
  
  if (lowerName.includes('bio')) attrs.bio = true;
  if (lowerName.includes('vegan')) attrs.vegan = true;
  if (lowerName.includes('glutenfrei')) attrs.glutenfrei = true;
  if (lowerName.includes('laktosefrei')) attrs.laktosefrei = true;
  
  return attrs;
}

async function importSupermarket(supermarket: string) {
  const csvPath = await getLatestCSV(supermarket);
  
  if (!csvPath) {
    console.log(`⚠️  No CSV found for ${supermarket}`);
    return 0;
  }

  console.log(`📂 Reading ${supermarket}: ${csvPath}`);
  
  const content = fs.readFileSync(csvPath, 'utf-8');
  const records: ProductRow[] = parse(content, {
    columns: true,
    skip_empty_lines: true,
  });

  console.log(`   Found ${records.length} products`);

  let imported = 0;
  for (const record of records) {
    try {
      const price = parsePrice(record.price);
      const categories = extractCategories(record.category);
      const attributes = extractAttributes(record.name);

      await pool.query(
        `INSERT INTO products 
         (name, price, price_text, unit, unit_price, is_discounted, 
          discount_info, supermarket, categories, attributes, image_url, product_url)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)`,
        [
          record.name,
          price,
          record.price_text,
          record.unit,
          record.unit_price,
          record.is_discounted === 'true' || record.is_discounted === '1',
          record.discount_info,
          supermarket,
          categories,
          JSON.stringify(attributes),
          record.image_url,
          record.product_url,
        ]
      );
      imported++;
    } catch (err) {
      console.error(`   Error importing product: ${record.name}`, err);
    }
  }

  console.log(`✅ Imported ${imported} products from ${supermarket}`);
  return imported;
}

async function main() {
  console.log('🚀 Starting data import...\n');

  // Clear existing data
  await pool.query('TRUNCATE products CASCADE');
  console.log('🗑️  Cleared existing data\n');

  let totalImported = 0;
  for (const supermarket of SUPERMARKETS) {
    const count = await importSupermarket(supermarket);
    totalImported += count;
  }

  // Refresh materialized view
  await pool.query('REFRESH MATERIALIZED VIEW category_price_stats');
  console.log('\n🔄 Refreshed materialized views');

  console.log(`\n✨ Import complete! Total products: ${totalImported}`);
  
  await pool.end();
}

main().catch(err => {
  console.error('❌ Import failed:', err);
  process.exit(1);
});
