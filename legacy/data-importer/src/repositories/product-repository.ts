import { Pool } from "pg";
import type { Product } from "../transformers/product-transformer";
import { error as logError, info } from "../utils/logger";

/**
 * Result of an upsert batch operation
 */
export interface UpsertResult {
  inserted: number;
  updated: number;
  failed: number;
}

/**
 * Repository for managing product data in PostgreSQL database.
 * Handles batch upsert operations with transaction support.
 */
export class ProductRepository {
  constructor(private pool: Pool) {}

  /**
   * Upserts a batch of products into the database.
   * Uses INSERT ... ON CONFLICT to handle duplicates based on (name, supermarket, product_url).
   * All operations are wrapped in a transaction for atomicity.
   *
   * @param products - Array of products to upsert
   * @returns Result containing counts of inserted, updated, and failed records
   *
   * @example
   * ```typescript
   * const repository = new ProductRepository(pool);
   * const products = [product1, product2];
   * const result = await repository.upsertBatch(products);
   * console.log(`Inserted: ${result.inserted}, Updated: ${result.updated}`);
   * ```
   */
  async upsertBatch(products: Product[]): Promise<UpsertResult> {
    if (products.length === 0) {
      return { inserted: 0, updated: 0, failed: 0 };
    }

    const client = await this.pool.connect();

    try {
      await client.query("BEGIN");

      let inserted = 0;
      let updated = 0;
      let failed = 0;

      for (const product of products) {
        try {
          const query = `
            INSERT INTO products (
              name,
              price,
              price_text,
              currency,
              unit,
              unit_price,
              original_quantity,
              original_unit,
              normalized_quantity,
              normalized_unit,
              normalized_price,
              is_discounted,
              discount_info,
              supermarket,
              categories,
              attributes,
              image_url,
              product_url,
              scraped_at
            ) VALUES (
              $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
              $11, $12, $13, $14, $15, $16, $17, $18, $19
            )
            ON CONFLICT (name, supermarket, product_url)
            DO UPDATE SET
              price = EXCLUDED.price,
              price_text = EXCLUDED.price_text,
              currency = EXCLUDED.currency,
              unit = EXCLUDED.unit,
              unit_price = EXCLUDED.unit_price,
              original_quantity = EXCLUDED.original_quantity,
              original_unit = EXCLUDED.original_unit,
              normalized_quantity = EXCLUDED.normalized_quantity,
              normalized_unit = EXCLUDED.normalized_unit,
              normalized_price = EXCLUDED.normalized_price,
              is_discounted = EXCLUDED.is_discounted,
              discount_info = EXCLUDED.discount_info,
              categories = EXCLUDED.categories,
              attributes = EXCLUDED.attributes,
              image_url = EXCLUDED.image_url,
              scraped_at = EXCLUDED.scraped_at
            RETURNING (xmax = 0) AS inserted
          `;

          const values = [
            product.name,
            product.price,
            product.price_text,
            product.currency,
            product.unit,
            product.unit_price,
            product.original_quantity,
            product.original_unit,
            product.normalized_quantity,
            product.normalized_unit,
            product.normalized_price,
            product.is_discounted,
            product.discount_info,
            product.supermarket,
            product.categories,
            JSON.stringify(product.attributes),
            product.image_url,
            product.product_url,
            product.scraped_at,
          ];

          const result = await client.query(query, values);

          // Check if it was an insert or update
          // xmax = 0 means it was an INSERT, xmax > 0 means it was an UPDATE
          if (result.rows[0]?.inserted) {
            inserted++;
          } else {
            updated++;
          }
        } catch (err) {
          failed++;
          logError(
            `Failed to upsert product "${product.name}": ${
              err instanceof Error ? err.message : String(err)
            }`
          );
        }
      }

      await client.query("COMMIT");

      info(
        `Batch upsert complete: ${inserted} inserted, ${updated} updated, ${failed} failed`
      );

      return { inserted, updated, failed };
    } catch (err) {
      await client.query("ROLLBACK");
      logError(
        `Transaction failed: ${
          err instanceof Error ? err.message : String(err)
        }`
      );
      return { inserted: 0, updated: 0, failed: products.length };
    } finally {
      client.release();
    }
  }

  /**
   * Closes the database connection pool.
   * Should be called when the application is shutting down.
   */
  async close(): Promise<void> {
    await this.pool.end();
  }
}
