# Decision Record: Selection of Vercel AI SDK for LLM Integration

- **Status:** Accepted
- **Decision Makers:** Nathan Vogel
- **Date:** 2025-11-05
- **Related Decision Records (Optional):** N/A

## Context

The project requires integration with Large Language Models (LLMs) to power a product categorization system. The primary technical requirement for the MVP is to invoke LLMs and receive reliable, structured (JSON) output for further processing within the Nest.js backend.

The key constraints and forces influencing this decision are:

- **Team Composition:** The team is a solo developer with strong TypeScript expertise.
- **Project Goal:** The immediate goal is to deliver an MVP as quickly as possible.
- **Technical Stack:** The stack is TypeScript-only (Nest.js, PostgreSQL), self-hosted, with no current or planned Python integration.
- **MVP Scope:** The initial scope does not include Retrieval-Augmented Generation (RAG) or complex, autonomous agentic workflows. The focus is on schema-enforced structured data extraction.
- **Prior Research:** A detailed research report, "An Architectural Analysis of TypeScript-Native LLM Frameworks," was conducted to evaluate options.

## Decision

We will adopt the **Vercel AI SDK** as the primary library for LLM integration in the project.

Specifically, we will leverage its `generateObject` function, which integrates with `zod` for schema validation, to handle all calls to LLMs that require structured data as a response. This choice aligns with the "Lightweight Toolkit" architectural pattern identified in the research report, prioritizing simplicity and development speed.

## Consequences

- **Positive:**

  - **Accelerated Development:** The Vercel AI SDK's simple, function-call-based API (`generateObject`) is extremely straightforward, minimizing the learning curve and enabling rapid implementation of the core requirement.
  - **Excellent Developer Experience (DX):** As a "TypeScript-Native" library, its design feels clean and idiomatic within our Nest.js codebase, avoiding the cumbersome abstractions of Python-ported alternatives.
  - **Focused & Decoupled:** The SDK is a utility, not a monolithic framework. It integrates easily into our existing Nest.js service architecture without imposing its own structure.
  - **Sufficient for MVP:** It directly and effectively addresses the main requirement of schema-enforced structured output.

- **Neutral:**

  - The Vercel AI SDK is framework-agnostic and not tied to Vercel hosting. It works perfectly within our self-hosted Docker environment.

- **Negative:**
  - **Lacks Advanced Retries:** Unlike alternatives like `instructor-js`, the SDK does not have a built-in, sophisticated validation-feedback retry loop. This may require custom error handling for production hardening in the future.
  - **Limited Agentic Primitives:** The SDK is not a comprehensive agent framework. If future requirements demand complex, multi-step agentic workflows, we may need to introduce another library or build significant custom logic. This is an acceptable trade-off for MVP speed.

## Alternatives Considered

- **LangChain.js:** Rejected. While mature and well-documented for the Nest.js stack, it was deemed overly complex and "bloated" for the simple structured output requirement of the MVP.
- **Mastra:** Rejected. Although it offers a superior TS-native DX for complex agentic workflows, it is an "all-in-one" framework that would introduce unnecessary complexity for an MVP that does not require its core features.
- **LlamaIndexTS:** Rejected. The research report identified a critical production risk regarding its pgvector data incompatibility with its Python counterpart. Furthermore, the MVP does not have a RAG requirement, which is its core strength.
- **`instructor-js`:** A very strong contender due to its superior reliability with validation-feedback retry loops. However, for the initial MVP, the slightly simpler API of the Vercel AI SDK was preferred for maximum development speed. It remains a viable option to switch to if response validation becomes a significant issue post-MVP. However, the latest development activity on its github main branch is from 10 months ago.

## References

- [Research Report: An Architectural Analysis of TypeScript-Native LLM Frameworks](../reports/2025-11-05-llm-ts-librairies.md)
- [Requirements: Product Categorization System](../../.kiro/specs/product-categorization-system/requirements.md)
- [Vercel AI SDK Documentation](https://ai-sdk.dev/)
