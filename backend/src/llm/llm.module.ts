import { Module } from "@nestjs/common";
import { ConfigModule } from "@nestjs/config";
import { LLMClientService } from "./llm-client.service";
import { ModelConfigService } from "./config/model.config";

@Module({
  imports: [ConfigModule],
  providers: [LLMClientService, ModelConfigService],
  exports: [LLMClientService, ModelConfigService],
})
export class LLMModule {}
