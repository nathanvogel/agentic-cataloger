import { z } from "zod";

/**
 * Supported LLM providers
 */
export enum LLMProvider {
  OPENAI = "openai",
  ANTHROPIC = "anthropic",
  GOOGLE = "google",
}

/**
 * Options for LLM completion requests
 */
export interface CompletionOptions {
  provider: LLMProvider;
  model: string;
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
    /** The number of input (prompt) tokens used. */
    inputTokens: number | undefined;
    /** The number of output (completion) tokens used. */
    outputTokens: number | undefined;
    /**
  The total number of tokens as reported by the provider.
  This number might be different from the sum of `inputTokens` and `outputTokens`
  and e.g. include reasoning tokens or other overhead.
     */
    totalTokens: number | undefined;
    /** The number of reasoning tokens used. */
    reasoningTokens?: number | undefined;
    /** The number of cached input tokens. */
    cachedInputTokens?: number | undefined;
  };
  model: string;
  finishReason: string;
  provider: string;
  duration: number;
  isPartial?: boolean; // Indicates if response is incomplete due to errors
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
  generateArray<T>(
    prompt: string,
    schema: z.ZodSchema<T>,
    options?: CompletionOptions,
  ): Promise<LLMResponse<T[]>>;
}
