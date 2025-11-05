import { Injectable, Inject } from "@nestjs/common";
import { Pool } from "pg";
import * as db from "zapatos/db";
import type * as s from "zapatos/schema";
import { DATABASE_POOL } from "../database.module";

export interface CreateCategoryInput {
  name: string;
  display_name: string;
  reasoning?: string;
  confidence?: number;
}

/**
 * Repository for managing product categories.
 * Handles category creation, retrieval, and product assignment.
 * Requirements: 2.1, 2.2, 2.3, 2.4
 */
@Injectable()
export class CategoryRepository {
  constructor(@Inject(DATABASE_POOL) private pool: Pool) {}

  /**
   * Create a new category.
   *
   * @param input - Category creation data
   * @returns The created category
   *
   * @example
   * ```typescript
   * const category = await repository.createCategory({
   *   name: 'vegetables',
   *   display_name: 'Gemüse',
   *   reasoning: 'Products that are vegetables',
   *   confidence: 0.95
   * });
   * ```
   */
  async createCategory(
    input: CreateCategoryInput,
  ): Promise<s.categories.JSONSelectable> {
    const categories = await db
      .insert("categories", {
        name: input.name,
        display_name: input.display_name,
        reasoning: input.reasoning,
        confidence: input.confidence,
        product_count: 0,
      })
      .run(this.pool);
    return categories[0] as s.categories.JSONSelectable;
  }

  /**
   * Get a category by ID.
   *
   * @param categoryId - The category ID
   * @returns Category or null if not found
   */
  async getCategory(
    categoryId: number,
  ): Promise<s.categories.JSONSelectable | null> {
    const results = await db
      .select("categories", { id: categoryId })
      .run(this.pool);
    return results[0] || null;
  }

  /**
   * Get a category by name.
   *
   * @param name - The category name
   * @returns Category or null if not found
   */
  async getCategoryByName(
    name: string,
  ): Promise<s.categories.JSONSelectable | null> {
    const results = await db.select("categories", { name }).run(this.pool);
    return results[0] || null;
  }

  /**
   * Get all categories.
   *
   * @returns Array of all categories
   */
  async getAllCategories(): Promise<s.categories.JSONSelectable[]> {
    return db
      .select("categories", db.all, { order: { by: "name", direction: "ASC" } })
      .run(this.pool);
  }

  /**
   * Assign products to a category.
   * Updates product_count and assigns category_id to products in a transaction.
   *
   * @param categoryId - The category ID
   * @param productIds - Array of product IDs to assign
   * @param confidence - Confidence score for the assignment
   *
   * @example
   * ```typescript
   * await repository.assignProducts(5, [101, 102, 103], 0.92);
   * ```
   */
  async assignProducts(
    categoryId: number,
    productIds: number[],
    confidence: number = 1.0,
  ): Promise<void> {
    const client = await this.pool.connect();
    try {
      await client.query("BEGIN");

      // Update products with category assignment
      await db
        .update(
          "products",
          {
            category_id: categoryId,
            categorization_confidence: confidence,
          },
          { id: db.sql`${db.self} = ANY(${db.param(productIds)})` },
        )
        .run(client);

      // Update category product count
      await db
        .update(
          "categories",
          {
            product_count: db.sql`(
            SELECT COUNT(*) 
            FROM products 
            WHERE category_id = ${db.param(categoryId)}
          )`,
          },
          { id: categoryId },
        )
        .run(client);

      await client.query("COMMIT");
    } catch (error) {
      await client.query("ROLLBACK");
      throw error;
    } finally {
      client.release();
    }
  }

  /**
   * Update category schema reference.
   * Links a category to its schema definition.
   *
   * @param categoryId - The category ID
   * @param schemaId - The schema ID to link
   */
  async updateCategorySchema(
    categoryId: number,
    schemaId: number,
  ): Promise<void> {
    await db
      .update("categories", { schema_id: schemaId }, { id: categoryId })
      .run(this.pool);
  }

  /**
   * Update category product count.
   * Recalculates the product count for a category.
   *
   * @param categoryId - The category ID
   */
  async updateProductCount(categoryId: number): Promise<void> {
    await db
      .update(
        "categories",
        {
          product_count: db.sql`(
          SELECT COUNT(*) 
          FROM products 
          WHERE category_id = ${db.param(categoryId)}
        )`,
        },
        { id: categoryId },
      )
      .run(this.pool);
  }
}
