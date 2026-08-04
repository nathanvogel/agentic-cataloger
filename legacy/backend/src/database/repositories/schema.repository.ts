import { Injectable, Inject } from "@nestjs/common";
import { Pool } from "pg";
import * as db from "zapatos/db";
import type * as s from "zapatos/schema";
import { DATABASE_POOL } from "../database.constants";

export interface CreateSchemaInput {
  category_id: number;
  schema: Record<string, any>;
  version?: number;
}

export interface RegisterAttributeInput {
  name: string;
  display_name: string;
  type: "string" | "number" | "boolean" | "enum" | "array";
  enum_values?: string[];
  description?: string;
  unit?: string;
}

/**
 * Repository for managing category schemas and global attributes.
 * Handles schema storage, versioning, and attribute registry.
 * Requirements: 3.2, 3.3, 4.1, 4.2
 */
@Injectable()
export class SchemaRepository {
  constructor(@Inject(DATABASE_POOL) private pool: Pool) {}

  /**
   * Save a new schema for a category.
   * Automatically increments version if a schema already exists for the category.
   *
   * @param input - Schema creation data
   * @returns The created schema
   *
   * @example
   * ```typescript
   * const schema = await repository.saveSchema({
   *   category_id: 5,
   *   schema: {
   *     type: 'object',
   *     properties: {
   *       weight: { type: 'number', unit: 'g' }
   *     }
   *   }
   * });
   * ```
   */
  async saveSchema(
    input: CreateSchemaInput,
  ): Promise<s.category_schemas.JSONSelectable> {
    // Get the latest version for this category
    const latestVersion = await this.getLatestVersion(input.category_id);
    const newVersion = input.version || latestVersion + 1;

    const schema = await db
      .insert("category_schemas", {
        category_id: input.category_id,
        schema: input.schema,
        version: newVersion,
      })
      .run(this.pool);

    return schema;
  }

  /**
   * Get a schema by ID.
   *
   * @param schemaId - The schema ID
   * @returns Schema or null if not found
   */
  async getSchema(
    schemaId: number,
  ): Promise<s.category_schemas.JSONSelectable | null> {
    const results = await db
      .select("category_schemas", { id: schemaId })
      .run(this.pool);
    return results[0] || null;
  }

  /**
   * Get the latest schema for a category.
   *
   * @param categoryId - The category ID
   * @returns Latest schema or null if none exists
   */
  async getLatestSchemaForCategory(
    categoryId: number,
  ): Promise<s.category_schemas.JSONSelectable | null> {
    const results = await db
      .select(
        "category_schemas",
        { category_id: categoryId },
        {
          order: { by: "version", direction: "DESC" },
          limit: 1,
        },
      )
      .run(this.pool);
    return results[0] || null;
  }

  /**
   * Get all schemas for a category.
   *
   * @param categoryId - The category ID
   * @returns Array of schemas ordered by version
   */
  async getSchemasForCategory(
    categoryId: number,
  ): Promise<s.category_schemas.JSONSelectable[]> {
    return db
      .select(
        "category_schemas",
        { category_id: categoryId },
        { order: { by: "version", direction: "ASC" } },
      )
      .run(this.pool);
  }

  /**
   * Get the latest version number for a category.
   *
   * @param categoryId - The category ID
   * @returns Latest version number (0 if no schemas exist)
   */
  private async getLatestVersion(categoryId: number): Promise<number> {
    const latest = await this.getLatestSchemaForCategory(categoryId);
    return latest?.version || 0;
  }

  /**
   * Register a new global attribute or update usage count if it exists.
   *
   * @param input - Attribute registration data
   * @returns The created or updated attribute
   *
   * @example
   * ```typescript
   * const attr = await repository.registerAttribute({
   *   name: 'weight',
   *   display_name: 'Weight',
   *   type: 'number',
   *   unit: 'g',
   *   description: 'Product weight in grams'
   * });
   * ```
   */
  async registerAttribute(
    input: RegisterAttributeInput,
  ): Promise<s.global_attributes.JSONSelectable> {
    // Try to get existing attribute
    const existing = await this.getAttributeByName(input.name);

    if (existing) {
      // Increment usage count
      const updated = await db
        .update(
          "global_attributes",
          {
            usage_count: db.sql`${db.self} + 1`,
          },
          { id: existing.id },
        )
        .run(this.pool);
      return updated[0];
    }

    // Create new attribute
    const attribute = await db
      .insert("global_attributes", {
        name: input.name,
        display_name: input.display_name,
        type: input.type,
        enum_values: input.enum_values,
        description: input.description,
        unit: input.unit,
        usage_count: 1,
      })
      .run(this.pool);

    return attribute;
  }

  /**
   * Get an attribute by name.
   *
   * @param name - The attribute name
   * @returns Attribute or null if not found
   */
  async getAttributeByName(
    name: string,
  ): Promise<s.global_attributes.JSONSelectable | null> {
    const results = await db
      .select("global_attributes", { name })
      .run(this.pool);
    return results[0] || null;
  }

  /**
   * Get all global attributes.
   *
   * @returns Array of all attributes ordered by usage count
   */
  async getGlobalAttributes(): Promise<s.global_attributes.JSONSelectable[]> {
    return db
      .select("global_attributes", db.all, {
        order: { by: "usage_count", direction: "DESC" },
      })
      .run(this.pool);
  }

  /**
   * Get attributes by type.
   *
   * @param type - The attribute type
   * @returns Array of attributes of the specified type
   */
  async getAttributesByType(
    type: string,
  ): Promise<s.global_attributes.JSONSelectable[]> {
    return db
      .select(
        "global_attributes",
        { type },
        { order: { by: "usage_count", direction: "DESC" } },
      )
      .run(this.pool);
  }
}
