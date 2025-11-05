# Research Report: An Architectural Analysis of TypeScript-Native LLM Frameworks for Production Nest.js Applications

**Author(s):** Gemini 2.5 Pro Deep Research, Nathan Vogel

**Date:** 2025-11-05

## **1\. Executive Summary: Architect's Recommendation for the Nest.js AI Stack**

This report provides a comprehensive architectural analysis to determine the optimal library selection for the specified technical stack: a TypeScript-only, self-hosted (VPS, Docker) Nest.js backend utilizing a PostgreSQL database. The analysis of the query and the target stack indicates that the "best library" is not a single choice but rather the selection of an _architectural pattern_.  
The investigation has identified three distinct patterns for integrating AI capabilities into this stack:

1. **The "All-in-One Framework"**: Committing to a single, comprehensive framework to manage all AI tasks. This path presents a choice between:
   - **1a. LangChain.js**: Prioritizing maturity and the most extensive integration documentation.
   - **1b. Mastra**: Prioritizing a TypeScript-native developer experience (DX) and modern agent/workflow design.
2. **The "Specialized Stack"**: Composing "best-in-class" libraries for different tasks (e.g., LlamaIndexTS for RAG, Vercel AI SDK for output).
3. **The "Lightweight Toolkit"**: Bypassing monolithic frameworks in favor of minimal, focused tools (instructor-js, pgvector-node) and building core logic idiomatically within Nest.js services.

**Key Findings & Recommendations:**

- **Pattern 2 (Specialized Stack) is NOT Recommended.** The analysis uncovered a critical production risk: the LlamaIndexTS PGVectorStore is explicitly documented as **incompatible** with data indexed by its Python counterpart.1 This creates data silos, breaks polyglot development workflows, and signals that the library is not a first-class, interoperable citizen.
- **Pattern 3 (Lightweight Toolkit) is the Architecturally Superior Choice.** For a senior team building a production-grade, self-hosted system, this pattern offers maximum control, performance, transparency, and long-term maintainability. It aligns perfectly with the Nest.js dependency-injection philosophy and avoids framework "magic."
- **Pattern 1 (All-in-One) is the Pragmatic Choice for Speed.**
  - For teams prioritizing a **TypeScript-native developer experience** above all else, **Mastra (Pattern 1b)** is the recommended "all-in-one" framework. Its workflow syntax is built for JavaScript developers and its architecture is cohesive.3
  - For teams prioritizing **minimal risk and mature, pre-existing integration guides**, **LangChain.js (Pattern 1a)** offers the most-documented path. There are multiple public-facing tutorials for its _exact_ integration with Nest.js and pgvector.5

## **2\. Deconstructing the Technical Challenge: A Triad of Capabilities**

The user's project requirements, as implied by the library list and technology stack, can be deconstructed into three distinct, though interrelated, technical capabilities.

### **2.1. Capability 1: Retrieval-Augmented Generation (RAG)**

The core requirement of the project is to connect Large Language Models (LLMs) to a private data source. The stack combination of Nest.js \+ PostgreSQL \+ Docker is the classic signature of a self-hosted RAG API.5 The PostgreSQL database will, by necessity, leverage the pgvector extension for efficient vector similarity search.8 The libraries LlamaIndexTS and Mastra are both explicitly designed to address this RAG use case.10

### **2.2. Capability 2: Reliable Structured Data Output**

The inclusion of instructor-js 12 and the vercel/ai SDK (specifically its generateObject function) 13 highlights a critical production-grade requirement: forcing unstructured LLM outputs into reliable, type-safe, and predictable JSON schemas. In a TypeScript environment, this is synonymous with zod validation.12 This capability is essential for building robust API endpoints that can be reliably consumed by other services or frontends.

### **2.3. Capability 3: Agentic Workflow Orchestration**

The presence of Mastra 16 and LlamaIndexTS 10 signals a desire to move beyond simple request-response RAG. These frameworks provide tools to build autonomous agents: multi-step, tool-using systems that can reason, execute complex tasks, and manage their own memory.

### **2.4. The Fragmented TypeScript AI Ecosystem: "Python-Ports" vs. "TypeScript-Natives"**

The user's selection of libraries is not redundant; it is a symptom of a deep fragmentation in the TypeScript AI market. The research indicates a clear schism between two "philosophies" of AI libraries:

1. **The "Python-Ports" (LangChain.js, LlamaIndexTS):** These libraries are immensely powerful, mature, and feature-rich, stemming from their dominant Python originals. However, they are frequently criticized by the TypeScript community for feeling like second-class citizens. They are often described as "less developed than their python versions" 18, "cumbersome" 3, and built on "too many abstractions" that feel alien to a TypeScript developer.19
2. **The "TypeScript-Natives" (Mastra, Vercel AI SDK, instructor-js):** These libraries were built from the ground up for TypeScript.12 They are consistently praised for a developer experience that is "smoother" 3, "cleaner" 19, and "refreshingly straightforward".23

