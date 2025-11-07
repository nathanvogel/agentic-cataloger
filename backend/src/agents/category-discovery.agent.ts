import { Injectable, Logger } from "@nestjs/common";
import { z } from "zod";
import { LLMClientService } from "../llm/llm-client.service";
import { LLMProvider } from "../llm/interfaces/llm-client.interface";
import { ProductsRepository } from "../database/repositories/products.repository";
import { CategoryRepository } from "../database/repositories/category.repository";
import {
  AgentExecutionRepository,
  AgentPhase,
} from "../database/repositories/agent-execution.repository";
import { categories } from "zapatos/schema";

/**
 * Product summary for category discovery
 */
export interface ProductSummary {
  id: number;
  name: string;
  supermarket: string;
  unit: string | null;
  price: number | null;
}

/**
 * Discovered category from LLM analysis
 */
export interface DiscoveredCategory {
  name: string; // e.g., "lemon", "apple", "tomato-cherry"
  displayName: string; // e.g., "Lemon", "Apple", "Cherry Tomato"
  productIds: number[];
  reasoning: string; // LLM explanation for category
  confidence?: number; // Confidence score (optional for MVP)
}

/**
 * Result of category discovery operation
 */
export interface CategoryDiscoveryResult {
  categories: categories.JSONSelectable[];
  totalProducts: number;
  executionId: number;
}

/**
 * Zod schema for LLM response validation
 */
const DiscoveredCategorySchema = z.object({
  name: z.string().describe("Category name in lowercase_snake_case"),
  displayName: z.string().describe("Human-readable category name"),
  productIds: z
    .array(z.number())
    .describe("Array of product IDs in this category"),
  reasoning: z
    .string()
    .describe("Explanation for why these products form a category"),
  confidence: z
    .number()
    .min(0)
    .max(1)
    .optional()
    .describe("Confidence score 0-1"),
});

const CategoryDiscoveryResponseSchema = z.array(DiscoveredCategorySchema);

/**
 * Category Discovery Agent
 * Analyzes products and creates precise categories based on consumer substitutability.
 * Requirements: 1.1, 1.2, 1.3, 1.4
 */
@Injectable()
export class CategoryDiscoveryAgent {
  private readonly logger = new Logger(CategoryDiscoveryAgent.name);

  constructor(
    private llmClient: LLMClientService,
    private productsRepository: ProductsRepository,
    private categoryRepository: CategoryRepository,
    private executionRepository: AgentExecutionRepository,
  ) {}

  /**
   * Discover categories from products filtered by category names.
   * This is the main entry point that handles the full workflow:
   * 1. Query products by category filter
   * 2. Prepare product summaries
   * 3. Call LLM for category discovery
   * 4. Validate and store categories
   * 5. Assign products to categories
   * 6. Log execution
   *
   * @param categoryFilter - Array of category names to filter (e.g., ["Gemüse", "Früchte"])
   * @returns Discovery result with categories and execution ID
   *
   * @example
   * ```typescript
   * const result = await agent.discoverCategoriesFromFilter(['Gemüse', 'Früchte']);
   * console.log(`Discovered ${result.categories.length} categories`);
   * ```
   */
  async discoverCategoriesFromFilter(
    categoryFilter: string[],
  ): Promise<CategoryDiscoveryResult> {
    this.logger.log(
      `Starting category discovery for categories: ${categoryFilter.join(", ")}`,
    );

    // Step 1: Query products
    const products =
      await this.productsRepository.getProductsByCategories(categoryFilter);

    if (products.length === 0) {
      throw new Error(
        `No products found for categories: ${categoryFilter.join(", ")}`,
      );
    }

    this.logger.log(`Found ${products.length} products to analyze`);

    // Step 2: Prepare product summaries
    const productSummaries = this.prepareProductSummaries(products);

    // Step 3: Discover categories using LLM
    const discoveredCategories =
      await this.discoverCategories(productSummaries);

    // Step 4: Validate and store categories
    const result = await this.validateAndStoreCategories(
      discoveredCategories,
      products.length,
    );

    this.logger.log(
      `Category discovery complete. Discovered ${result.categories.length} categories`,
    );

    return result;
  }

