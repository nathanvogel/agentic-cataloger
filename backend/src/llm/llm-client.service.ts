import { Injectable, Logger } from "@nestjs/common";
import { ConfigService } from "@nestjs/config";
import { generateObject } from "ai";
import { createOpenAI } from "@ai-sdk/openai";
import { createAnthropic } from "@ai-sdk/anthropic";
import { createGoogleGenerativeAI } from "@ai-sdk/google";
import { z } from "zod";
import {
  ILLMClient,
  CompletionOptions,
  LLMResponse,
} from "./interfaces/llm-client.interface";
import { LLMProvider } from "./config/model.config";

/**
 * LLM Client Service
 * Provides model-agnostic interface for LLM interactions with retry logic,
 * timeout handling, and structured JSON output
 */
@Injectable()
export class LLMClientService implements ILLMClient {
  private readonly logger = new Logger(LLMClientService.name);
  private readonly openai: ReturnType<typeof createOpenAI> | null = null;
  private readonly anthropic: ReturnType<typeof createAnthropic> | null = null;
  private readonly google: ReturnType<typeof createGoogleGenerativeAI> | null =
    null;

  constructor(private configService: ConfigService) {
    // Initialize providers
    const openaiKey = this.configService.get<string>("OPENAI_API_KEY");
    const anthropicKey = this.configService.get<string>("ANTHROPIC_API_KEY");
    const googleKey = this.configService.get<string>("GOOGLE_API_KEY");

    if (openaiKey) {
      this.openai = createOpenAI({ apiKey: openaiKey });
    }

    if (anthropicKey) {
      this.anthropic = createAnthropic({ apiKey: anthropicKey });
    }

    if (googleKey) {
      this.google = createGoogleGenerativeAI({ apiKey: googleKey });
    }
  }

  /**
   * Get the appropriate provider client
   */
  private getProviderClient(provider: LLMProvider, model: string) {
    switch (provider) {
      case LLMProvider.OPENAI:
        if (!this.openai) {
          throw new Error("OpenAI API key not configured");
        }
        return this.openai(model);

      case LLMProvider.ANTHROPIC:
        if (!this.anthropic) {
          throw new Error("Anthropic API key not configured");
        }
        return this.anthropic(model);

      case LLMProvider.GOOGLE:
        if (!this.google) {
          throw new Error("Google API key not configured");
        }
        return this.google(model);

      default:
        throw new Error(`Unsupported provider: ${provider}`);
    }
  }

  /**
   * Sleep utility for exponential backoff
   */
  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  /**
   * Send prompt to LLM and get structured response with retry logic
   */
  async complete<T>(
    prompt: string,
    schema: z.ZodSchema<T>,
    options: CompletionOptions = {},
  ): Promise<LLMResponse<T>> {
    const {
      provider = LLMProvider.OPENAI,
      model = "gpt-4o",
      temperature = 0.7,
      maxTokens = 4096,
      retries = 3,
      timeout = 60000,
    } = options;

    let lastError: Error | null = null;

    // Retry loop with exponential backoff
    for (let attempt = 0; attempt < retries; attempt++) {
      try {
        this.logger.log(
          `Attempt ${attempt + 1}/${retries} - Calling ${provider} model ${model}`,
        );

        const startTime = Date.now();

        // Create timeout promise
        const timeoutPromise = new Promise<never>((_, reject) => {
          setTimeout(() => reject(new Error("Request timeout")), timeout);
        });

        // Create completion promise
        const completionPromise = generateObject({
          model: this.getProviderClient(provider, model),
          schema,
          prompt,
          temperature,
          maxTokens,
        });

        // Race between completion and timeout
        const result = await Promise.race([completionPromise, timeoutPromise]);

        const duration = Date.now() - startTime;

        // Log request and response
        this.logger.debug({
          message: "LLM Request",
          model,
          provider,
          promptLength: prompt.length,
          temperature,
          maxTokens,
        });

        this.logger.debug({
          message: "LLM Response",
          model,
          provider,
          duration,
          usage: result.usage,
          finishReason: result.finishReason,
        });

        // Map AI SDK usage to our interface
        const usage = result.usage as any;
        return {
          data: result.object,
          usage: {
            promptTokens: usage.promptTokens || 0,
            completionTokens: usage.completionTokens || 0,
            totalTokens: usage.totalTokens || 0,
          },
          model,
          finishReason: result.finishReason,
          provider,
          duration,
        };
      } catch (error) {
        lastError = error as Error;
        this.logger.warn(
          `Attempt ${attempt + 1}/${retries} failed: ${lastError.message}`,
        );

        // Check if error is retryable (rate limit, timeout, network error)
        const isRetryable =
          lastError.message.includes("rate limit") ||
          lastError.message.includes("timeout") ||
          lastError.message.includes("network") ||
          lastError.message.includes("ECONNRESET");

        if (!isRetryable || attempt === retries - 1) {
          // Don't retry on non-retryable errors or last attempt
          break;
        }

        // Exponential backoff: 1s, 2s, 4s, 8s...
        const backoffMs = Math.pow(2, attempt) * 1000;
        this.logger.log(`Retrying in ${backoffMs}ms...`);
        await this.sleep(backoffMs);
      }
    }

    // All retries exhausted
    this.logger.error({
      message: "LLM request failed after all retries",
      model,
      provider,
      error: lastError?.message,
    });

    throw new Error(
      `LLM request failed after ${retries} attempts: ${lastError?.message}`,
    );
  }
}
