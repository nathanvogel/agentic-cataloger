---
stepsCompleted: [1]
inputDocuments:
  - _bmad-output/specs/spec-2026-agent-workflow/SPEC.md
  - _bmad-output/specs/spec-2026-agent-workflow/explore-bakeoffs.md
  - _bmad-output/specs/spec-2026-agent-workflow/kill-pile.md
  - _bmad-output/brainstorming/brainstorm-2026-agent-workflow-2026-07-30/morphological-matrix.md
  - docs/specs/2026-scope.md
workflowType: 'research'
lastStep: 1
research_type: 'technical'
research_topic: 'Agent orchestration vendors and inspectability for 2026 workflow bakeoffs'
research_goals: 'Map Python-fit agent frameworks/vendors to O1–O5 and P* explore set; compare inspectability (vendor traces vs custom E4 UI); produce bakeoff-ready shortlist for architecture without pre-picking a winner'
user_name: 'Nathan'
date: '2026-07-31'
web_research_enabled: true
source_verification: true
---

# Research Report: technical

**Date:** 2026-07-31
**Author:** Nathan
**Research Type:** technical

---

## Research Overview

Technical research on agent orchestration vendors/frameworks and inspectability for pricecomp's 2026 agent workflow bakeoffs (O1–O5, P\*, E4). Grounded in SPEC-2026-agent-workflow commitments (Python monolith, staged I9, C2 search, eval harness). No stack winner locked.

---

## Technical Research Scope Confirmation

**Research Topic:** Agent orchestration vendors and inspectability for 2026 workflow bakeoffs
**Research Goals:** Map Python-fit agent frameworks/vendors to O1–O5 and P\* explore set; compare inspectability (vendor traces vs custom E4 UI); produce bakeoff-ready shortlist for architecture without pre-picking a winner

**Technical Research Scope:**

- Architecture Analysis - design patterns, frameworks, system architecture
- Implementation Approaches - development methodologies, coding patterns
- Technology Stack - languages, frameworks, tools, platforms
- Integration Patterns - APIs, protocols, interoperability
- Performance Considerations - scalability, optimization, patterns

**Research Methodology:**

- Current web data with rigorous source verification
- Multi-source validation for critical technical claims
- Confidence level framework for uncertain information
- Comprehensive technical coverage with architecture-specific insights

**Scope Confirmed:** 2026-07-31

---

## Technology Stack Analysis

Scoped to agent orchestration + inspectability for a Python monolith bakeoff (O1–O5 / E4). Broader cloud/DB sections note only what bends this initiative; existing pricecomp Postgres remains assumed.

### Programming Languages

_Popular Languages:_ Python dominates production agent frameworks in 2026 comparisons (LangGraph, PydanticAI, CrewAI, Microsoft Agent Framework Python). TypeScript remains strong for app agents (Cloudflare Agents / Code Mode packages) but conflicts with the locked Python monolith constraint unless Code Mode is treated as an isolated bakeoff sandbox, not the primary backend.
_Emerging Languages:_ Rust/Go appear in observability SDKs and runtimes; not primary agent-authoring languages for this MVP.
_Language Evolution:_ Industry writeups converge on “typed Python backends” (PydanticAI) vs “graph control planes” (LangGraph) as the durable production pair; role-based multi-agent DSLs (CrewAI) stay prototype-heavy.
_Performance Characteristics:_ Framework overhead is secondary to token cost; sources claim PydanticAI often lowest operational overhead for structured I/O; LangGraph favored when state/checkpointing reduces wasted retries. Treat comparative % overhead claims as medium confidence unless re-measured on our eval slice.
_Source:_ https://aitechconnect.in/news/agent-frameworks-langgraph-crewai-pydanticai-microsoft-2026 · https://veprompts.com/reports/agent-frameworks-comparison/ · https://github.com/langchain-ai/langgraph

### Development Frameworks and Libraries

