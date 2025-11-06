import { Injectable, Logger } from "@nestjs/common";
import { CategoryDiscoveryAgent } from "../../agents/category-discovery.agent";

/**
 * CLI Command for Category Discovery
 * Exposes the discoverCategoriesFromFilter method via command line
 */
@Injectable()
export class CategoryDiscoveryCommand {
  private readonly logger = new Logger(CategoryDiscoveryCommand.name);

  constructor(private categoryDiscoveryAgent: CategoryDiscoveryAgent) {}

  /**
   * Execute category discovery from CLI
   * @param categories - Array of category names to filter
   */
  async execute(categories: string[]): Promise<void> {
    try {
      this.logger.log(
        `Starting category discovery for: ${categories.join(", ")}`,
      );

      const result =
        await this.categoryDiscoveryAgent.discoverCategoriesFromFilter(
          categories,
        );

      this.logger.log(`✅ Discovery completed successfully!`);
      this.logger.log(`📊 Results:`);
      this.logger.log(
        `   - Categories discovered: ${result.categories.length}`,
      );
      this.logger.log(`   - Products analyzed: ${result.totalProducts}`);
      this.logger.log(`   - Execution ID: ${result.executionId}`);

      // Print discovered categories
      console.log("\n📋 Discovered Categories:");
      result.categories.forEach((category, index) => {
        console.log(
          `${index + 1}. ${category.display_name} (${category.name})`,
        );
        console.log(`   Products: ${category.product_count}`);
        if (category.reasoning) {
          console.log(`   Reasoning: ${category.reasoning}`);
        }
        console.log("");
      });
    } catch (error) {
      this.logger.error(
        `❌ Category discovery failed: ${error instanceof Error ? error.message : String(error)}`,
      );
      throw error;
    }
  }
}
