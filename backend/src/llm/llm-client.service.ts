import { Injectable, Logger } from "@nestjs/common";
import { ConfigService } from "@nestjs/config";
import {
  streamObject,
  NoObjectGeneratedError,
  LanguageModelUsage,
  StreamObjectResult,
  AsyncIterableStream,
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
  async generateArray<T>(
    prompt: string,
    schema: z.ZodSchema<T>,
    options: CompletionOptions,
  ): Promise<LLMResponse<T[]>> {
    const {
      provider,
      model,
      temperature,
      maxTokens,
      retries = 3,
      // timeout = 10 * 60000,
    } = options;

    this.logger.log(
      `Prompt is ${prompt.length.toLocaleString("en")} chars, so ~${Math.round(prompt.length * 0.3).toLocaleString("en")} tokens.`,
    );

    let lastError: Error | null = null;
    let detailedErrorMessage: string | undefined;
    const llmClient = this.getProviderClient(provider, model);

    // Retry loop with exponential backoff
    for (let attempt = 1; attempt <= retries; attempt++) {
      // Track collected elements and timing at attempt level for error handlers
      const collectedElements: T[] = [];
      let result:
        | StreamObjectResult<T[], T[], AsyncIterableStream<T>>
        | undefined;
      const startTime = Date.now();
      this.logger.log(
        `Attempt ${attempt}/${retries} - Calling ${provider} model ${model}`,
      );

      try {
        // Use streamObject with elementStream for array streaming
        // According to AI SDK docs: https://ai-sdk.dev/docs/reference/ai-sdk-core/stream-object#streamobject
        // elementStream allows processing array elements as they arrive, even if JSON is incomplete
        result = streamObject({
          model: llmClient,
          schema,
          prompt,
          temperature,
          output: "array",
          maxOutputTokens: maxTokens,
        });

        // Use elementStream to collect array elements as they arrive
        // This is the key feature for handling incomplete JSON - we get valid
        // elements even if the response is truncated mid-array
        this.logger.debug("Starting to consume elementStream");

        for await (const element of result.elementStream) {
          collectedElements.push(element);
          this.logger.debug(
            `Received element ${collectedElements.length}: ${JSON.stringify(element).substring(0, 100)}`,
          );
        }

        this.logger.debug(
          `Finished consuming elementStream, collected ${collectedElements.length} elements`,
        );

        // Get final results
        const finalObject = await result.object;
        const finalUsage = await result.usage;
        const finishReason = (await result.finishReason) || "unknown";
        const duration = Date.now() - startTime;

        this.logger.log(
          `LLM completed successfully in ${duration}ms (finish: ${finishReason}, elements: ${collectedElements.length})`,
        );

        // Success path return
        return {
          data: finalObject,
          usage: finalUsage,
          model,
          finishReason,
          provider,
          duration,
          isPartial: false,
        };
      } catch (error) {
        const duration = Date.now() - startTime;
        const errorMessage =
          error instanceof Error ? error.message : String(error);
        const errorName =
          error instanceof Error ? error.constructor.name : "Unknown";
        const errorStack = error instanceof Error ? error.stack : undefined;
        if (error instanceof Error) {
          lastError = error;
        }

        // Log detailed streaming error information
        this.logger.error({
          message: "Error during array generation",
          errorType: errorName,
          errorMessage,
          stack: errorStack,
          error: JSON.stringify(error, null, 2),
          elementsCollected: collectedElements.length,
          duration,
          model,
          provider,
          attempt,
          retries,
        });

        // Check if we have partial array elements we can salvage
        // This handles cases like "SyntaxError: Unexpected end of JSON input"
        // where the JSON is incomplete but we collected valid array elements via elementStream
        if (collectedElements.length > 0) {
          this.logger.warn("Returning partial results despite streaming error");

          // Get whatever usage info we can
          let partialUsage: LanguageModelUsage = {
            inputTokens: undefined,
            outputTokens: undefined,
            totalTokens: undefined,
          };
          let partialFinishReason = "error";
          if (result) {
            try {
              partialUsage = await result.usage;
              partialFinishReason = (await result.finishReason) || "error";
            } catch (usageError) {
              this.logger.debug(
                `Could not retrieve usage info: ${usageError instanceof Error ? usageError.message : String(usageError)}`,
              );
            }
          }

          // Partial success path return
          return {
            data: collectedElements,
            usage: partialUsage,
            finishReason: partialFinishReason,
            model,
            provider,
            duration,
            isPartial: true,
          };
        } else {
          // No partial results available, log and throw the error
          this.logger.error(
            "No partial results available, streaming failed completely",
          );
        }

        // Handle NoObjectGeneratedError specifically
        // This occurs when the model fails to generate valid structured output
        if (error instanceof NoObjectGeneratedError) {
          // Provide detailed error message
          detailedErrorMessage = [
            `NoObjectGeneratedError: LLM failed to generate valid structured output.`,
            `Finish reason: ${error.finishReason}`,
            `Response text length: ${error.text?.length || 0} chars`,
            `Response preview: ${error.text?.substring(0, 500) || "none"}`,
            `Cause: ${error.cause ? JSON.stringify(error.cause) : "unknown"}`,
            `Usage: ${JSON.stringify(error.usage)}`,
            `Elements collected via stream: ${collectedElements.length}`,
            `This usually indicates:`,
            `  - Token limit reached (finish: length) - increase maxTokens`,
            `  - Model failed to follow schema constraints`,
            `  - Response was empty or malformed`,
            `  - Schema validation failed`,
            `  - Content filtering/safety blocks (finish: stop, content_filter)`,
          ].join("\n");
          this.logger.error({
            message:
              "NoObjectGeneratedError - LLM failed to generate a valid object",
            errorType: "NoObjectGeneratedError",
            detailedErrorMessage,
          });
        }

        // Check if error is retryable
        const isRetryable =
          error instanceof Error &&
          (error.message.includes("rate limit") ||
            error.message.includes("timeout") ||
            error.message.includes("network") ||
            error.message.includes("ECONNRESET"));
        if (!isRetryable || attempt === retries) {
          break;
        }
        // Exponential backoff
        const backoffMs = Math.pow(2, attempt + 1) * 1000;
        this.logger.log(`Retrying in ${backoffMs}ms...`);
        await this.sleep(backoffMs);
      }
    }

    this.logger.debug("LLM request failed after all retries");

    throw new Error(
      `LLM request failed after ${retries} attempts.\n` +
        `Error: ${lastError?.message || "Unknown error"}\n` +
        `Error details: ${detailedErrorMessage}\n` +
        `Model: ${provider}/${model}\n`,
    );
  }
}