| Candidate | Morph fit | Notes for bakeoff |
| --- | --- | --- |
| **LangGraph** | O4 strong; O1+O5 via tools-in-nodes; HITL primitives | Stateful graph, durable execution, checkpointers; native LangSmith debugging/evals. Official: low-level orchestration for long-running agents. |
| **PydanticAI** | O1 (typed tools); partial O5 via graph extension | Type-safe tools/outputs, FastAPI-like ergonomics; not a full multi-agent orchestrator by default. Pairs with Logfire / OTel. |
| **CrewAI** | Weak for staged I9 eval | Role/crew DSL; fast prototype, higher token overhead in third-party benches; poorer fit for per-stage assign/create/extract eval slices. |
| **Microsoft Agent Framework (ex-AutoGen/SK)** | O1/O4-ish if Azure-aligned | v1.0 GA reported Apr 2026 consolidating AutoGen + Semantic Kernel; enterprise telemetry. Low priority unless Azure lock-in is desired (it is not). |
| **OpenAI Agents SDK** | O1 | Lightweight tool-calling loop; provider-coupled; usable as thin O1 baseline in bakeoff. |
| **Plain Python + structured output** | Baseline control | “No framework” still recommended by several guides for first spike; useful as cost floor vs any O\*. |
| **Cloudflare Code Mode** (`@cloudflare/codemode`) | O3 | Agent writes code against typed connectors; ~1k token fixed catalog vs MCP schema dump; V8 isolate. TS/Cloudflare-centric — bake as pattern (search+execute) even if host differs. |
| **CLI-like tool surface** | O2 | Progressive disclosure via `--help` / thin wrappers; community consensus 2026: CLI for known tools, MCP where auth/remote schema needed; avoid full MCP schema dump (aligns with C2 / kill C5). |

_Major Frameworks:_ LangGraph (control), PydanticAI (typed single-agent), CrewAI (roles), MAF (Microsoft).
_Micro-frameworks:_ OpenAI Agents SDK, smolagents-class tools — good O1 baselines.
_Evolution Trends:_ Split “orchestration graph” from “typed agent runtime”; observability becomes a separate OTel layer rather than framework-owned only.
_Ecosystem Maturity:_ LangGraph + LangSmith deepest for graph traces; PydanticAI + Logfire/OTel strong for Python services; Code Mode / CLI patterns mature as token-control tactics, not full app frameworks.
_Source:_ https://docs.langchain.com/oss/python/langgraph/graph-api · https://pydantic.dev/docs/ai/integrations/logfire/ · https://blog.cloudflare.com/code-mode-mcp/ · https://developers.cloudflare.com/agents/tools/codemode/how-it-works/ · https://agentswarms.fyi/blog/agentic-ai-frameworks-comparison-guide

**O1–O5 mapping (stack → morph, not a winner):**

- **O1 Tool-calling:** PydanticAI, OpenAI Agents SDK, LangGraph tool nodes, MAF agents
- **O2 CLI-like:** Host-local CLIs + skill/help files; MCP→CLI bridges; not a single vendor product
- **O3 Code Mode:** Cloudflare Code Mode pattern (search/describe/execute); Anthropic-style programmatic tool calling analogues
- **O4 LangGraph/state-machine:** LangGraph StateGraph (+ checkpointers)
- **O5 Hybrid graph+tools-in-stage:** LangGraph stages with tools only inside assign/extract nodes (matches SPEC I9)

### Database and Storage Technologies

_Relational Databases:_ Existing PostgreSQL remains the system of record (products, categories, merge upsert D6). LangGraph offers Postgres checkpointers for run state — relevant if O4/O5 needs durable stage state; optional for MVP if runs are short-lived.
_NoSQL / vectors:_ Embedding neighbors (P3/P9/P10) imply a vector index (pgvector or external). Not required to pick in this step; note as bakeoff infra for product supply.
_In-Memory:_ Redis optional for cache-efficiency goal from scope; not required for orchestration bakeoff itself.
_Data Warehousing:_ N/A for MVP agent workflow.
_Source:_ https://atlan.com/know/ai-agent/ai-agent-memory/what-is-langgraph/ (PostgresSaver mention) · project constraint: pricecomp Postgres

### Development Tools and Platforms

_IDE and Editors:_ Irrelevant to vendor pick.
_Version Control / Build:_ Yarn today; Python side likely uv/poetry in monolith migration — out of scope for orchestration bakeoff.
_Testing / Eval harnesses:_ **LangSmith evaluate API** for LangGraph targets; **Pydantic Evals** + Logfire span-based evaluators; **Phoenix** eval-first datasets; **Langfuse** datasets/scores. These are the practical “free inspectability” answers to E4 for MVP.
_Source:_ https://docs.langchain.com/oss/python/langchain/observability · https://pydantic.dev/docs/ai/evals/how-to/logfire-integration/ · https://dreaming.press/posts/langfuse-vs-langsmith-vs-phoenix-observability.html

