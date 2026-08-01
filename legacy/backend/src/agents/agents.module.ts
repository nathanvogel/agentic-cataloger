import { Module } from "@nestjs/common";
import { CategoryDiscoveryAgent } from "./category-discovery.agent";
import { LLMModule } from "../llm/llm.module";
import { DatabaseModule } from "../database/database.module";

/**
 * Agents Module
 * Provides LLM-powered agents for product categorization system
 */
@Module({
  imports: [LLMModule, DatabaseModule],
  providers: [CategoryDiscoveryAgent],
  exports: [CategoryDiscoveryAgent],
})
export class AgentsModule {}