This report's central analysis navigates this schism. The decision is not merely about features but about architectural philosophy: committing to a mature-but-clunky, Python-first ecosystem or embracing a sleek-but-less-proven, TS-native one.

### **Table 1: Framework & Tool Capability Matrix**

| Library           | Primary Paradigm                       | Core Strength                       | pgvector Support    | Nest.js Integration |
| :---------------- | :------------------------------------- | :---------------------------------- | :------------------ | :------------------ |
| **LangChain.js**  | All-in-One Framework (Python-Port)     | Maturity, Ecosystem & Integrations  | Yes (Mature)        | Proven (Community)  |
| **LlamaIndexTS**  | RAG-Specialist Framework (Python-Port) | Advanced RAG Techniques \[10\]      | **Yes (High-Risk)** | Generic Node.js     |
| **Mastra**        | All-in-One Framework (TS-Native)       | Agent/Workflow DX 3                 | Yes (Cohesive)      | Generic Node.js     |
| **Vercel AI SDK** | Utility SDK (TS-Native)                | Unified API, UI Hooks, Decoupled 13 | N/A                 | N/A (Utility)       |
| **instructor-js** | Specialist Tool (TS-Native)            | Zod-Validation & Retries 12         | N/A                 | N/A (Utility)       |

## **3\. Part I: The Core Capability — RAG with Nest.js & pgvector**

This is the most critical component of the stack. The analysis focuses on how each library integrates with pgvector within a self-hosted Nest.js application.

### **3.1. Framework-based RAG: The "All-in-One" Abstractions**

- LangChain.js (@langchain/community):  
  This solution is, by far, the most documented and battle-tested for this specific stack. Multiple, detailed tutorials exist that explicitly walk through building a RAG application using LangChain.js, Nest.js, and pgvector deployed via Docker.5 This alignment is a significant risk-reduction factor. The pgvector adapter is a mature part of the @langchain/community package and supports standard setup procedures.25
- LlamaIndexTS (PGVectorStore):  
  LlamaIndex is purpose-built for RAG and positions itself as the specialist in this domain.10 It provides a PGVectorStore adapter for this purpose.1 However, a critical production red flag was discovered in its documentation. Snippets 1 and 2 both contain the explicit warning: "Note: Can't be used with data created using the Python version...".  
  This is not a minor limitation; it is an architectural deal-breaker.
  1. **The Implication:** It signals that the LlamaIndexTS and llama_index (Python) libraries do not share an interoperable data schema for pgvector.
  2. **The Production Risk:** A common and vital workflow is for a data science team to perform data ingestion, cleansing, and embedding backfills using Python scripts. This warning means that any data indexed by the Python library _cannot be read_ by the Nest.js backend. It creates an impassable data silo within the same project.
  3. **The Signal:** This strongly suggests the TypeScript version is a "second-class citizen" 18 and not a true, interoperable port, making it a high-risk choice for any production, polyglot environment.
- Mastra (@mastra/pg):  
  Mastra provides a clean, unified approach to data persistence. It fully supports pgvector 29 as part of its RAG system.11 Architecturally, its design is elegant: the single @mastra/pg package is used for both vector storage (RAG) and persistent agent memory (e.g., chat history).33 This cohesion reduces dependencies and configuration complexity. The documentation shows a simple, clear constructor for connecting to a PostgreSQL instance.29

### **3.2. The "Unbundled" Stack: Idiomatic Nest.js RAG**

This pattern eschews monolithic AI frameworks in favor of building the RAG pipeline directly, using minimal tools. This approach offers maximum control and is likely the most appealing to a Nest.js-purist architect.

- **The Components:**
  1. **Nest.js DatabaseModule:** This module would be configured to use the standard pg (node-postgres) library.34 Following Nest.js best practices, it would provide the Pool object as an injectable provider.35
  2. **pgvector-node:** A lightweight helper library whose _sole_ purpose is to handle the type conversion between the vector type in PostgreSQL and a JavaScript array.36
  3. **Custom RagService:** A standard Nest.js Injectable service that encapsulates the RAG logic.
- **Implementation Steps:**
  1. **Database Setup:** After installing the pgvector extension via Docker, the database needs to be initialized with CREATE EXTENSION vector; 8 and a table created, e.g., CREATE TABLE items (id serial, embedding vector(1536));.8
  2. **Ingestion:** An addDocument method in RagService would generate an embedding (e.g., using Vercel AI SDK or raw OpenAI) and then execute a standard SQL query: await this.pool.query('INSERT INTO items (embedding) VALUES ($1)',)\]);.36
  3. **Retrieval:** A search method would take a query embedding and execute the core pgvector search: await this.pool.query('SELECT \* FROM items ORDER BY embedding \<-\> $1 LIMIT 5',);. The \<-\> operator is the L2 distance (Euclidean) function, the key to the vector search.36

