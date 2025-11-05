import { Injectable, Inject } from "@nestjs/common";
import { Pool } from "pg";
import * as db from "zapatos/db";
import type * as s from "zapatos/schema";
import { DATABASE_POOL } from "../database.module";

export type AgentPhase =
  | "CATEGORY_DISCOVERY"
  | "SCHEMA_GENERATION"
  | "ATTRIBUTE_EXTRACTION";
export type AgentStatus = "success" | "error" | "partial";

export interface CreateExecutionInput {
  phase: AgentPhase;
  status: AgentStatus;
  llm_input: Record<string, any>;
  llm_output: Record<string, any>;
  product_ids?: number[];
  category_ids?: number[];
  schema_ids?: number[];
  error_message?: string;
  tokens_used?: number;
  duration_ms?: number;
  llm_model: string;
  llm_provider: string;
}

export interface MarkReviewedInput {
  is_correct: boolean;
  reviewer_notes?: string;
}

export interface ExecutionQueryFilters {
  phase?: AgentPhase;
  status?: AgentStatus;
  llm_model?: string;
  is_reviewed?: boolean;
  product_id?: number;
  category_id?: number;
  schema_id?: number;
}

export interface AccuracyStats {
  model: string;
  total_executions: number;
  reviewed_executions: number;
  correct_executions: number;
  accuracy_rate: number;
}

/**
 * Repository for logging and managing LLM agent executions.
 * Tracks all agent interactions for review, debugging, and quality assurance.
 * Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 15.3
 */
@Injectable()
export class AgentExecutionRepository {
  constructor(@Inject(DATABASE_POOL) private pool: Pool) {}

  /**
   * Log a new agent execution.
   *
   * @param input - Execution log data
   * @returns The created execution log
   *
   * @example
   * ```typescript
   * const execution = await repository.logExecution({
   *   phase: 'CATEGORY_DISCOVERY',
   *   status: 'success',
   *   llm_input: { prompt: '...', products: [...] },
   *   llm_output: { categories: [...] },
   *   product_ids: [1, 2, 3],
   *   category_ids: [5],
   *   tokens_used: 1500,
   *   duration_ms: 2300,
   *   llm_model: 'gpt-4',
   *   llm_provider: 'openai'
   * });
   * ```
   */
  async logExecution(
    input: CreateExecutionInput,
  ): Promise<s.agent_executions.JSONSelectable> {
    const execution = await db
      .insert("agent_executions", {
        phase: input.phase,
        status: input.status,
        llm_input: input.llm_input,
        llm_output: input.llm_output,
        product_ids: input.product_ids || [],
        category_ids: input.category_ids || [],
        schema_ids: input.schema_ids || [],
        error_message: input.error_message,
        tokens_used: input.tokens_used,
        duration_ms: input.duration_ms,
        llm_model: input.llm_model,
        llm_provider: input.llm_provider,
        completed_at: new Date(),
      })
      .run(this.pool);

    return execution;
  }

  /**
   * Mark an execution as reviewed with correctness assessment.
   *
   * @param executionId - The execution ID
   * @param review - Review data
   *
   * @example
   * ```typescript
   * await repository.markAsReviewed(123, {
   *   is_correct: true,
   *   reviewer_notes: 'Categories look accurate'
   * });
   * ```
   */
  async markAsReviewed(
    executionId: number,
    review: MarkReviewedInput,
  ): Promise<void> {
    await db
      .update(
        "agent_executions",
        {
          is_reviewed: true,
          is_correct: review.is_correct,
          reviewer_notes: review.reviewer_notes,
          reviewed_at: new Date(),
        },
        { id: executionId },
      )
      .run(this.pool);
  }

  /**
   * Get execution by ID.
   *
   * @param executionId - The execution ID
   * @returns Execution or null if not found
   */
  async getExecution(
    executionId: number,
  ): Promise<s.agent_executions.JSONSelectable | null> {
    const results = await db
      .select("agent_executions", { id: executionId })
      .run(this.pool);
    return results[0] || null;
  }

