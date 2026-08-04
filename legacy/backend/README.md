# Product Categorization Backend

NestJS backend for the LLM-powered product categorization system.

## Features

- **LLM Client Service**: Model-agnostic interface for OpenAI, Anthropic, and Google
  - **Retry Logic**: Exponential backoff for rate limits and transient errors
  - **Structured Output**: Type-safe JSON responses using Zod schemas
  - **Request/Response Logging**: Full logging of LLM interactions
  - **Model Configuration**: Per-operation model defaults with override support

## Installation

```bash
yarn install
```

## Configuration

Copy `.env.example` to `.env` and configure it.

## Usage

### LLM Client Service

The `LLMClientService` provides a model-agnostic interface for LLM interactions:

```typescript
import { LLMClientService, LLMProvider } from "./llm";
import { z } from "zod";

// Define response schema
const CategorySchema = z.object({
  name: z.string(),
  displayName: z.string(),
  productIds: z.array(z.number()),
});

// Call LLM with explicit provider
const response = await llmClient.complete(
  "Categorize these products...",
  CategorySchema,
  {
    provider: LLMProvider.OPENAI,
    model: "gpt-4o",
    temperature: 0.7,
    maxTokens: 4096,
    retries: 3,
    timeout: 60000,
  },
);

console.log(response.data); // Typed as { name: string, displayName: string, productIds: number[] }
console.log(response.usage); // Token usage
console.log(response.provider); // 'openai', 'anthropic', or 'google'
```

### Model Configuration

Override via environment variables or options:

```typescript
import { ModelConfigService, LLMOperation, LLMProvider } from './llm';

// Inject the service
constructor(private modelConfigService: ModelConfigService) {}

// Get default config
const config = this.modelConfigService.getModelConfig(LLMOperation.CATEGORY_DISCOVERY);

// Override with custom provider/model
const customConfig = this.modelConfigService.getModelConfig(
  LLMOperation.CATEGORY_DISCOVERY,
  {
    provider: LLMProvider.GOOGLE,
    model: 'gemini-2.0-flash-exp',
  }
);
```

## Development

```bash
# Build
yarn build

# Run in development mode
yarn start:dev

# Run tests
yarn test

# Run tests in watch mode
yarn test:watch
```

## Architecture

### LLM Module Structure

```
src/llm/
├── interfaces/
│   └── llm-client.interface.ts    # TypeScript interfaces
├── llm-client.service.ts          # Main LLM client implementation
├── llm.module.ts                  # NestJS module
└── index.ts                       # Exports
```