This "unbundled" stack 37 has zero "magic." The developer has full, transparent control over the SQL, the indexing (e.g., creating HNSW or IVFFlat indexes for performance: CREATE INDEX ON items USING hnsw (embedding vector_l2_ops) 34), and all application logic. For a production system on a VPS, this transparency is invaluable for performance tuning. The trade-off is the need to manually implement document loading and chunking, features that frameworks provide out-of-the-box.39

### **Table 2: pgvector Adapter Technical Comparison**

| Feature                     | LangChain.js (@langchain/community) | LlamaIndexTS (PGVectorStore) | Mastra (@mastra/pg)       | "Unbundled" (pgvector-node) |
| :-------------------------- | :---------------------------------- | :--------------------------- | :------------------------ | :-------------------------- |
| **Python Interoperability** | Yes                                 | **No \- Critical Risk** 1    | Yes (Assumed, direct SQL) | N/A (Direct SQL)            |
| **Underlying Dependency**   | pg                                  | pg (via postgres)            | pg                        | pg                          |
| **Abstraction Level**       | High (VectorStore)                  | High (VectorStore)           | High (VectorStore)        | Low (SQL Helper)            |
| **Advanced Indexing**       | Configurable                        | Unclear from docs            | Configurable              | Full SQL Control 36         |
| **Nest.js Examples**        | **Excellent** 5                     | None                         | Generic Node.js 40        | **Excellent** 35            |

## **4\. Part II: The Reliability Layer — Schema-Enforced Structured Output**

This capability is essential for building reliable API endpoints. The analysis compares the two leading TS-native tools for this purpose.

### **4.1. Specialist Tool: instructor-js**

- **Core Philosophy:** instructor-js operates via "Client Patching".12 It is not an LLM client itself, but a wrapper that "patches" an existing client (like openai) to add powerful structured output capabilities.
- **Key Features:** Its primary value is the deep integration with zod 12 and its built-in **retry logic**. This is not just a simple schema-enforced call; instructor-js is built on the pattern of catching zod validation errors, feeding those errors _back_ to the LLM, and asking it to correct its own output.43 This validation-feedback loop is critical for production reliability.
- **Provider Flexibility:** A major advantage for the self-hosted VPS/Docker stack is its broad provider support. It works seamlessly with local models via Ollama, as well as other providers like TogetherAI and Anyscale.12 This prevents vendor lock-in and allows for cost-effective, self-hosted models.

### **4.2. SDK Utility: Vercel AI SDK (generateObject)**

- **Core Philosophy:** The Vercel AI SDK provides a clean, function-call-based API. It is not a patch, but a standalone toolkit.13
- **Key Features:** The core of the SDK is a set of unified functions: generateText, generateObject, streamText, and streamObject.14 This provides a highly consistent and clean developer experience. It also uses zod for schema validation in generateObject.14
- **Decoupling Insight:** It is critical to understand that the Vercel AI SDK is _not_ tied to Vercel hosting. It is marketed as "The AI Toolkit for TypeScript" and is designed for any Node.js runtime.13 It can be installed (npm install ai) and used within a Nest.js service on a VPS without issue.

### **4.3. Showdown: instructor-js vs. generateObject in a Nest.js Service**

The practical difference is best illustrated by how they would be implemented in an injectable Nest.js service.  
**MyService with instructor-js (The "Patching" Pattern):**

TypeScript

// In my.module.ts  
import { Module } from '@nestjs/common';  
import OpenAI from 'openai';  
import Instructor from '@instructor-ai/instructor';  
import { MyService } from './my.service';

const oai \= new OpenAI({ apiKey: '...' });  
const instructorClient \= Instructor({ client: oai, mode: "TOOLS" });

@Module({  
 providers:,  
 exports:,  
})  
export class MyModule {}

// In my.service.ts  
import { Inject, Injectable } from '@nestjs/common';  
import { z } from 'zod';

const MyZodSchema \= z.object({ name: z.string(), age: z.number() });

@Injectable()  
export class MyService {  
 constructor(@Inject('INSTRUCTOR_CLIENT') private client) {}

async getStructuredData(prompt: string) {  
 // instructor-js uses the \`chat.completions.create\` method  
 // but adds \`response_model\` and \`max_retries\`  
 return this.client.chat.completions.create({  
 messages: \[{ role: "user", content: prompt }\],  
 model: "gpt-4o",  
 response_model: { schema: MyZodSchema, name: "MySchema" },  
 max_retries: 3, // The key reliability feature  
 });  
 }  
}

**MyService with vercel/ai (The "Function Call" Pattern):**

TypeScript

// In my.service.ts  
import { Injectable } from '@nestjs/common';  
import { generateObject } from 'ai';  
import { openai } from '@ai-sdk/openai';  
import { z } from 'zod';

const MyZodSchema \= z.object({ name: z.string(), age: z.number() });

@Injectable()  
export class MyService {  
 async getStructuredData(prompt: string) {  
 // The Vercel SDK provides a simple, standalone function \[45\]  
 const { object } \= await generateObject({  
 model: openai('gpt-4o'),  
 schema: MyZodSchema,  
 prompt: prompt,  
 });  
 return object;  
 }  
}

