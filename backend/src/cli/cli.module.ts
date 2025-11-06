import { Module } from "@nestjs/common";
import { ConfigModule } from "@nestjs/config";
import { DatabaseModule } from "../database/database.module";
import { LLMModule } from "../llm/llm.module";
import { AgentsModule } from "../agents/agents.module";
import { CategoryDiscoveryCommand } from "./commands/category-discovery.command";

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      envFilePath: ".env",
    }),
    DatabaseModule,
    LLMModule,
    AgentsModule,
  ],
  providers: [CategoryDiscoveryCommand],
})
export class CliModule {}
