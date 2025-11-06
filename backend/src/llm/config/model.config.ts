import { Injectable } from "@nestjs/common";
import { ConfigService } from "@nestjs/config";

/**
 * Supported LLM providers
 */
export enum LLMProvider {
  OPENAI = "openai",
  ANTHROPIC = "anthropic",
  GOOGLE = "google",
}

/**
 * LLM operations for product categorization
 */
export enum LLMOperation {
  CATEGORY_DISCOVERY = "CATEGORY_DISCOVERY",
  SCHEMA_GENERATION = "SCHEMA_GENERATION",
  ATTRIBUTE_EXTRACTION = "ATTRIBUTE_EXTRACTION",
}

/**
 * Model configuration
 */
export interface ModelConfig {
  provider: LLMProvider;
  model: string;
  temperature: number;
  maxTokens: number;
}

/**
 * Default model configurations per operation
 * - Category Discovery: Requires strong reasoning (GPT-4, Claude Opus, Gemini Pro)
 * - Schema Generation: Requires structured thinking (GPT-4, Claude Opus, Gemini Pro)
 * - Attribute Extraction: High volume, simpler task (Claude Sonnet or cheaper models)
 */
const DEFAULT_MODEL_CONFIG: Record<LLMOperation, ModelConfig> = {
  // requires strong reasoning
  [LLMOperation.CATEGORY_DISCOVERY]: {
    provider: LLMProvider.OPENAI,
    model: "gpt-5",
    temperature: 0.7,
    maxTokens: 30000,
  },
  // requires structured thinking
  [LLMOperation.SCHEMA_GENERATION]: {
    provider: LLMProvider.OPENAI,
    model: "gpt-4.1-nano",
    temperature: 0.7,
    maxTokens: 4096,
  },
  // high volume, simpler task
  [LLMOperation.ATTRIBUTE_EXTRACTION]: {
    provider: LLMProvider.OPENAI,
    model: "gpt-4.1-nano",
    temperature: 0.5,
    maxTokens: 2048,
  },
};

/**
 * Model Configuration Service
 * Manages LLM model configurations with environment variable overrides
 */
@Injectable()
export class ModelConfigService {
  constructor(private configService: ConfigService) {}

  /**
   * Get model configuration for a specific operation
   * Supports environment variable overrides and explicit overrides
   */
  getModelConfig(
    operation: LLMOperation,
    overrides?: Partial<ModelConfig>,
  ): ModelConfig {
    const config = { ...DEFAULT_MODEL_CONFIG[operation] };

    // Check for environment variable overrides
    const envProvider = this.configService.get<string>(`${operation}_PROVIDER`);
    const envModel = this.configService.get<string>(`${operation}_MODEL`);

    if (
      envProvider &&
      Object.values(LLMProvider).includes(envProvider as LLMProvider)
    ) {
      config.provider = envProvider as LLMProvider;
    }

    if (envModel) {
      config.model = envModel;
    }

    // Apply explicit overrides
    if (overrides) {
      Object.assign(config, overrides);
    }

    return config;
  }

  /**
   * Get all default configurations
   */
  getAllDefaultConfigs(): Record<LLMOperation, ModelConfig> {
    return { ...DEFAULT_MODEL_CONFIG };
  }
}
