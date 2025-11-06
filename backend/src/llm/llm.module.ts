import { Module } from "@nestjs/common";
import { ConfigModule } from "@nestjs/config";
import { LLMClientService } from "./llm-client.service";

@Module({
  imports: [ConfigModule],
  providers: [LLMClientService],
  exports: [LLMClientService],
})
export class LLMModule {}
