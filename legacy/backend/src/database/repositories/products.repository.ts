import { Injectable, Inject } from "@nestjs/common";
import { Pool } from "pg";
import * as db from "zapatos/db";
import type * as s from "zapatos/schema";
import { DATABASE_POOL } from "../database.constants";

/**
 * Repository for managing product data with categorization support.
 * Handles product queries, category assignments, and attribute updates.
 * Requirements: 1.1, 5.2, 7.1, 10.2
 */
@Injectable()
export class ProductsRepository {
  constructor(@Inject(DATABASE_POOL) private pool: Pool) {}

  /**
   * Get products by multiple categories (OR condition).
   * Filters products that have any of the specified categories in their categories array.
   *
   * @param categories - Array of category names to filter by (e.g., ["Gemüse", "Früchte"])
   * @returns Array of products matching any of the categories
   *
   * @example
   * ```typescript
   * const products = await repository.getProductsByCategories(['Gemüse', 'Früchte']);
   * ```
   */
  async getProductsByCategories(categories: string[]) {
    return db
      .select(
        "products",
        { categories: db.sql`${db.self} && ${db.param(categories)}` },
        {
          columns: [
            "id",
            "name",
            "categories",
            "attributes",
            "category_id",
            "supermarket",
            "unit",
            "price",
          ],
        },
      )
      .run(this.pool);
  }

  /**
   * Get all products assigned to a specific discovered category.
   *
   * @param categoryId - The category ID to filter by
   * @returns Array of products in the specified category, ordered by name
   */
  async getProductsByCategory(categoryId: number) {
    return db
      .select(
        "products",
        { category_id: categoryId },
        {
          columns: [
            "id",
            "name",
            "price",
            "price_text",
            "currency",
            "unit",
            "unit_price",
            "original_quantity",
            "original_unit",
            "normalized_quantity",
            "normalized_unit",
            "normalized_price",
            "is_discounted",
            "discount_info",
            "supermarket",
            "categories",
            "attributes",
            "image_url",
            "product_url",
            "scraped_at",
            "category_id",
            "categorization_confidence",
            "attributes_extracted_at",
          ],
          order: { by: "name", direction: "ASC" },
        },
      )
      .run(this.pool);
  }

  /**
   * Assign a category to a product with confidence score.
   * Updates the category_id and categorization_confidence fields.
   *
   * @param productId - The product ID to update
   * @param categoryId - The category ID to assign
   * @param confidence - Confidence score (0.00 to 1.00)
   */
  async updateProductCategory(
    productId: number,
    categoryId: number,
    confidence: number,
  ): Promise<void> {
    await db
      .update(
        "products",
        {
          category_id: categoryId,
          categorization_confidence: confidence,
        },
        { id: productId },
      )
      .run(this.pool);
  }

  /**
   * Update product attributes in the JSONB column.
   * Merges new attributes with existing ones.
   *
   * @param productId - The product ID to update
   * @param attributes - Attributes object to store
   */
  async updateProductAttributes(
    productId: number,
    attributes: Record<string, any>,
  ): Promise<void> {
    await db
      .update(
        "products",
        {
          attributes: db.sql`${db.self} || ${db.param(attributes)}::jsonb`,
          attributes_extracted_at: new Date(),
        },
        { id: productId },
      )
      .run(this.pool);
  }

  /**
   * Get a single product by ID.
   *
   * @param productId - The product ID
   * @returns Product or null if not found
   */
  async getProductById(
    productId: number,
  ): Promise<s.products.JSONSelectable | null> {
    const results = await db
      .select("products", { id: productId })
      .run(this.pool);
    return results[0] || null;
  }

  /**
   * Get products without a category assignment.
   * Useful for finding products that need categorization.
   *
   * @param limit - Maximum number of products to return
   * @returns Array of uncategorized products
   */
  async getUncategorizedProducts(limit: number = 100) {
    return db
      .select(
        "products",
        { category_id: db.conditions.isNull },
        {
          columns: [
            "id",
            "name",
            "categories",
            "attributes",
            "supermarket",
            "category_id",
          ],
          limit,
        },
      )
      .run(this.pool);
  }
}
