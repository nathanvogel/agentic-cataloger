import { describe, it, expect, beforeAll, afterAll, afterEach } from "vitest";
import { Pool } from "pg";
import { AgentExecutionRepository } from "./agent-execution.repository";
import { cleanupTestData, createTestExecution } from "./test-helpers";

describe("AgentExecutionRepository Integration Tests", () => {
  let pool: Pool;
  let repository: AgentExecutionRepository;

  beforeAll(() => {
    pool = new Pool({
      connectionString: process.env.DATABASE_URL,
    });
    repository = new AgentExecutionRepository(pool);
  });

  afterEach(async () => {
    await cleanupTestData(pool);
  });

  afterAll(async () => {
    await pool.end();
  });

  describe("logExecution", () => {
    it("should create a complete execution log", async () => {
      const execution = await repository.logExecution({
        phase: "CATEGORY_DISCOVERY",
        status: "success",
        llm_input: { prompt: "test", products: [1, 2, 3] },
        llm_output: { categories: ["A", "B"] },
        product_ids: [1, 2, 3],
        category_ids: [10, 11],
        tokens_used: 1500,
        duration_ms: 2300,
        llm_model: "gpt-4",
        llm_provider: "openai",
      });

      expect(execution.id).toBeDefined();
      expect(execution.phase).toBe("CATEGORY_DISCOVERY");
      expect(execution.status).toBe("success");
      expect(execution.llm_input).toEqual({
        prompt: "test",
        products: [1, 2, 3],
      });
      expect(execution.llm_output).toEqual({ categories: ["A", "B"] });
      expect(execution.product_ids).toEqual([1, 2, 3]);
      expect(execution.category_ids).toEqual([10, 11]);
      expect(execution.tokens_used).toBe(1500);
      expect(execution.duration_ms).toBe(2300);
      expect(execution.llm_model).toBe("gpt-4");
      expect(execution.llm_provider).toBe("openai");
      expect(execution.is_reviewed).toBe(false);
      expect(execution.completed_at).toBeTruthy();
    });

    it("should handle error status with error message", async () => {
      const execution = await repository.logExecution({
        phase: "SCHEMA_GENERATION",
        status: "error",
        llm_input: { test: "input" },
        llm_output: {},
        error_message: "API timeout",
        llm_model: "claude-3",
        llm_provider: "anthropic",
      });

      expect(execution.status).toBe("error");
      expect(execution.error_message).toBe("API timeout");
    });

    it("should handle minimal execution log", async () => {
      const execution = await repository.logExecution({
        phase: "ATTRIBUTE_EXTRACTION",
        status: "success",
        llm_input: {},
        llm_output: {},
        llm_model: "gemini-pro",
        llm_provider: "google",
      });

      expect(execution.id).toBeDefined();
      expect(execution.product_ids).toEqual([]);
      expect(execution.category_ids).toEqual([]);
      expect(execution.schema_ids).toEqual([]);
    });
  });

  describe("markAsReviewed", () => {
    it("should mark execution as reviewed with correctness", async () => {
      const execution = await createTestExecution(pool);

      await repository.markAsReviewed(execution.id, {
        is_correct: true,
        reviewer_notes: "Looks good",
      });

      const updated = await repository.getExecution(execution.id);
      expect(updated?.is_reviewed).toBe(true);
      expect(updated?.is_correct).toBe(true);
      expect(updated?.reviewer_notes).toBe("Looks good");
      expect(updated?.reviewed_at).toBeTruthy();
    });

    it("should mark execution as incorrect", async () => {
      const execution = await createTestExecution(pool);

      await repository.markAsReviewed(execution.id, {
        is_correct: false,
        reviewer_notes: "Wrong categories",
      });

      const updated = await repository.getExecution(execution.id);
      expect(updated?.is_correct).toBe(false);
    });
  });

  describe("getExecution", () => {
    it("should return execution by ID", async () => {
      const created = await createTestExecution(pool, {
        llm_model: "test-model",
      });

      const execution = await repository.getExecution(created.id);

      expect(execution).toBeTruthy();
      expect(execution?.llm_model).toBe("test-model");
    });

    it("should return null for non-existent execution", async () => {
      const execution = await repository.getExecution(999999);
      expect(execution).toBeNull();
    });
  });

  describe("queryExecutions", () => {
    it("should filter by phase", async () => {
      await createTestExecution(pool, {
        phase: "CATEGORY_DISCOVERY",
      });
      await createTestExecution(pool, {
        phase: "SCHEMA_GENERATION",
      });
      await createTestExecution(pool, {
        phase: "CATEGORY_DISCOVERY",
      });

      const executions = await repository.queryExecutions({
        phase: "CATEGORY_DISCOVERY",
      });

      expect(executions.length).toBeGreaterThanOrEqual(2);
      expect(executions.every((e) => e.phase === "CATEGORY_DISCOVERY")).toBe(
        true,
      );
    });

    it("should filter by status", async () => {
      await createTestExecution(pool, { status: "success" });
      await createTestExecution(pool, { status: "error" });
      await createTestExecution(pool, { status: "success" });

      const executions = await repository.queryExecutions({
        status: "success",
      });

      expect(executions.length).toBeGreaterThanOrEqual(2);
      expect(executions.every((e) => e.status === "success")).toBe(true);
    });

    it("should filter by model", async () => {
      await createTestExecution(pool, { llm_model: "gpt-4" });
      await createTestExecution(pool, { llm_model: "claude-3" });
      await createTestExecution(pool, { llm_model: "gpt-4" });

      const executions = await repository.queryExecutions({
        llm_model: "gpt-4",
      });

      expect(executions.length).toBeGreaterThanOrEqual(2);
      expect(executions.every((e) => e.llm_model === "gpt-4")).toBe(true);
    });

    it("should filter by review status", async () => {
      const reviewed = await createTestExecution(pool, {
        is_reviewed: true,
      });
      await createTestExecution(pool, { is_reviewed: false });

      const executions = await repository.queryExecutions({
        is_reviewed: true,
      });

      expect(executions.some((e) => e.id === reviewed.id)).toBe(true);
      expect(executions.every((e) => e.is_reviewed === true)).toBe(true);
    });

    it("should filter by product_id", async () => {
      await createTestExecution(pool, { product_ids: [100, 101] });
      await createTestExecution(pool, { product_ids: [200] });
      await createTestExecution(pool, { product_ids: [100, 300] });

      const executions = await repository.queryExecutions({
        product_id: 100,
      });

      expect(executions.length).toBeGreaterThanOrEqual(2);
      expect(executions.every((e) => e.product_ids?.includes(100))).toBe(true);
    });

    it("should filter by category_id", async () => {
      await createTestExecution(pool, { category_ids: [5, 6] });
      await createTestExecution(pool, { category_ids: [7] });
      await createTestExecution(pool, { category_ids: [5, 8] });

      const executions = await repository.queryExecutions({
        category_id: 5,
      });

      expect(executions.length).toBeGreaterThanOrEqual(2);
      expect(executions.every((e) => e.category_ids?.includes(5))).toBe(true);
    });

    it("should combine multiple filters", async () => {
      await createTestExecution(pool, {
        phase: "CATEGORY_DISCOVERY",
        status: "success",
        llm_model: "gpt-4",
      });
      await createTestExecution(pool, {
        phase: "CATEGORY_DISCOVERY",
        status: "error",
        llm_model: "gpt-4",
      });

      const executions = await repository.queryExecutions({
        phase: "CATEGORY_DISCOVERY",
        status: "success",
        llm_model: "gpt-4",
      });

      expect(executions.length).toBeGreaterThanOrEqual(1);
      expect(
        executions.every(
          (e) =>
            e.phase === "CATEGORY_DISCOVERY" &&
            e.status === "success" &&
            e.llm_model === "gpt-4",
        ),
      ).toBe(true);
    });

    it("should respect limit parameter", async () => {
      for (let i = 0; i < 5; i++) {
        await createTestExecution(pool);
      }

      const executions = await repository.queryExecutions({}, 3);

      expect(executions.length).toBeLessThanOrEqual(3);
    });
  });

  describe("getExecutionsByPhase", () => {
    it("should return executions for specific phase", async () => {
      await createTestExecution(pool, {
        phase: "SCHEMA_GENERATION",
      });

      const executions =
        await repository.getExecutionsByPhase("SCHEMA_GENERATION");

      expect(executions.length).toBeGreaterThanOrEqual(1);
      expect(executions.every((e) => e.phase === "SCHEMA_GENERATION")).toBe(
        true,
      );
    });
  });

  describe("getExecutionsByStatus", () => {
    it("should return executions with specific status", async () => {
      await createTestExecution(pool, { status: "partial" });

      const executions = await repository.getExecutionsByStatus("partial");

      expect(executions.length).toBeGreaterThanOrEqual(1);
      expect(executions.every((e) => e.status === "partial")).toBe(true);
    });
  });

  describe("getExecutionsByModel", () => {
    it("should return executions for specific model", async () => {
      await createTestExecution(pool, { llm_model: "claude-3-opus" });

      const executions = await repository.getExecutionsByModel("claude-3-opus");

      expect(executions.length).toBeGreaterThanOrEqual(1);
      expect(executions.every((e) => e.llm_model === "claude-3-opus")).toBe(
        true,
      );
    });
  });

  describe("getUnreviewedExecutions", () => {
    it("should return only unreviewed executions", async () => {
      await createTestExecution(pool, { is_reviewed: false });
      await createTestExecution(pool, { is_reviewed: true });

      const executions = await repository.getUnreviewedExecutions();

      expect(executions.length).toBeGreaterThanOrEqual(1);
      expect(executions.every((e) => e.is_reviewed === false)).toBe(true);
    });
  });

  describe("getAccuracyStatsByModel", () => {
    it("should calculate accuracy statistics per model", async () => {
      // Create executions for gpt-4
      await createTestExecution(pool, {
        llm_model: "gpt-4-test",
        is_reviewed: true,
        is_correct: true,
      });
      await createTestExecution(pool, {
        llm_model: "gpt-4-test",
        is_reviewed: true,
        is_correct: true,
      });
      await createTestExecution(pool, {
        llm_model: "gpt-4-test",
        is_reviewed: true,
        is_correct: false,
      });
      await createTestExecution(pool, {
        llm_model: "gpt-4-test",
        is_reviewed: false,
      });

      const stats = await repository.getAccuracyStatsByModel();

      const gpt4Stats = stats.find((s) => s.model === "gpt-4-test");
      expect(gpt4Stats).toBeDefined();
      expect(gpt4Stats?.total_executions).toBe(4);
      expect(gpt4Stats?.reviewed_executions).toBe(3);
      expect(gpt4Stats?.correct_executions).toBe(2);
      expect(gpt4Stats?.accuracy_rate).toBeCloseTo(0.67, 1);
    });

    it("should handle models with no reviews", async () => {
      await createTestExecution(pool, {
        llm_model: "new-model",
        is_reviewed: false,
      });

      const stats = await repository.getAccuracyStatsByModel();

      const newModelStats = stats.find((s) => s.model === "new-model");
      expect(newModelStats?.reviewed_executions).toBe(0);
      expect(newModelStats?.accuracy_rate).toBe(0);
    });
  });

  describe("getExecutionsForProduct", () => {
    it("should return executions affecting a product", async () => {
      await createTestExecution(pool, { product_ids: [123, 456] });
      await createTestExecution(pool, { product_ids: [789] });

      const executions = await repository.getExecutionsForProduct(123);

      expect(executions.length).toBeGreaterThanOrEqual(1);
      expect(executions.every((e) => e.product_ids?.includes(123))).toBe(true);
    });
  });

  describe("getExecutionsForCategory", () => {
    it("should return executions affecting a category", async () => {
      await createTestExecution(pool, { category_ids: [42, 43] });
      await createTestExecution(pool, { category_ids: [99] });

      const executions = await repository.getExecutionsForCategory(42);

      expect(executions.length).toBeGreaterThanOrEqual(1);
      expect(executions.every((e) => e.category_ids?.includes(42))).toBe(true);
    });
  });
});