The vercel/ai example is simpler for a one-shot call. The instructor-js example is more configuration-heavy but exposes deeper, more robust controls like max_retries.

### **Table 3: Structured Output Tool Showdown**

| Feature                 | instructor-js                            | Vercel AI SDK (generateObject)            |
| :---------------------- | :--------------------------------------- | :---------------------------------------- |
| **Integration Method**  | Client Patching 12                       | Function Call 14                          |
| **Key Feature**         | Validation-Retry Loop 43                 | Unified API (Text, Object, Stream) \[45\] |
| **zod Support**         | Yes (Core) 12                            | Yes (Core) \[15\]                         |
| **Non-OpenAI Support**  | **Excellent** (Ollama, Together, etc) 42 | Good (Anthropic, Google, etc) 13          |
| **Nest.js Integration** | Simple (as an injectable provider)       | Simple (as a direct function call)        |

**Conclusion:** instructor-js is the superior _specialist tool_ for robust, self-hosted model validation, especially given its excellent support for local models via Ollama.42 Vercel AI SDK is the superior _general-purpose utility_ for building a consistent AI interaction layer (text, objects, and streaming).

## **5\. Part III: The Orchestration Engine — Agents & Workflows**

This section analyzes the most complex capability: building multi-step agentic systems. The market has largely shifted from unreliable "implicit loops" (where the LLM decides everything) to "explicit graphs" (where the developer defines the workflow structure and the LLM makes decisions at specific nodes).

### **5.1. LangChain.js (LangGraph)**

LangChain's answer to its own "cumbersome" agent system 3 is LangGraph. This module explicitly implements the "explicit graph" paradigm, modeling workflows as a "stateful graph with nodes and conditional edges".46 This is a far more robust and debuggable system for production.47 However, it still carries the full complexity and "Python-first" feel of the LangChain ecosystem.4

### **5.2. Mastra (Workflows)**

This is Mastra's "killer feature" and is central to its design.16 It is praised by TS developers for offering a "much more simple approach to workflows" 3 that is "familiar to JavaScript devs".4 The syntax is explicit, programmatic, and TS-native, using chained methods like .then(), .branch(), and .parallel() to define the graph.16 Mastra is designed as a "cohesive architecture for defining agents, tools, workflows, and memory systems" 4, making it a purpose-built solution for this problem.

### **5.3. Vercel AI SDK (ToolLoopAgent)**

The AI SDK offers a _lightweight_ agent primitive called ToolLoopAgent.13 This is _not_ a full-blown graph framework like LangGraph or Mastra. It is a simple, un-opinionated loop for managing tool calls. This primitive aligns perfectly with the "Lightweight Toolkit" philosophy: it provides the bare-bones structure for tool use 49, but expects the architect to build the complex workflow logic around it, likely within a custom Nest.js service.

### **5.4. Comparative Analysis & Nest.js Integration**

- **Mastra vs. LangChain:** For a TypeScript-native team, Mastra is the clear winner in terms of developer experience for agents.23 LangGraph is more mature, but also more complex and "confusing".3
- **Nest.js Integration Nuance:** This is a critical point. While there are no official @nestjs/mastra guides, Mastra _can_ be used within Nest.js.
  - One Reddit user reports success: "We're using Mastra and it works pretty well".18
  - However, a Mastra GitHub issue 40 includes a statement from the team: "We are not going to do any specific NestJS integration ourselves."
  - This means Mastra (a Node.js framework 51) can be used _inside_ Nest.js (a Node.js framework 52), but it requires manual instantiation and management within a Nest.js provider. This is a standard integration pattern, but not the "zero-config" magic of a first-party module.

## **6\. Part IV: The Integration Blueprint — Assembling the Final Stack**

This section synthesizes all findings into three concrete architectural blueprints for the Nest.js \+ Docker \+ VPS \+ PostgreSQL stack.

### **6.1. Architectural Pattern 1: The "All-in-One Framework"**

- **Option 1a: The "Mature" Path \- Nest.js \+ LangChain.js**
  - **Description:** Use LangChain.js for everything: RAG, structured output (via tool-calling), and agents (LangGraph).5
  - **Pros:** Single AI dependency. Most mature and battle-tested. **Best-in-class documentation for this _exact_ stack** (Nest.js \+ pgvector).5
  - **Cons:** Widely criticized developer experience.3 "Bloated" and "cumbersome." Commits the project to a Python-first ecosystem.18
- **Option 1b: The "TS-Native" Path \- Nest.js \+ Mastra**
  - **Description:** Use Mastra for everything: RAG, structured output (via tools), and workflows.11
  - **Pros:** Superior "TypeScript-first" developer experience.3 Architecturally elegant; cohesive pg module for both memory and vectors.33
  - **Cons:** No official Nest.js integration module 40, requiring manual provider setup. Less mature and battle-tested than LangChain.