  /**
   * Query executions with filters.
   *
   * @param filters - Query filters
   * @param limit - Maximum number of results
   * @returns Array of executions matching the filters
   *
   * @example
   * ```typescript
   * // Get all successful category discoveries
   * const executions = await repository.queryExecutions({
   *   phase: 'CATEGORY_DISCOVERY',
   *   status: 'success'
   * }, 50);
   *
   * // Get executions for a specific product
   * const productExecutions = await repository.queryExecutions({
   *   product_id: 123
   * });
   * ```
   */
  async queryExecutions(
    filters: ExecutionQueryFilters,
    limit: number = 100,
  ): Promise<s.agent_executions.JSONSelectable[]> {
    const whereConditions: Partial<s.agent_executions.Whereable> = {};

    if (filters.phase !== undefined) {
      whereConditions.phase = filters.phase;
    }
    if (filters.status !== undefined) {
      whereConditions.status = filters.status;
    }
    if (filters.llm_model !== undefined) {
      whereConditions.llm_model = filters.llm_model;
    }
    if (filters.is_reviewed !== undefined) {
      whereConditions.is_reviewed = filters.is_reviewed;
    }
    if (filters.product_id !== undefined) {
      (whereConditions as Record<string, unknown>).product_ids =
        db.sql`${db.self} && ARRAY[${db.param(filters.product_id)}]::integer[]`;
    }
    if (filters.category_id !== undefined) {
      (whereConditions as Record<string, unknown>).category_ids =
        db.sql`${db.self} && ARRAY[${db.param(filters.category_id)}]::integer[]`;
    }
    if (filters.schema_id !== undefined) {
      (whereConditions as Record<string, unknown>).schema_ids =
        db.sql`${db.self} && ARRAY[${db.param(filters.schema_id)}]::integer[]`;
    }

    return db
      .select(
        "agent_executions",
        whereConditions as s.agent_executions.Whereable,
        {
          order: { by: "created_at", direction: "DESC" },
          limit,
        },
      )
      .run(this.pool);
  }

  /**
   * Get executions by phase.
   *
   * @param phase - The agent phase
   * @param limit - Maximum number of results
   * @returns Array of executions for the phase
   */
  async getExecutionsByPhase(
    phase: AgentPhase,
    limit: number = 100,
  ): Promise<s.agent_executions.JSONSelectable[]> {
    return this.queryExecutions({ phase }, limit);
  }

  /**
   * Get executions by status.
   *
   * @param status - The execution status
   * @param limit - Maximum number of results
   * @returns Array of executions with the status
   */
  async getExecutionsByStatus(
    status: AgentStatus,
    limit: number = 100,
  ): Promise<s.agent_executions.JSONSelectable[]> {
    return this.queryExecutions({ status }, limit);
  }

  /**
   * Get executions by model.
   *
   * @param model - The LLM model name
   * @param limit - Maximum number of results
   * @returns Array of executions using the model
   */
  async getExecutionsByModel(
    model: string,
    limit: number = 100,
  ): Promise<s.agent_executions.JSONSelectable[]> {
    return this.queryExecutions({ llm_model: model }, limit);
  }

  /**
   * Get unreviewed executions.
   *
   * @param limit - Maximum number of results
   * @returns Array of unreviewed executions
   */
  async getUnreviewedExecutions(
    limit: number = 100,
  ): Promise<s.agent_executions.JSONSelectable[]> {
    return this.queryExecutions({ is_reviewed: false }, limit);
  }

  /**
   * Calculate accuracy statistics per model.
   * Returns accuracy rates based on human review data.
   *
   * @returns Array of accuracy statistics per model
   *
   * @example
   * ```typescript
   * const stats = await repository.getAccuracyStatsByModel();
   * // [
   * //   {
   * //     model: 'gpt-4',
   * //     total_executions: 100,
   * //     reviewed_executions: 50,
   * //     correct_executions: 48,
   * //     accuracy_rate: 0.96
   * //   }
   * // ]
   * ```
   */
  async getAccuracyStatsByModel(): Promise<AccuracyStats[]> {
    const result = await db.sql<
      s.agent_executions.SQL,
      { model: string; total: string; reviewed: string; correct: string }[]
    >`
      SELECT 
        llm_model as model,
        COUNT(*)::text as total,
        COUNT(*) FILTER (WHERE is_reviewed = true)::text as reviewed,
        COUNT(*) FILTER (WHERE is_reviewed = true AND is_correct = true)::text as correct
      FROM ${"agent_executions"}
      GROUP BY llm_model
      ORDER BY COUNT(*) DESC
    `.run(this.pool);

    return result.map((row) => {
      const total = parseInt(row.total, 10);
      const reviewed = parseInt(row.reviewed, 10);
      const correct = parseInt(row.correct, 10);
      const accuracy_rate = reviewed > 0 ? correct / reviewed : 0;

      return {
        model: row.model,
        total_executions: total,
        reviewed_executions: reviewed,
        correct_executions: correct,
        accuracy_rate: Math.round(accuracy_rate * 100) / 100,
      };
    });
  }

  /**
   * Get executions affecting a specific product.
   *
   * @param productId - The product ID
   * @returns Array of executions that affected the product
   */
  async getExecutionsForProduct(
    productId: number,
  ): Promise<s.agent_executions.JSONSelectable[]> {
    return this.queryExecutions({ product_id: productId });
  }

  /**
   * Get executions affecting a specific category.
   *
   * @param categoryId - The category ID
   * @returns Array of executions that affected the category
   */
  async getExecutionsForCategory(
    categoryId: number,
  ): Promise<s.agent_executions.JSONSelectable[]> {
    return this.queryExecutions({ category_id: categoryId });
  }
}