  /**
   * Discover categories from product list using LLM.
   * This method handles the LLM interaction, prompt generation, and response parsing.
   *
   * @param products - Array of product summaries
   * @returns Array of discovered categories
   */
  async discoverCategories(
    products: ProductSummary[],
  ): Promise<DiscoveredCategory[]> {
    this.logger.log(`Analyzing ${products.length} products for categorization`);

    // Get existing categories to avoid duplicates
    const existingCategories = await this.categoryRepository.getAllCategories();
    this.logger.log(`Found ${existingCategories.length} existing categories`);

    // Build prompt
    const prompt = this.buildCategoryDiscoveryPrompt(
      products,
      existingCategories,
    );

    const startTime = Date.now();

    try {
      // Call LLM with structured output - requires strong reasoning
      const response = await this.llmClient.generateObject(
        prompt,
        CategoryDiscoveryResponseSchema,
        {
          provider: LLMProvider.GOOGLE,
          model: "gemini-2.5-flash",
          maxTokens: 1000000,
        },
      );

      const duration = Date.now() - startTime;

      this.logger.log(
        `LLM returned ${response.data.length} categories in ${duration}ms`,
      );

      // Log execution
      await this.executionRepository.logExecution({
        phase: "CATEGORY_DISCOVERY" as AgentPhase,
        status: response.isPartial ? "partial" : "success",
        llm_input: {
          prompt,
          productCount: products.length,
          products: products.slice(0, 10), // Sample for logging
        },
        llm_output: response.data,
        product_ids: products.map((p) => p.id),
        tokens_used: response.usage.totalTokens,
        input_tokens: response.usage.inputTokens,
        output_tokens: response.usage.outputTokens,
        reasoning_tokens: response.usage.reasoningTokens,
        cached_input_tokens: response.usage.cachedInputTokens,
        duration_ms: duration,
        llm_model: response.model,
        llm_provider: response.provider,
        error_message: response.isPartial
          ? "Partial results - response was incomplete"
          : undefined,
      });

      if (response.isPartial) {
        this.logger.warn(
          `LLM returned partial results with ${response.data.length} categories`,
        );
      }

      return response.data;
    } catch (error) {
      const duration = Date.now() - startTime;

      // Log failed execution
      await this.executionRepository.logExecution({
        phase: "CATEGORY_DISCOVERY" as AgentPhase,
        status: "error",
        llm_input: {
          prompt,
          productCount: products.length,
        },
        llm_output: {},
        product_ids: products.map((p) => p.id),
        error_message: error instanceof Error ? error.message : String(error),
        duration_ms: duration,
        llm_model: "?",
        llm_provider: "?",
      });

      this.logger.error(`Category discovery failed: ${error}`);
      throw error;
    }
  }

  /**
   * Build the LLM prompt for category discovery.
   * Includes instructions, rules, product data, and existing categories.
   *
   * @param products - Array of product summaries
   * @param existingCategories - Array of existing categories to avoid duplicates
   * @returns Formatted prompt string
   */
  private buildCategoryDiscoveryPrompt(
    products: ProductSummary[],
    existingCategories: categories.JSONSelectable[],
  ): string {
    const productList = products
      .map(
        (p, idx) =>
          `${idx + 1}. [ID: ${p.id}] ${p.name} (${p.supermarket}${p.unit ? `, ${p.unit}` : ""}${p.price ? `, CHF ${p.price}` : ""})`,
      )
      .join("\n");

    const existingCategoryNames = existingCategories
      .map((c) => c.name)
      .sort()
      .join(", ");

    return `You are analyzing grocery products to create categories for price comparison.

EXISTING CATEGORIES (DO NOT CREATE DUPLICATES):
${existingCategoryNames}

IMPORTANT: Only create NEW categories that don't already exist in the list above.

CATEGORIZATION RULES:
1. GROUP products that consumers would reasonably substitute for each other in everyday shopping in the SAME category.
2. Create SEPARATE categories for products that consumers would NOT substitute in the long-term 
3. Create SEPARATE categories for products whose price can not be reasonnably compared by weight/quantity computations.
4. Each product must be assigned to exactly ONE category

CONSUMER SUBSTITUTABILITY PRINCIPLE:
Ask yourself: "Would a regular shopper switch from product A to product B for their everyday needs?"
- If YES → same category
- If NO → different categories

Examples:
- "Zitronen Bio" and "Zitronen" → SAME category ("lemon") - organic vs non-organic are substitutable.
- "Zitronen" and "Limetten" → DIFFERENT categories ("lemon" vs "lime") - not substitutable.
- "Cherry Tomaten" and "Tomaten" → SAME categorie ("tomato") - most recipe can accomodate either.
- "Gala Äpfel" and "Braeburn Äpfel" → SAME categories ("apple") - differentiation can happen downstream via attributes, if desirable for the specific customer.

INPUT: ${products.length} products from supermarkets (Migros, Lidl, Coop, Denner)

PRODUCTS:
${productList}

OUTPUT REQUIREMENTS:
- Return a JSON array (NOT an object with an array field, just the array directly: [...])
- Each array element is a category object with: 
  - name: ID in lowercase_snake_case, singular, in ENGLISH. 
  - displayName: readable, in ENGLISH. 
  - productIds: array of IDs.
  - reasoning: Clear brief explanation on the substitutability logic.
  - confidence: 0-1 on confidence.
- Ensure every product ID appears in exactly one category
- NEVER use German language.
- Start your response with [ and end with ]

Analyze these products and create precise categories based on consumer substitutability.`;
  }

