import { z } from "zod";
import { LLMProvider } from "../config/model.config";

/**
 * Options for LLM completion requests
 */
export interface CompletionOptions {
  provider?: LLMProvider;
  model?: string;
  temperature?: number;
  maxTokens?: number;
  retries?: number;
  timeout?: number;
}

/**
 * LLM response with usage metadata
 */
export interface LLMResponse<T> {
  data: T;
  usage: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
  model: string;
  finishReason: string;
  provider: string;
  duration: number;
}

/**
 * LLM Client interface for model-agnostic interactions
 */
export interface ILLMClient {
  /**
   * Send prompt to LLM and get structured response
   * @param prompt The prompt to send to the LLM
   * @param schema Zod schema for response validation
   * @param options Optional completion parameters
   */
  complete<T>(
    prompt: string,
    schema: z.ZodSchema<T>,
    options?: CompletionOptions,
  ): Promise<LLMResponse<T>>;
}
