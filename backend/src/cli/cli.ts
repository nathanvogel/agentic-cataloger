#!/usr/bin/env node

import "dotenv/config";
import { NestFactory } from "@nestjs/core";
import { CliModule } from "./cli.module";
import { CategoryDiscoveryCommand } from "./commands/category-discovery.command";

/**
 * CLI Entry Point
 * Handles command line arguments and routes to appropriate commands
 */
async function bootstrap() {
  const app = await NestFactory.createApplicationContext(CliModule, {
    logger: ["error", "warn", "log"],
  });

  const args = process.argv.slice(2);
  const command = args[0];

  try {
    switch (command) {
      case "discover-categories": {
        const categories = args.slice(1);

        if (categories.length === 0) {
          console.error("❌ Error: Please provide category names to filter");
          console.log(
            "Usage: yarn cli discover-categories <category1> [category2] ...",
          );
          console.log("Example: yarn cli discover-categories Gemüse Früchte");
          process.exit(1);
        }

        const categoryDiscovery = app.get(CategoryDiscoveryCommand);
        await categoryDiscovery.execute(categories);
        break;
      }

      case "help":
      case "--help":
      case "-h":
        printHelp();
        break;

      default:
        console.error(`❌ Unknown command: ${command}`);
        printHelp();
        process.exit(1);
    }
  } catch (error) {
    console.error(
      `❌ Command failed: ${error instanceof Error ? error.message : String(error)}`,
    );
    process.exit(1);
  } finally {
    await app.close();
  }
}

function printHelp() {
  console.log(`
🛠️  Backend CLI Commands

Available commands:
  discover-categories <category1> [category2] ...  Discover product categories from filter
  help, --help, -h                               Show this help message

Examples:
  yarn cli discover-categories Gemüse Früchte
  yarn cli discover-categories "Milch & Eier" Fleisch
  yarn cli help

Note: Category names are case-sensitive and should match the categories in your database.
`);
}

// Handle unhandled promise rejections
process.on("unhandledRejection", (reason, promise) => {
  console.error("Unhandled Rejection at:", promise, "reason:", reason);
  process.exit(1);
});

void bootstrap();
