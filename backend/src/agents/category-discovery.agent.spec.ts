import { Test, TestingModule } from "@nestjs/testing";
import {
  CategoryDiscoveryAgent,
  ProductSummary,
} from "./category-discovery.agent";
import { LLMClientService } from "../llm/llm-client.service";
import { ProductsRepository } from "../database/repositories/products.repository";
import { CategoryRepository } from "../database/repositories/category.repository";
import { AgentExecutionRepository } from "../database/repositories/agent-execution.repository";
import { describe, it, expect, beforeEach, vi } from "vitest";

describe("CategoryDiscoveryAgent", () => {
  let agent: CategoryDiscoveryAgent;
  let llmClient: LLMClientService;
  let productsRepository: ProductsRepository;
  let categoryRepository: CategoryRepository;
  let executionRepository: AgentExecutionRepository;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [
        CategoryDiscoveryAgent,
        {
          provide: LLMClientService,
          useValue: {
            complete: vi.fn(),
          },
        },

        {
          provide: ProductsRepository,
          useValue: {
            getProductsByCategories: vi.fn(),
          },
        },
        {
          provide: CategoryRepository,
          useValue: {
            createCategory: vi.fn(),
            assignProducts: vi.fn(),
          },
        },
        {
          provide: AgentExecutionRepository,
          useValue: {
            logExecution: vi.fn(),
            getExecutionsByPhase: vi.fn(),
          },
        },
      ],
    }).compile();

    agent = module.get<CategoryDiscoveryAgent>(CategoryDiscoveryAgent);
    llmClient = module.get<LLMClientService>(LLMClientService);
    productsRepository = module.get<ProductsRepository>(ProductsRepository);
    categoryRepository = module.get<CategoryRepository>(CategoryRepository);
    executionRepository = module.get<AgentExecutionRepository>(
      AgentExecutionRepository,
    );
  });

  describe("discoverCategories", () => {
    it("should discover categories from product summaries", async () => {
      const products: ProductSummary[] = [
        {
          id: 1,
          name: "Zitronen Bio",
          supermarket: "migros",
          unit: "kg",
          price: 3.5,
        },
        {
          id: 2,
          name: "Zitronen",
          supermarket: "coop",
          unit: "kg",
          price: 2.9,
        },
        {
          id: 3,
          name: "Limetten",
          supermarket: "lidl",
          unit: "kg",
          price: 4.2,
        },
      ];

      const mockResponse = {
        data: {
          categories: [
            {
              name: "lemon",
              displayName: "Lemon",
              productIds: [1, 2],
              reasoning:
                "Both products are lemons, organic and non-organic are substitutable",
              confidence: 0.95,
            },
            {
              name: "lime",
              displayName: "Lime",
              productIds: [3],
              reasoning: "Limes are not substitutable with lemons",
              confidence: 0.98,
            },
          ],
        },
        usage: {
          promptTokens: 500,
          completionTokens: 200,
          totalTokens: 700,
        },
        model: "gpt-4o",
        finishReason: "stop",
        provider: "openai",
        duration: 1500,
      };

      vi.mocked(llmClient.generateObject).mockResolvedValue(mockResponse);
      vi.mocked(executionRepository.logExecution).mockResolvedValue({
        id: 1,
      } as any);

      const result = await agent.discoverCategories(products);

      expect(result).toHaveLength(2);
      expect(result[0].name).toBe("lemon");
      expect(result[0].productIds).toEqual([1, 2]);
      expect(result[1].name).toBe("lime");
      expect(result[1].productIds).toEqual([3]);

      expect(llmClient.generateObject).toHaveBeenCalledOnce();
      expect(executionRepository.logExecution).toHaveBeenCalledWith(
        expect.objectContaining({
          phase: "CATEGORY_DISCOVERY",
          status: "success",
          tokens_used: 700,
          llm_model: "gpt-4o",
          llm_provider: "openai",
        }),
      );
    });

    it("should log execution on error", async () => {
      const products: ProductSummary[] = [
        {
          id: 1,
          name: "Test Product",
          supermarket: "migros",
          unit: null,
          price: null,
        },
      ];

      const error = new Error("LLM API error");
      vi.mocked(llmClient.generateObject).mockRejectedValue(error);
      vi.mocked(executionRepository.logExecution).mockResolvedValue({
        id: 1,
      } as any);

      await expect(agent.discoverCategories(products)).rejects.toThrow(
        "LLM API error",
      );

      expect(executionRepository.logExecution).toHaveBeenCalledWith(
        expect.objectContaining({
          phase: "CATEGORY_DISCOVERY",
          status: "error",
          error_message: "LLM API error",
        }),
      );
    });
  });

  describe("discoverCategoriesFromFilter", () => {
    it("should discover categories from database products", async () => {
      const mockProducts = [
        {
          id: 1,
          name: "Zitronen Bio",
          supermarket: "migros",
          unit: "kg",
          price: 3.5,
          category_id: 1,
          categories: [],
          attributes: {},
        },
        {
          id: 2,
          name: "Zitronen",
          supermarket: "coop",
          unit: "kg",
          price: 2.9,
          category_id: 1,
          categories: [],
          attributes: {},
        },
      ];

      const mockLLMResponse = {
        data: {
          categories: [
            {
              name: "lemon",
              displayName: "Lemon",
              productIds: [1, 2],
              reasoning: "Both are lemons",
              confidence: 0.95,
            },
          ],
        },
        usage: { promptTokens: 500, completionTokens: 200, totalTokens: 700 },
        model: "gpt-4o",
        finishReason: "stop",
        provider: "openai",
        duration: 1500,
      };

      vi.mocked(productsRepository.getProductsByCategories).mockResolvedValue(
        mockProducts,
      );
      vi.mocked(llmClient.generateObject).mockResolvedValue(mockLLMResponse);
      vi.mocked(categoryRepository.createCategory).mockResolvedValue({
        id: 1,
        name: "lemon",
        display_name: "Lemon",
      } as any);
      vi.mocked(categoryRepository.assignProducts).mockResolvedValue(undefined);
      vi.mocked(executionRepository.logExecution).mockResolvedValue({
        id: 1,
      } as any);
      vi.mocked(executionRepository.getExecutionsByPhase).mockResolvedValue([
        { id: 1 } as any,
      ]);

      const result = await agent.discoverCategoriesFromFilter([
        "Gemüse",
        "Früchte",
      ]);

      expect(result.categories).toHaveLength(1);
      expect(result.totalProducts).toBe(2);
      expect(productsRepository.getProductsByCategories).toHaveBeenCalledWith([
        "Gemüse",
        "Früchte",
      ]);
      expect(categoryRepository.createCategory).toHaveBeenCalledWith({
        name: "lemon",
        display_name: "Lemon",
        reasoning: "Both are lemons",
        confidence: 0.95,
      });
      expect(categoryRepository.assignProducts).toHaveBeenCalledWith(1, [1, 2]);
    });

    it("should throw error when no products found", async () => {
      vi.mocked(productsRepository.getProductsByCategories).mockResolvedValue(
        [],
      );

      await expect(
        agent.discoverCategoriesFromFilter(["NonExistent"]),
      ).rejects.toThrow("No products found");
    });
  });
});