### **6.2. Architectural Pattern 2: The "Specialized Stack" (NOT RECOMMENDED)**

- **Description:** Combine LlamaIndexTS (for RAG) \+ Vercel AI SDK (for structured output).
- **Pros:** (Theoretical) "best-in-class" for each individual task.
- **Cons:**
  - **CRITICAL RISK:** The LlamaIndexTS pgvector incompatibility 1 makes this a production non-starter.
  - **High Integration Friction:** Managing two complex, overlapping, and potentially conflicting AI frameworks increases complexity.

### **6.3. Architectural Pattern 3: The "Lightweight Toolkit" (Architect's Choice)**

- **Description:** Do not use an "all-in-one" AI framework. Instead, build all logic _within_ Nest.js using minimal, focused libraries.
- **The Stack:**
  - **Backend:** Nest.js DatabaseModule, RagService, AgentService.35
  - **RAG:** node-postgres \+ pgvector-node. Logic is just raw SQL queries.36
  - **Structured Output:** instructor-js (for robustness and self-hosted model support 12) or Vercel AI SDK (for its clean API 14).
  - **Agents:** Custom logic within AgentService, potentially using Vercel AI SDK's ToolLoopAgent as a primitive.13
- **Pros:**
  - **Maximum Control & Transparency:** No "magic" abstractions. The team owns the code, not the framework.20
  - **Performance:** Zero framework overhead.
  - **Idiomatic Code:** 100% pure, idiomatic, testable Nest.js code that aligns with the framework's dependency-injection philosophy.
  - **Maintainability:** Easier to debug and maintain. No "fighting the framework".20
- **Cons:**
  - **Implementation Burden:** The team must write their own document loaders, chunkers, and agent loops, which frameworks provide out-of-the-box.39 This is a significant time/cost trade-off.

## **7\. Final Technical Recommendation and Implementation Roadmap**

The query reveals a core tension between the maturity of Python-first frameworks (LangChain) and the superior developer experience of TS-native tools (Mastra, instructor-js).  
**The Final Verdict:**