  /**
   * Prepare product summaries from database records.
   * Extracts essential fields for LLM analysis.
   *
   * @param products - Raw product records from database
   * @returns Array of product summaries
   */
  private prepareProductSummaries(
    products: Array<{
      id: number;
      name: string;
      supermarket: string;
      unit: string | null;
      price: number | null;
    }>,
  ): ProductSummary[] {
    return products.map((p) => ({
      id: p.id,
      name: p.name,
      supermarket: p.supermarket || "unknown",
      unit: p.unit || null,
      price: p.price,
    }));
  }

  /**
   * Validate discovered categories and store them in the database.
   * Creates category records and assigns products to categories.
   *
   * @param discoveredCategories - Categories from LLM
   * @param totalProducts - Total number of products analyzed
   * @returns Discovery result with execution ID
   */
  private async validateAndStoreCategories(
    discoveredCategories: DiscoveredCategory[],
    totalProducts: number,
  ): Promise<CategoryDiscoveryResult> {
    this.logger.log(
      `Validating and storing ${discoveredCategories.length} categories`,
    );

    // Validate that all products are assigned
    const assignedProductIds = new Set<number>();
    for (const category of discoveredCategories) {
      for (const productId of category.productIds) {
        if (assignedProductIds.has(productId)) {
          this.logger.warn(
            `Product ${productId} assigned to multiple categories`,
          );
        }
        assignedProductIds.add(productId);
      }
    }

    this.logger.log(
      `Assigned ${assignedProductIds.size} out of ${totalProducts} products`,
    );

    // Store categories and assign products
    const storedCategories: categories.JSONSelectable[] = [];
    const categoryIds: number[] = [];

    for (const discovered of discoveredCategories) {
      try {
        // Check if category already exists
        let category = await this.categoryRepository.getCategoryByName(
          discovered.name,
        );

        if (category) {
          this.logger.log(
            `Using existing category "${category.display_name}" (${category.name})`,
          );
        } else {
          // Create new category
          category = await this.categoryRepository.createCategory({
            name: discovered.name,
            display_name: discovered.displayName,
            reasoning: discovered.reasoning,
            confidence: discovered.confidence,
          });

          this.logger.log(
            `Created new category "${category.display_name}" (${category.name})`,
          );
        }

        categoryIds.push(category.id);

        // Assign products to category
        if (discovered.productIds.length > 0) {
          await this.categoryRepository.assignProducts(
            category.id,
            discovered.productIds,
          );
        }

        storedCategories.push(category);

        this.logger.log(
          `Assigned ${discovered.productIds.length} products to category "${category.display_name}"`,
        );
      } catch (error) {
        this.logger.error(
          `Failed to process category "${discovered.name}": ${error}`,
        );
        throw error;
      }
    }

    // Get the latest execution ID for this phase
    const executions = await this.executionRepository.getExecutionsByPhase(
      "CATEGORY_DISCOVERY",
      1,
    );
    const executionId = executions[0]?.id || 0;

    // Update execution with category IDs
    if (executionId && categoryIds.length > 0) {
      await this.updateExecutionWithCategoryIds(executionId, categoryIds);
    }

    return {
      categories: storedCategories,
      totalProducts,
      executionId,
    };
  }

  /**
   * Update the execution log with category IDs after they are created.
   *
   * @param executionId - The execution ID to update
   * @param categoryIds - Array of category IDs that were created
   */
  private async updateExecutionWithCategoryIds(
    executionId: number,
    categoryIds: number[],
  ): Promise<void> {
    try {
      await this.executionRepository.updateExecutionWithCategoryIds(
        executionId,
        categoryIds,
      );
      this.logger.log(
        `Updated execution ${executionId} with ${categoryIds.length} category IDs`,
      );
    } catch (error) {
      this.logger.error(
        `Failed to update execution ${executionId} with category IDs: ${error}`,
      );
      // Don't throw - this is just logging, shouldn't fail the main operation
    }
  }
}
