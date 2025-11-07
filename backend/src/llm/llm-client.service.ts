import { Injectable, Logger } from "@nestjs/common";
import { ConfigService } from "@nestjs/config";
import { streamObject, NoObjectGeneratedError, LanguageModelUsage } from "ai";
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
   * Send prompt to LLM and get structured response with streaming and array support.
   * Uses streamObject to handle partial results, which is crucial for avoiding
   * "SyntaxError: Unexpected end of JSON input" errors that occur when the LLM
   * response is truncated or incomplete. With array streaming, we can process
   * valid array elements even if the JSON is incomplete.
   *
   * @param prompt - The prompt to send to the LLM
   * @param schema - Zod schema for response validation (should have an array field)
   * @param options - Completion options
   * @returns LLMResponse with data and metadata, isPartial=true if incomplete
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
      timeout = 10 * 60000,
    } = options;

    this.logger.log(
      `Prompt is ${prompt.length.toLocaleString("en")} chars, so ~${Math.round(prompt.length * 0.3).toLocaleString("en")} tokens.`,
    );

    let lastError: Error | null = null;

    // Retry loop with exponential backoff
    for (let attempt = 0; attempt < retries; attempt++) {
      // Track collected elements and timing at attempt level for error handlers
      const collectedElements: unknown[] = [];
      let elementCount = 0;
      const startTime = Date.now();

      try {
        this.logger.log(
          `Attempt ${attempt + 1}/${retries} - Calling ${provider} model ${model}`,
        );

        const llmClient = this.getProviderClient(provider, model);

        // Use streamObject with elementStream for array streaming
        // According to AI SDK docs: https://ai-sdk.dev/docs/reference/ai-sdk-core/stream-object#streamobject
        // elementStream allows processing array elements as they arrive, even if JSON is incomplete
        const result = streamObject({
          model: llmClient,
          schema,
          prompt,
          temperature,
          output: "array",
          maxOutputTokens: maxTokens,
        });

        // Track timeout with reset on each streaming update
        let timeoutHandle: NodeJS.Timeout | null = null;
        let streamTimeoutError: Error | null = null;

        const resetTimeout = () => {
          if (timeoutHandle) {
            clearTimeout(timeoutHandle);
          }
          timeoutHandle = setTimeout(() => {
            streamTimeoutError = new Error(
              "Request timeout - no streaming updates",
            );
          }, timeout);
        };

        resetTimeout();

        try {
          // Use elementStream to collect array elements as they arrive
          // This is the key feature for handling incomplete JSON - we get valid
          // elements even if the response is truncated mid-array
          this.logger.debug("Starting to consume elementStream");

          for await (const element of result.elementStream) {
            collectedElements.push(element);
            elementCount++;
            this.logger.debug(
              `Received element ${elementCount}: ${JSON.stringify(element).substring(0, 100)}`,
            );
            resetTimeout();
          }

          this.logger.debug(
            `Finished consuming elementStream, collected ${elementCount} elements`,
          );

          if (timeoutHandle) {
            clearTimeout(timeoutHandle);
          }

          // Check if timeout occurred during streaming
          // TODO: Fix. This doesn't make sense.
          if (streamTimeoutError) {
            // throw streamTimeoutError;
            this.logger.error("Stream timeout error");
          }

          // Get final results
          const finalObject = (await result.object) as T;
          const finalUsage = await result.usage;
          const finishReason = (await result.finishReason) || "unknown";
          const duration = Date.now() - startTime;

          this.logger.log(
            `LLM completed successfully in ${duration}ms (finish: ${finishReason}, elements: ${elementCount})`,
          );

          return {
            data: finalObject,
            usage: finalUsage,
            model,
            finishReason,
            provider,
            duration,
            isPartial: false,
          };
        } catch (streamingError: unknown) {
          if (timeoutHandle) {
            clearTimeout(timeoutHandle);
          }

          const duration = Date.now() - startTime;
          const errorMessage =
            streamingError instanceof Error
              ? streamingError.message
              : String(streamingError);
          const errorName =
            streamingError instanceof Error
              ? streamingError.constructor.name
              : "Unknown";
          const errorStack =
            streamingError instanceof Error ? streamingError.stack : undefined;

          // Log detailed streaming error information
          this.logger.error({
            message: "Streaming error occurred",
            errorType: errorName,
            errorMessage,
            stack: errorStack,
            elementsCollected: collectedElements.length,
            duration,
            model,
            provider,
            attempt: attempt + 1,
            retries,
          });

          // Check if we have partial array elements we can salvage
          // This handles cases like "SyntaxError: Unexpected end of JSON input"
          // where the JSON is incomplete but we collected valid array elements via elementStream
          if (collectedElements.length > 0) {
            this.logger.warn({
              message: "Returning partial results despite streaming error",
              errorType: errorName,
              errorMessage,
              elementsCollected: collectedElements.length,
              duration,
            });

            // Get whatever usage info we can
            let partialUsage: LanguageModelUsage | undefined;
            let partialFinishReason = "error";
            try {
              partialUsage = await result.usage;
              partialFinishReason = (await result.finishReason) || "error";
            } catch (usageError) {
              this.logger.debug(
                `Could not retrieve usage info: ${usageError instanceof Error ? usageError.message : String(usageError)}`,
              );
              partialUsage = {
                inputTokens: undefined,
                outputTokens: undefined,
                totalTokens: undefined,
              };
            }

            // Return collected elements directly as the schema is an array
            const partialObject = collectedElements as T;

            return {
              data: partialObject,
              usage: partialUsage,
              model,
              finishReason: partialFinishReason,
              provider,
              duration,
              isPartial: true, // Signal to caller that results are incomplete
            };
          }

          // No partial results available, log and throw the error
          this.logger.error({
            message:
              "No partial results available, streaming failed completely",
            errorType: errorName,
            errorMessage,
            duration,
          });

          throw streamingError;
        }
      } catch (error) {
        lastError = error as Error;

        // Handle NoObjectGeneratedError specifically
        // This occurs when the model fails to generate valid structured output
        if (error instanceof NoObjectGeneratedError) {
          const hasPartialElements = collectedElements.length > 0;

          this.logger.error({
            message:
              "NoObjectGeneratedError - LLM failed to generate a valid object",
            errorType: "NoObjectGeneratedError",
            attempt: attempt + 1,
            retries,
            model,
            provider,
            finishReason: error.finishReason,
            responseText: error.text?.substring(0, 1000) || "none",
            responseTextLength: error.text?.length || 0,
            cause: error.cause,
            usage: error.usage,
            stack: error.stack,
            elementsCollectedViaStream: collectedElements.length,
            hasPartialElements,
          });

          // If we collected elements via elementStream, return them as partial results
          if (hasPartialElements) {
            this.logger.warn({
              message:
                "Returning partial results from elementStream despite NoObjectGeneratedError",
              elementsCollected: collectedElements.length,
              finishReason: error.finishReason,
            });

            const duration = Date.now() - startTime;
            return {
              data: collectedElements as T,
              usage: error.usage || {
                inputTokens: undefined,
                outputTokens: undefined,
                totalTokens: undefined,
              },
              model,
              finishReason: error.finishReason || "error",
              provider,
              duration,
              isPartial: true,
            };
          }

          // Provide detailed error message
          const detailedMessage = [
            `NoObjectGeneratedError: LLM failed to generate valid structured output.`,
            `Finish reason: ${error.finishReason}`,
            `Response text length: ${error.text?.length || 0} chars`,
            `Response preview: ${error.text?.substring(0, 500) || "none"}`,
            `Cause: ${error.cause ? JSON.stringify(error.cause) : "unknown"}`,
            `Elements collected via stream: ${collectedElements.length}`,
            `This usually indicates:`,
            `  - Content filtering/safety blocks (finish: stop, content_filter)`,
            `  - Token limit reached (finish: length) - increase maxTokens`,
            `  - Model failed to follow schema constraints`,
            `  - Response was empty or malformed`,
            `  - Schema validation failed`,
          ].join("\n");

          throw new Error(detailedMessage);
        }

        // Log general error with full context
        this.logger.warn({
          message: "LLM request attempt failed",
          errorType: lastError.constructor.name,
          errorMessage: lastError.message,
          stack: lastError.stack,
          attempt: attempt + 1,
          retries,
          model,
          provider,
        });

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

    // All retries exhausted - provide comprehensive error information
    this.logger.error({
      message: "LLM request failed after all retries",
      errorType: lastError?.constructor.name || "Unknown",
      errorMessage: lastError?.message || "Unknown error",
      stack: lastError?.stack,
      model,
      provider,
      temperature,
      maxTokens,
      retries,
      promptLength: prompt.length,
      promptPreview: prompt.substring(0, 200),
    });

    throw new Error(
      `LLM request failed after ${retries} attempts.\n` +
        `Error: ${lastError?.message || "Unknown error"}\n` +
        `Model: ${provider}/${model}\n` +
        `Prompt length: ${prompt.length} chars`,
    );
  }
}