1. **REJECT: The "Specialized Stack" (Pattern 2).** The LlamaIndexTS pgvector incompatibility 1 is a critical production-blocking risk that cannot be justified.
2. RECOMMEND (Architect's Choice): The "Lightweight Toolkit" (Pattern 3).  
   This is the architecturally superior choice for a senior team. The specified stack (Nest.js, Docker, VPS) implies a value on control, reliability, and long-term maintainability. This pattern provides 100% control, aligns with Nest.js idioms 35, and avoids vendor lock-in by supporting local models via tools like instructor-js.42
3. RECOMMEND (Pragmatic Choice): The "All-in-One Framework" (Pattern 1).  
   This is the faster path to market. The choice is a cultural one:
   - If the team values a **TS-native developer experience** and is willing to perform a one-time manual integration, choose **Mastra (Pattern 1b)**.23
   - If the team values **safety and the lowest-risk path**, choose **LangChain.js (Pattern 1a)**. Its "cumbersome" nature 3 may be an acceptable trade-off for the extensive, stack-specific documentation.5

**Implementation Roadmap (for Recommended Pattern 3: Lightweight Toolkit):**

1. **Phase 1: Setup Nest.js \+ pgvector:**
   - Use Docker Compose to launch a pgvector/pgvector:pg16 image.5
   - Create a Nest.js DatabaseModule that provides an injectable Pool from node-postgres, following best practices.35
   - Run CREATE EXTENSION vector; on your database.8
2. **Phase 2: Build the Core RagService:**
   - Create an injectable RagService.41
   - Use pgvector-node for type handling.36
   - Implement addDocument(text):
     1. Generate embedding (see Phase 3).
     2. await this.pool.query('INSERT...',);.36
   - Implement search(queryText):
     1. Generate query embedding.
     2. const results \= await this.pool.query('SELECT... ORDER BY embedding \<-\> $1',);.36
     3. Return results.rows.
3. **Phase 3: Add the LLMService:**
   - Create an EmbeddingService 41 and an LLMService.
   - For structured output (e.g., in AgentService), use instructor-js.12 Instantiate it as a provider (see section 4.3). Its support for self-hosted models 42 is ideal for a VPS setup.
   - For simple text generation or streaming, the Vercel AI SDK (generateText, streamText) provides a clean, unified API.13
4. **Phase 4: Expose via ChatController:**
   - Create a ChatController 24 that injects RagService and LLMService.
   - The controller will orchestrate the basic RAG flow:
     1. Get user query.
     2. Call RagService.search(query).
     3. Build a new prompt with the retrieved context.
     4. Call LLMService.generateText(contextualPrompt).
     5. Return the response.
5. **Phase 5: Add Agents:**
   - Evolve LLMService into an AgentService.
   - Use the Vercel AI SDK's ToolLoopAgent 13 as a lightweight primitive to manage tool-calling logic, while keeping the main workflow control logic within your Nest.js service. This provides the best balance of power and transparency.

#### **Sources des citations**

1. PGVectorStore \- Welcome to LlamaIndex.TS, consulté le novembre 5, 2025, [https://next.ts.llamaindex.ai/docs/api/classes/PGVectorStore](https://next.ts.llamaindex.ai/docs/api/classes/PGVectorStore)
2. PGVectorStore | LlamaIndex TypeScript API Reference, consulté le novembre 5, 2025, [https://developers.llamaindex.ai/typescript/framework-api-reference/classes/pgvectorstore/](https://developers.llamaindex.ai/typescript/framework-api-reference/classes/pgvectorstore/)
3. LangChain or Mastra for a faster TypeScript based AI platform? \- Reddit, consulté le novembre 5, 2025, [https://www.reddit.com/r/LangChain/comments/1nk56kn/langchain_or_mastra_for_a_faster_typescript_based/](https://www.reddit.com/r/LangChain/comments/1nk56kn/langchain_or_mastra_for_a_faster_typescript_based/)
4. Choosing a JavaScript Agent Framework \- Mastra, consulté le novembre 5, 2025, [https://mastra.ai/blog/choosing-a-js-agent-framework](https://mastra.ai/blog/choosing-a-js-agent-framework)
5. LangChain with NestJS (Node framework): Talk with documents part 1 | by Abdullah Irfan, consulté le novembre 5, 2025, [https://medium.com/@abdullahirfan99_80517/langchain-with-nestjs-node-framework-talk-with-documents-part-1-b099a392822e](https://medium.com/@abdullahirfan99_80517/langchain-with-nestjs-node-framework-talk-with-documents-part-1-b099a392822e)
6. Build Agentic RAG application using langchain.js, nestjs, Htmx, and Gemma 2, consulté le novembre 5, 2025, [https://dev.to/railsstudent/build-agentic-rag-application-using-langchainjs-nestjs-htmx-and-gemma-2-3imd](https://dev.to/railsstudent/build-agentic-rag-application-using-langchainjs-nestjs-htmx-and-gemma-2-3imd)
7. Building a Production-Ready RAG System: Zero to Hero with TypeScript, Docker, Google Gemini & LangChain.js \- DEV Community, consulté le novembre 5, 2025, [https://dev.to/glaucia86/building-a-production-ready-rag-system-zero-to-hero-with-typescript-docker-google-gemini--50nh](https://dev.to/glaucia86/building-a-production-ready-rag-system-zero-to-hero-with-typescript-docker-google-gemini--50nh)
8. pgvector/pgvector: Open-source vector similarity search for Postgres \- GitHub, consulté le novembre 5, 2025, [https://github.com/pgvector/pgvector](https://github.com/pgvector/pgvector)
9. Retrieval Augmented Generation (RAG) with pgvector vector database \- Medium, consulté le novembre 5, 2025, [https://medium.com/@yogi_r/retrieval-augmented-generation-rag-with-pgvector-vector-database-0d741e14d62f](https://medium.com/@yogi_r/retrieval-augmented-generation-rag-with-pgvector-vector-database-0d741e14d62f)
10. run-llama/LlamaIndexTS: Data framework for your LLM applications. Focus on server side solution \- GitHub, consulté le novembre 5, 2025, [https://github.com/run-llama/LlamaIndexTS](https://github.com/run-llama/LlamaIndexTS)
11. RAG (Retrieval-Augmented Generation) in Mastra, consulté le novembre 5, 2025, [https://mastra.ai/docs/rag/overview](https://mastra.ai/docs/rag/overview)
12. 567-labs/instructor-js: structured extraction for llms \- GitHub, consulté le novembre 5, 2025, [https://github.com/567-labs/instructor-js](https://github.com/567-labs/instructor-js)
13. vercel/ai: The AI Toolkit for TypeScript. From the creators of Next.js, the AI SDK is a free open-source library for building AI-powered applications and agents \- GitHub, consulté le novembre 5, 2025, [https://github.com/vercel/ai](https://github.com/vercel/ai)
14. AI SDK Core: Generating Structured Data, consulté le novembre 5, 2025, [https://ai-sdk.dev/docs/ai-sdk-core/generating-structured-data](https://ai-sdk.dev/docs/ai-sdk-core/generating-structured-data)
15. AI SDK 5 \- Vercel, consulté le novembre 5, 2025, [https://vercel.com/blog/ai-sdk-5](https://vercel.com/blog/ai-sdk-5)
16. mastra-ai/mastra: The TypeScript AI agent framework ... \- GitHub, consulté le novembre 5, 2025, [https://github.com/mastra-ai/mastra](https://github.com/mastra-ai/mastra)
17. Welcome to LlamaIndex.TS, consulté le novembre 5, 2025, [https://developers.llamaindex.ai/typescript/framework/](https://developers.llamaindex.ai/typescript/framework/)
18. Your experience in using Gen AI SDKs/frameworks with NestJS \- Reddit, consulté le novembre 5, 2025, [https://www.reddit.com/r/Nestjs_framework/comments/1mvoupz/your_experience_in_using_gen_ai_sdksframeworks/](https://www.reddit.com/r/Nestjs_framework/comments/1mvoupz/your_experience_in_using_gen_ai_sdksframeworks/)
19. Comparing Different AI Framework Options for Building Applications \- langchain, consulté le novembre 5, 2025, [https://community.latenode.com/t/comparing-different-ai-framework-options-for-building-applications/39018](https://community.latenode.com/t/comparing-different-ai-framework-options-for-building-applications/39018)
20. Typescript & LLMs: Lessons Learned from 9 Months in Production | by John Childs-Eddy, consulté le novembre 5, 2025, [https://johnchildseddy.medium.com/typescript-llms-lessons-learned-from-9-months-in-production-4910485e3272](https://johnchildseddy.medium.com/typescript-llms-lessons-learned-from-9-months-in-production-4910485e3272)
21. Mastra: The Typescript AI framework, consulté le novembre 5, 2025, [https://mastra.ai/](https://mastra.ai/)
22. AI SDK by Vercel, consulté le novembre 5, 2025, [https://ai-sdk.dev/docs/introduction](https://ai-sdk.dev/docs/introduction)
23. Mastra Agent System Review: A Fresh Take on AI Development | by Justin Rich | Medium, consulté le novembre 5, 2025, [https://justinrich.medium.com/mastra-agent-system-review-a-fresh-take-on-ai-development-04ca3e8e3a1b](https://justinrich.medium.com/mastra-agent-system-review-a-fresh-take-on-ai-development-04ca3e8e3a1b)
24. LangChain with NestJS (Node framework): Basic chat setup | by Abdullah Irfan \- Medium, consulté le novembre 5, 2025, [https://medium.com/@abdullahirfan99_80517/langchain-with-nestjs-node-framework-basic-chat-setup-3296fb91ced0](https://medium.com/@abdullahirfan99_80517/langchain-with-nestjs-node-framework-basic-chat-setup-3296fb91ced0)
25. PGVectorStore \- LangChain.js, consulté le novembre 5, 2025, [https://js.langchain.com/docs/integrations/vectorstores/pgvector/](https://js.langchain.com/docs/integrations/vectorstores/pgvector/)
26. PGVectorStore \- LangChain.js, consulté le novembre 5, 2025, [https://api.js.langchain.com/classes/langchain_community_vectorstores_pgvector.PGVectorStore.html](https://api.js.langchain.com/classes/langchain_community_vectorstores_pgvector.PGVectorStore.html)
27. Llamaindex vs Langchain: What's the difference? \- IBM, consulté le novembre 5, 2025, [https://www.ibm.com/think/topics/llamaindex-vs-langchain](https://www.ibm.com/think/topics/llamaindex-vs-langchain)
28. Vector Stores \- Welcome to LlamaIndex.TS, consulté le novembre 5, 2025, [https://next.ts.llamaindex.ai/docs/llamaindex/modules/data/stores/vector_stores](https://next.ts.llamaindex.ai/docs/llamaindex/modules/data/stores/vector_stores)
29. Reference: PG Vector Store | Vector Databases | Mastra Docs, consulté le novembre 5, 2025, [https://mastra.ai/en/reference/vectors/pg](https://mastra.ai/en/reference/vectors/pg)
30. Storing Embeddings in A Vector Database | RAG | Mastra Docs, consulté le novembre 5, 2025, [https://mastra.ai/docs/rag/vector-databases](https://mastra.ai/docs/rag/vector-databases)
31. Example: Optimizing Information Density | RAG | Mastra Docs, consulté le novembre 5, 2025, [https://mastra.ai/examples/rag/usage/cleanup-rag](https://mastra.ai/examples/rag/usage/cleanup-rag)
32. Example: Optimizing Information Density | RAG | Mastra Docs, consulté le novembre 5, 2025, [https://mastra.ai/en/examples/rag/usage/cleanup-rag](https://mastra.ai/en/examples/rag/usage/cleanup-rag)
33. Example: Memory with PostgreSQL \- Mastra, consulté le novembre 5, 2025, [https://mastra.ai/examples/memory/memory-with-pg](https://mastra.ai/examples/memory/memory-with-pg)
34. pgvector (PostgreSQL Vector Extension) | Genkit \- Firebase \- Google, consulté le novembre 5, 2025, [https://firebase.google.com/docs/genkit/templates/pgvector](https://firebase.google.com/docs/genkit/templates/pgvector)
35. How can I configure postgreSQL in the Nestjs way? \- Stack Overflow, consulté le novembre 5, 2025, [https://stackoverflow.com/questions/74361203/how-can-i-configure-postgresql-in-the-nestjs-way](https://stackoverflow.com/questions/74361203/how-can-i-configure-postgresql-in-the-nestjs-way)
36. pgvector support for Node.js, Deno, and Bun (and TypeScript) \- GitHub, consulté le novembre 5, 2025, [https://github.com/pgvector/pgvector-node](https://github.com/pgvector/pgvector-node)
37. Building an FAQ Search System with Node.js, OpenAI, and pgvector | by Vadim Pryakhin, consulté le novembre 5, 2025, [https://medium.com/@lostargon/building-an-faq-search-system-with-node-js-openai-and-pgvector-e426e71b2c7f](https://medium.com/@lostargon/building-an-faq-search-system-with-node-js-openai-and-pgvector-e426e71b2c7f)
38. Implementing Filtered Semantic Search Using Pgvector and JavaScript | Tiger Data, consulté le novembre 5, 2025, [https://www.tigerdata.com/blog/implementing-filtered-semantic-search-using-pgvector-and-javascript-2](https://www.tigerdata.com/blog/implementing-filtered-semantic-search-using-pgvector-and-javascript-2)
39. Build a Retrieval Augmented Generation (RAG) App: Part 1 \- LangChain.js, consulté le novembre 5, 2025, [https://js.langchain.com/docs/tutorials/rag/](https://js.langchain.com/docs/tutorials/rag/)
40. \[FEATURE\]\[COMMUNITY DRIVEN\] \- Use NestJS to provide services. · Issue \#5081 · mastra-ai/mastra \- GitHub, consulté le novembre 5, 2025, [https://github.com/mastra-ai/mastra/issues/5081](https://github.com/mastra-ai/mastra/issues/5081)
41. Building Vector Search with PostgreSQL and pgvector: A Complete Guide \- Medium, consulté le novembre 5, 2025, [https://medium.com/@author.hlukhaniuk/building-vector-search-with-postgresql-and-pgvector-a-complete-guide-6b7a000cc6b7](https://medium.com/@author.hlukhaniuk/building-vector-search-with-postgresql-and-pgvector-a-complete-guide-6b7a000cc6b7)
42. Structured Output for Open Source and Local LLMS \- Instructor (JS), consulté le novembre 5, 2025, [https://js.useinstructor.com/blog/2024/03/07/open-source-local-structured-output-zod-json-openai/](https://js.useinstructor.com/blog/2024/03/07/open-source-local-structured-output-zod-json-openai/)
43. Self-healing Generate Object Function Call like Instructor · vercel ai · Discussion \#3255, consulté le novembre 5, 2025, [https://github.com/vercel/ai/discussions/3255](https://github.com/vercel/ai/discussions/3255)
44. A Practical Guide to Using Vercel AI SDK in Next.js Applications \- Telerik.com, consulté le novembre 5, 2025, [https://www.telerik.com/blogs/practical-guide-using-vercel-ai-sdk-next-js-applications](https://www.telerik.com/blogs/practical-guide-using-vercel-ai-sdk-next-js-applications)
45. AI SDK \- Vercel, consulté le novembre 5, 2025, [https://vercel.com/docs/ai-sdk](https://vercel.com/docs/ai-sdk)
46. LlamaIndex vs LangChain: Which Framework Is Best for Agentic AI Workflows? \- ZenML, consulté le novembre 5, 2025, [https://www.zenml.io/blog/llamaindex-vs-langchain](https://www.zenml.io/blog/llamaindex-vs-langchain)
47. Comparing Open-Source AI Agent Frameworks \- Langfuse Blog, consulté le novembre 5, 2025, [https://langfuse.com/blog/2025-03-19-ai-agent-comparison](https://langfuse.com/blog/2025-03-19-ai-agent-comparison)
48. LangChain vs. Mastra AI Comparison \- SourceForge, consulté le novembre 5, 2025, [https://sourceforge.net/software/compare/LangChain-vs-Mastra/](https://sourceforge.net/software/compare/LangChain-vs-Mastra/)
49. Building AI Agent Workflows With Vercel's AI SDK: A Practical Guide \- Callstack, consulté le novembre 5, 2025, [https://www.callstack.com/blog/building-ai-agent-workflows-with-vercels-ai-sdk-a-practical-guide](https://www.callstack.com/blog/building-ai-agent-workflows-with-vercels-ai-sdk-a-practical-guide)
50. How to build AI Agents with Vercel and the AI SDK, consulté le novembre 5, 2025, [https://vercel.com/guides/how-to-build-ai-agents-with-vercel-and-the-ai-sdk](https://vercel.com/guides/how-to-build-ai-agents-with-vercel-and-the-ai-sdk)
51. About Mastra | Mastra Docs | Mastra Documentation, consulté le novembre 5, 2025, [https://mastra.ai/docs](https://mastra.ai/docs)
52. nestjs/nest: A progressive Node.js framework for building efficient, scalable, and enterprise-grade server-side applications with TypeScript/JavaScript \- GitHub, consulté le novembre 5, 2025, [https://github.com/nestjs/nest](https://github.com/nestjs/nest)
