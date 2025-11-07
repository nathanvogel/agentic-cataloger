import { Injectable, Logger } from "@nestjs/common";
import { ConfigService } from "@nestjs/config";
import {
  streamObject,
  generateObject,
  LanguageModelUsage,
  NoObjectGeneratedError,
} from "ai";
import { createOpenAI } from "@ai-sdk/openai";
import { createAnthropic } from "@ai-sdk/anthropic";
import { createGoogleGenerativeAI } from "@ai-sdk/google";
import { z } from "zod";
import {
  ILLMClient,
  CompletionOptions,
  LLMResponse,
  LLMProvider,
} from "./interfaces/llm-client.interface";

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
        throw new Error(`Unsupported provider: ${String(provider)}`);
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
  async generateObject<T>(
    prompt: string,
    schema: z.ZodSchema<T>,
    options: CompletionOptions,
  ): Promise<LLMResponse<T>> {
    const {
      provider,
      model,
      temperature,
      maxTokens,
      retries = 3,
      timeout = 5 * 60000,
      stream = true, // Default to streaming for better timeout handling
    } = options;

    this.logger.log(
      `Prompt is ${prompt.length.toLocaleString("en")} chars, so ~${Math.round(prompt.length * 0.3).toLocaleString("en")} tokens.`,
    );

    let lastError: Error | null = null;

    // Retry loop with exponential backoff
    for (let attempt = 0; attempt < retries; attempt++) {
      try {
        this.logger.log(
          `Attempt ${attempt + 1}/${retries} - Calling ${provider} model ${model}`,
        );

        const startTime = Date.now();
        const llmClient = this.getProviderClient(provider, model);

        let finalObject: T;
        let finalUsage: LanguageModelUsage;
        let finishReason: string;

        if (stream) {
          // Use streaming for better timeout handling
          try {
            const result = streamObject({
              model: llmClient,
              schema,
              prompt,
              temperature,
              maxTokens,
            });

            // Create a timeout that resets on each streaming update
            let timeoutHandle: NodeJS.Timeout | null = null;
            const resetTimeout = () => {
              if (timeoutHandle) {
                clearTimeout(timeoutHandle);
              }
              timeoutHandle = setTimeout(() => {
                throw new Error(
                  "Request timeout - no streaming updates received",
                );
              }, timeout);
            };

            // Start the initial timeout
            resetTimeout();

            // Process streaming updates and reset timeout on each one
            // eslint-disable-next-line @typescript-eslint/no-unused-vars
            for await (const _partialObject of result.partialObjectStream) {
              resetTimeout(); // Reset timeout on each update
            }

            // Clear the timeout once streaming is complete
            if (timeoutHandle) {
              clearTimeout(timeoutHandle);
            }

            // Get final results
            finalObject = (await result.object) as T;
            finalUsage = await result.usage;
            finishReason = (await result.finishReason) || "unknown";
          } catch (streamingError: unknown) {
            // If streaming fails, fall back to non-streaming
            const errorMessage =
              streamingError instanceof Error
                ? streamingError.message
                : String(streamingError);
            this.logger.warn(
              `Streaming failed, falling back to non-streaming: ${errorMessage}`,
            );

            const timeoutPromise: Promise<never> = new Promise((_, reject) => {
              setTimeout(() => reject(new Error("Request timeout")), timeout);
            });

            const nonStreamingPromise = generateObject({
              model: llmClient,
              schema,
              prompt,
              temperature,
              maxTokens,
            });

            const fallbackResult = await Promise.race([
              nonStreamingPromise,
              timeoutPromise,
            ]);
            finalObject = fallbackResult.object;
            finalUsage = fallbackResult.usage;
            finishReason = fallbackResult.finishReason;
          }
        } else {
          // Use non-streaming mode
          const timeoutPromise: Promise<never> = new Promise((_, reject) => {
            setTimeout(() => reject(new Error("Request timeout")), timeout);
          });

          const nonStreamingPromise = generateObject({
            model: llmClient,
            schema,
            prompt,
            temperature,
            maxTokens,
          });

          const result = await Promise.race([
            nonStreamingPromise,
            timeoutPromise,
          ]);
          finalObject = result.object;
          finalUsage = result.usage;
          finishReason = result.finishReason;
        }

        const duration = Date.now() - startTime;

        return {
          data: finalObject,
          usage: finalUsage,
          model,
          finishReason: finishReason || "unknown",
          provider,
          duration,
        };
      } catch (error) {
        lastError = error as Error;

        // Handle NoObjectGeneratedError specifically
        if (error instanceof NoObjectGeneratedError) {
          this.logger.error({
            message: "LLM failed to generate a valid object",
            attempt: attempt + 1,
            retries,
            text: error.text,
            cause: error.cause,
            finishReason: error.finishReason,
            usage: error.usage,
          });

          // NoObjectGeneratedError is typically not retryable - it means the model
          // couldn't generate valid JSON or the response was filtered/blocked
          // Log detailed info and fail fast
          throw new Error(
            `LLM failed to generate valid object. Finish reason: ${error.finishReason}. ` +
              `Response text: ${error.text?.substring(0, 500) || "none"}. ` +
              `This usually indicates the model failed to generate a response, or it generated a response that could not be parsed or not be validated against the schema.
`,
          );
        }

        this.logger.warn(
          `Attempt ${attempt + 1}/${retries} failed: ${lastError.message}`,
        );

        // Check if error is retryable
        const isRetryable =
          lastError.message.includes("rate limit") ||
          lastError.message.includes("timeout") ||
          lastError.message.includes("network") ||
          lastError.message.includes("ECONNRESET");

        if (!isRetryable || attempt === retries - 1) {
          break;
        }

        // Exponential backoff
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