### Cloud Infrastructure and Deployment

_Major Cloud Providers:_ Not differentiating for local-first Devcontainers MVP; security OOS.
_Container Technologies:_ Devcontainers already constrained in SPEC — frameworks must run in-process or sidecar in Docker Compose (e.g. self-hosted Langfuse/Phoenix).
_Serverless / Edge:_ Cloudflare Agents/Code Mode shine on Workers; adopting that as primary host would fight the Python monolith constraint — treat as **pattern bakeoff**, not hosting decision.
_CDN/Edge:_ N/A.
_Source:_ https://developers.cloudflare.com/agents/tools/codemode/how-it-works/

### Inspectability stack (E4 lean)

| Tool | License / ops | Best when | Framework affinity |
| --- | --- | --- | --- |
| **LangSmith** | Managed (self-host enterprise) | Deepest LangGraph node traces + eval loops | LangGraph/LangChain |
| **Langfuse** | OSS MIT, self-host | Trace-first, cost dashboards, OTel ingest, keep data local | Framework-agnostic |
| **Arize Phoenix** | OSS, OTel/OpenInference | Eval/hallucination-first bakeoffs | Agnostic + notebooks |
| **Pydantic Logfire** | Managed + OTel export | PydanticAI-native agent+DB unified traces | PydanticAI; OTel to others |
| **OpenTelemetry GenAI** | Standard | Instrument once, fan-out to multiple UIs | Cross-cutting spine |

_Confidence:_ High that OTel is the shared spine in 2026 roundups; medium on any single “winner” ranking — pick by constraint (self-host vs managed, graph-depth vs eval-depth).
_Source:_ https://dreaming.press/posts/langfuse-vs-langsmith-vs-phoenix-observability.html · https://josenobile.co/guides/llm-observability/ · https://axiomlogica.com/ai-ml/llm-observability-stack-comparison-langsmith-vs-langfuse-vs-arize-phoenix-2 · https://yanboyang.com/posts/2026-06-24-132210-observability_for_ai_agent_frameworks_comparing_mlflow_langsmith_phoenix_langfuse_braintrust_w_b_weave_and_opentelemetry

### Technology Adoption Trends

_Migration Patterns:_ Prototype on CrewAI/plain loops → production on LangGraph or typed PydanticAI; AutoGen folding into MAF.
_Emerging Technologies:_ Code Mode / progressive tool disclosure to kill MCP catalog bloat; OTel GenAI semantic conventions as default instrumentation.
_Legacy Technology:_ Pure prompt chains (O6 — already kill-piled); full taxonomy/tool schema dumps.
_Community Trends:_ “Orchestration choice moves benchmark scores as much as model choice” (HAL-style claims in secondary sources — re-validate on our golden assign set).
_Source:_ https://blog.cloudflare.com/code-mode-mcp/ · https://www.buildmvpfast.com/blog/mcp-hidden-cost-cli-agent-infrastructure-2026 · secondary architecture writeups citing HAL gaps

### Bakeoff-ready shortlist (no winner)

**Orchestration runners to put on the harness:**

1. Plain Python stages + structured output (control / cost floor)
2. PydanticAI tool-calling stages (O1 typed)
3. LangGraph staged graph (O4 / O5 hybrid)
4. CLI-tool surface for category/product search (O2 tactic, composable with 2–3)
5. Code Mode–style search+execute sandbox for taxonomy/tools (O3 pattern; host TBD)

**Inspectability default recommendation for research (still not architecture lock):** instrument with **OpenTelemetry**; view via **Langfuse or Phoenix self-host** for framework-agnostic bakeoffs; add **LangSmith** only if LangGraph is in the active candidate set; add **Logfire** if PydanticAI is active. Prefer vendor UI over custom E4 until bakeoff proves a gap.

**Deprioritize for this initiative:** CrewAI as primary orchestrator; Microsoft Agent Framework; Cloudflare Workers as primary host.
