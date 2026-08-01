#!/usr/bin/env node

import "dotenv/config";
import { Pool } from "pg";
import { ConfigService } from "@nestjs/config";
import { CategoryDiscoveryAgent } from "../agents/category-discovery.agent";
import { ProductsRepository } from "../database/repositories/products.repository";
import { CategoryRepository } from "../database/repositories/category.repository";
import { AgentExecutionRepository } from "../database/repositories/agent-execution.repository";
import { LLMClientService } from "../llm/llm-client.service";

/**
 * Simple ConfigService implementation for standalone CLI
 */
class SimpleConfigService extends ConfigService {
  get<T = any>(propertyPath: string): T | undefined {
    return process.env[propertyPath] as T;
  }
}

/**
 * Standalone CLI for Category Discovery
 * Bypasses NestJS DI to avoid dependency resolution issues
 */
async function main() {
  const args = process.argv.slice(2);
  const command = args[0];

  if (
    command === "help" ||
    command === "--help" ||
    command === "-h" ||
    !command
  ) {
    printHelp();
    return;
  }

  if (command !== "discover-categories") {
    console.error(`❌ Unknown command: ${command}`);
    printHelp();
    process.exit(1);
  }

  const categories = args.slice(1);

  if (categories.length === 0) {
    console.error("❌ Error: Please provide category names to filter");
    console.log(
      "Usage: yarn cli:standalone discover-categories <category1> [category2] ...",
    );
    console.log(
      "Example: yarn cli:standalone discover-categories Gemüse Früchte",
    );
    process.exit(1);
  }

  try {
    // Create database pool
    const pool = new Pool({
      connectionString: process.env.DATABASE_URL,
    });

    // Create repositories
    const productsRepository = new ProductsRepository(pool);
    const categoryRepository = new CategoryRepository(pool);
    const agentExecutionRepository = new AgentExecutionRepository(pool);

    // Create services
    const configService = new SimpleConfigService();
    const llmClientService = new LLMClientService(configService);

    // Create agent
    const categoryDiscoveryAgent = new CategoryDiscoveryAgent(
      llmClientService,
      productsRepository,
      categoryRepository,
      agentExecutionRepository,
    );

    console.log(`🚀 Starting category discovery for: ${categories.join(", ")}`);

    const result =
      await categoryDiscoveryAgent.discoverCategoriesFromFilter(categories);

    console.log(`✅ Discovery completed successfully!`);
    console.log(`📊 Results:`);
    console.log(`   - Categories discovered: ${result.categories.length}`);
    console.log(`   - Products analyzed: ${result.totalProducts}`);
    console.log(`   - Execution ID: ${result.executionId}`);

    // Print discovered categories
    console.log("\n📋 Discovered Categories:");
    result.categories.forEach((category, index) => {
      console.log(`${index + 1}. ${category.display_name} (${category.name})`);
      console.log(`   Products: ${category.product_count}`);
      if (category.reasoning) {
        console.log(`   Reasoning: ${category.reasoning}`);
      }
      console.log("");
    });

    await pool.end();
  } catch (error) {
    console.error(
      `❌ Category discovery failed: ${error instanceof Error ? error.message : String(error)}`,
    );
    process.exit(1);
  }
}

function printHelp() {
  console.log(`
🛠️  Backend CLI Commands (Standalone)

Available commands:
  discover-categories <category1> [category2] ...  Discover product categories from filter
  help, --help, -h                               Show this help message

Examples:
  yarn cli:standalone discover-categories Gemüse Früchte
  yarn cli:standalone discover-categories "Milch & Eier" Fleisch
  yarn cli:standalone help

Note: Category names are case-sensitive and should match the categories in your database.
`);
}

// Handle unhandled promise rejections
process.on("unhandledRejection", (reason, promise) => {
  console.error("Unhandled Rejection at:", promise, "reason:", reason);
  process.exit(1);
});

void main();
