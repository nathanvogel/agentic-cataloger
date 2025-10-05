import { Injectable } from '@nestjs/common';
import { pool } from '../database/db';

@Injectable()
export class ProductsService {
  async search(query: string, filters?: { bio?: boolean; supermarket?: string }) {
    let sql = `
      SELECT id, name, supermarket, price, unit_price, is_discounted, 
             categories, attributes, product_url, image_url
      FROM products
      WHERE to_tsvector('german', name) @@ plainto_tsquery('german', $1)
    `;
    const params: any[] = [query];
    let paramCount = 1;

    if (filters?.bio) {
      sql += ` AND (name ILIKE '%bio%' OR attributes->>'bio' = 'true')`;
    }

    if (filters?.supermarket) {
      paramCount++;
      sql += ` AND supermarket = $${paramCount}`;
      params.push(filters.supermarket);
    }

    sql += ` ORDER BY price NULLS LAST LIMIT 100`;

    const result = await pool.query(sql, params);
    return result.rows;
  }

  async getCheapest(productName: string, filters?: { bio?: boolean }) {
    let sql = `
      SELECT id, name, supermarket, price, unit_price, is_discounted,
             categories, attributes, product_url, image_url
      FROM products
      WHERE name ILIKE $1 AND price IS NOT NULL
    `;
    const params: any[] = [`%${productName}%`];

    if (filters?.bio) {
      sql += ` AND (name ILIKE '%bio%' OR attributes->>'bio' = 'true')`;
    }

    sql += ` ORDER BY price LIMIT 20`;

    const result = await pool.query(sql, params);
    return result.rows;
  }

  async compareByCategory(category: string) {
    const sql = `
      SELECT supermarket, 
             COUNT(*) as product_count,
             AVG(price) as avg_price,
             MIN(price) as min_price
      FROM products
      WHERE $1 = ANY(categories) AND price IS NOT NULL
      GROUP BY supermarket
      ORDER BY avg_price
    `;
    const result = await pool.query(sql, [category]);
    return result.rows;
  }
}
