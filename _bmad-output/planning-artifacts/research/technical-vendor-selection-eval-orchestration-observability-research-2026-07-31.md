---

## stepsCompleted: [1]
inputDocuments:
  - docs/specs/2026-scope.md
  - _bmad-output/specs/spec-2026-agent-workflow/SPEC.md
  - _bmad-output/specs/spec-2026-agent-workflow/explore-bakeoffs.md
  - _bmad-output/specs/spec-2026-agent-workflow/kill-pile.md
  - _bmad-output/brainstorming/brainstorm-2026-agent-workflow-2026-07-30/morphological-matrix.md
workflowType: "research"
lastStep: 1
research_type: "technical"
research_topic: "Vendor selection for eval sets, agent orchestration, and LLM observability"
research_goals: "Shortlist and compare concrete vendors/tools for (1) golden eval set authoring, storage and scoring, (2) agent orchestration compatible with the O1-O5 bakeoff, and (3) LLM observability with inspectable runs, token-cost-per-item and human feedback capture — for a Python + DDD monolith, without pre-picking an O/P winner."
user_name: "Nathan"
date: "2026-07-31"
web_research_enabled: true
source_verification: true



# Research Report: technical

**Date:** 2026-07-31
**Author:** Nathan
**Research Type:** technical

---



## Research Overview

[Research overview and methodology will be appended here]

---



## Technical Research Scope Confirmation

**Research Topic:** Vendor selection for eval sets, agent orchestration, and LLM observability
**Research Goals:** Shortlist and compare concrete vendors/tools for (1) golden eval set authoring, storage and scoring, (2) agent orchestration compatible with the O1–O5 bakeoff, and (3) LLM observability with inspectable runs, token-cost-per-item and human feedback capture — for a Python + DDD monolith, without pre-picking an O/P winner.

**Technical Research Scope:**

- Architecture Analysis — design patterns, frameworks, system architecture
- Implementation Approaches — development methodologies, coding patterns
- Technology Stack — languages, frameworks, tools, platforms
- Integration Patterns — APIs, protocols, interoperability
- Performance Considerations — scalability, optimization, patterns

**Research Methodology:**

- Current web data with rigorous source verification
- Multi-source validation for critical technical claims
- Confidence level framework for uncertain information
- Comprehensive technical coverage with architecture-specific insights

**Scope decisions taken with the user:**


| Decision                         | Choice                                                                            |
| -------------------------------- | --------------------------------------------------------------------------------- |
| Deployment / cost posture        | Managed SaaS acceptable, modest paid plan OK (~$20–50/mo); self-host also in play |
| Platform breadth                 | Compare both single-platform and best-of-breed shapes, then recommend             |
| Cross-cutting areas in scope     | HITL annotation queue / feedback capture as a candidate H1 surface                |
| Cross-cutting areas out of scope | LLM gateway/caching, model-provider selection, embedding/vector vendor            |
| Portfolio showcase weight        | Nice-to-have — screenshots and exported metrics suffice; not a selection driver   |


**Anchor constraints carried from** `SPEC.md` **into every vendor judgement:**

1. **CAP-10 forbids pre-picking O/P.** For orchestration the question is not "best framework" but "which vendors let O1–O5 run on one harness with comparable traces and cost numbers." A vendor that expresses only one shape well would bias agentic-cataloger's own bakeoff.
2. **E1/E2/E3/E5 are four distinct jobs** — golden assign dataset with versioning, independent per-stage scoring, token-cost-per-item, and a model×strategy comparison matrix.
3. **CAP-9's non-blocking HITL (H1 + H2) may already be a vendor feature**, which would remove the need to build a review dashboard.
4. **The "Inspectability at MVP" open question prefers vendors that ship a run/trace UI**, making trace-UI depth a first-class selection criterion.
5. **Python monolith + DDD** — the domain layer must stay framework-free, so adapter-friendliness outranks feature count.

**Scope Confirmed:** 2026-07-31

---



## Technology Stack Analysis

Scoped to the three vendor areas plus the HITL surface. All prices and limits were read on **2026-07-31**; treat every number as dated, since four vendors changed pricing structure during 2026. Confidence labels: **High** = vendor's own current page, docs or source code, or verified directly during this research; **Medium** = single secondary source or vendor marketing; **Low** = thin or conflicting.

Four pricing pages were verified first-hand rather than taken from the research streams: [arize.com/pricing](https://arize.com/pricing/), [pydantic.dev/pricing](https://pydantic.dev/pricing), [comet.com/site/pricing](https://www.comet.com/site/pricing/), and the OTel GenAI convention status via [semantic-conventions-genai](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-spans.md).

### Programming Languages

*Popular Languages:* Python is unambiguously where 2026 production agent tooling lives — LangGraph, PydanticAI, Microsoft Agent Framework (Python GA 2026-04-03), Google ADK 2.0, smolagents and CrewAI all ship Python as a first-class or primary target. The locked "Python monolith" decision in `SPEC.md` therefore costs nothing in vendor availability; it is the majority path. Confidence: High.

*Where Python is second-class:* **promptfoo** is the notable exception — its core is TypeScript and Python enters as custom providers and Python assertions/graders, i.e. a supported extension point rather than the native idiom ([promptfoo docs](https://www.promptfoo.dev/docs/intro/)). For a Python DDD monolith that is friction, not a blocker. Confidence: Medium-High.

*Python-native eval libraries:* **DeepEval** (Apache-2.0, pytest-shaped), **Inspect AI** (MIT, Python-only, from the UK AI Security Institute) and **pydantic-evals** are genuinely Python-first. `pydantic-evals` is separately installable and explicitly designed to evaluate arbitrary functions, not only PydanticAI agents — relevant because one eval harness must score all five orchestration shapes ([PyPI](https://pypi.org/project/pydantic-evals/)).

*Language-level capability that changes the design:* strict schema conformance is now a **provider** feature rather than a library trick. OpenAI's `response_format: {type: "json_schema", strict: true}` and Anthropic's `strict` tool use both use grammar-constrained decoding, so a non-conforming token cannot be emitted ([OpenAI](https://developers.openai.com/api/docs/guides/structured-outputs), [Anthropic](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)). This matters directly for CAP-4: the `evidence_span` schema is enforceable at decode time. **Important caveat:** Anthropic's structured outputs silently **drop unsupported JSON Schema keywords** such as `minLength`/`minimum`, so the deterministic validator remains mandatory rather than belt-and-braces. Confidence: High.

*Language Evolution:* TypeScript remains strong for app-embedded agents (Cloudflare Agents, Code Mode packages), which is precisely the ecosystem agentic-cataloger is leaving. No 2026 evidence suggests the TS agent ecosystem offers capabilities Python lacks for this workload.

### Development Frameworks and Libraries

**The structural insight that should shape the harness.** O1–O5 are not five points on one axis; they are two independent axes:

- **Capability surface** — how the model reaches the domain: O1 = JSON tool calls, O2 = a CLI-ish command surface, O3 = code that calls an API.
- **Control-flow ownership** — who decides stage order: O4 = explicit graph, O5 = graph outside / agent loop inside, O1–O3 as usually implemented = the model's loop decides.

A framework biases the bakeoff mainly by claiming the second axis. If the framework owns control flow, O4/O5 come free but O1/O2/O3 collapse into "which tools does this node get" — at which point they are no longer peers of O4, they are running *inside* it. The neutral harness shape is therefore **one stage-runner interface + three interchangeable capability surfaces + a swappable control-flow driver**, all emitting the same spans so `tokens/item` and assign accuracy stay comparable.

There is a real 2026 precedent for exactly this kind of interface bakeoff: the **AXI study** ran 425 GitHub-task and 490 browser-task runs across raw CLI, MCP, MCP+tool-search, MCP+Code Mode and a hand-designed agent-first CLI, with an LLM judge and per-task cost/turn accounting, and published the harness ([axi.md](https://axi.md/), [github.com/ewilderj/axi](https://github.com/ewilderj/axi)). That is a working template for the O1/O2/O3 arms. No published 2026 study also varies control flow (O4/O5) on the same harness — that part agentic-cataloger would be inventing. Confidence: High on the precedent, High on the absence of an O4/O5 equivalent.

*Major Frameworks — fit map (✅ natural, ◑ workable with glue, ✖ fights you):*


| Framework (2026 state)             | O1  | O2                        | O3                 | O4                 | O5  | Invasiveness                       | OTel emit                            | Free neutral run UI            | Cost accounting                          |
| ---------------------------------- | --- | ------------------------- | ------------------ | ------------------ | --- | ---------------------------------- | ------------------------------------ | ------------------------------ | ---------------------------------------- |
| Plain Python + provider SDK        | ✅   | ✅                         | ◑                  | ◑                  | ◑   | **None**                           | any OTLP, your choice                | via Phoenix/Langfuse           | ✅ raw `usage`                            |
| PydanticAI (MIT, 1.42.x)           | ✅   | ◑                         | ◑                  | ◑                  | ✅   | **Low**                            | ✅ native, semconv 1.37               | Logfire free tier, or any OTLP | ✅ `gen_ai.usage.`*                       |
| OpenAI Agents SDK (MIT, 0.2.x)     | ✅   | ✅ shell tool              | ✅ native sandbox   | ◑                  | ◑   | Low–Med                            | ✅ official contrib instrumentor      | OpenAI Traces (proprietary)    | ✅                                        |
| Claude Agent SDK                   | ✅   | ✅ Bash/Read/Grep built in | ✅                  | ✖                  | ◑   | Med (owns loop, spawns CLI)        | ◑ third-party only                   | ✖                              | ✅ per-result cost                        |
| smolagents (v1.26.0)               | ✅   | ◑                         | ✅ **reference O3** | ✖                  | ◑   | Med                                | ✅ OpenInference                      | via Phoenix/Langfuse           | ✅                                        |
| LangGraph (MIT, 1.2 line)          | ✅   | ◑                         | ◑                  | ✅ **canonical O4** | ✅   | Med–High                           | ◑ via OpenInference, not first-party | LangSmith free = 5k traces     | ✅                                        |
| Apache Burr (0.42.0-incubating)    | ◑   | ◑                         | ◑                  | ✅                  | ✅   | **Low–Med**                        | ✅                                    | ✅ **self-hostable UI in-repo** | ◑ you record it                          |
| Microsoft Agent Framework (1.0 GA) | ✅   | ◑                         | ◑                  | ✅                  | ✅   | Med–High                           | ✅ native GenAI semconv               | ✖ (Foundry-oriented)           | ✅ incl. cache/reasoning tokens           |
| Google ADK 2.0 (Apache-2.0)        | ✅   | ◑                         | ◑                  | ✅                  | ✅   | Med–High + GCP gravity             | ✅ since 1.17                         | `adk web` local                | ✅                                        |
| LlamaIndex Workflows               | ◑   | ✖                         | ✖                  | ✅                  | ◑   | Med                                | ✅                                    | via Phoenix                    | ✅                                        |
| Haystack 2.29                      | ◑   | ✖                         | ✖                  | ✅                  | ◑   | **High** (pipeline is the program) | ✅                                    | enterprise                     | ◑                                        |
| CrewAI                             | ✅   | ✖                         | ✖                  | ◑                  | ◑   | **High** (role/crew-shaped)        | ✅                                    | AMP free (50 runs/mo)          | ◑                                        |
| AutoGen / Semantic Kernel          | —   | —                         | —                  | —                  | —   | —                                  | —                                    | —                              | **Maintenance mode — do not start here** |


*Ecosystem Maturity — three findings worth acting on:*

1. **The AutoGen question is settled.** Microsoft Agent Framework reached 1.0 GA for .NET and Python on 2026-04-03 with an LTS commitment, and **both AutoGen and Semantic Kernel are in maintenance mode** (bug and security fixes only), with official migration guides ([DevBlogs](https://devblogs.microsoft.com/agent-framework/microsoft-agent-framework-version-1-0/)). Confidence: High.
2. **Apache Burr is the most under-covered candidate for these specific constraints.** It is a state-machine library that explicitly refuses to own the LLM call — "Burr will *not* tell you how to build your models, how to query APIs, or how to manage your data" — and it ships a **free self-hostable tracking UI in the repo** (`pip install "burr[start]"`, port 7241) showing state at every step with rewind ([burr.apache.org](https://burr.apache.org/), [tracking docs](https://burr.dagworks.io/concepts/tracking/)). That combination — O4/O5 control flow, near-zero opinion about the capability surface, free inspectability — is close to the neutral harness shape above. Counterweight: ASF *incubating*, not graduated; PyPI still classifies it "4 - Beta"; small community. Confidence: High on capabilities, and the maturity caveat is the reason it is a candidate rather than a default.
3. **DSPy 3 + GEPA is a threat to the bakeoff, not just a candidate.** GEPA (ICLR 2026 oral) optimizes prompts *against your metric* — and the metric here is the bakeoff's own scoring function. Optimize per shape and you are comparing "shape + however much prompt headroom that shape had"; optimize once and you silently favour whichever shape it ran against. Either freeze prompt optimization as a control variable (optimize once, on a held-out slice, identically for all arms, version the output as a build artifact) or run it as a separate experiment after a shape is chosen ([DSPy GEPA docs](https://dspy.ai/api/optimizers/GEPA/overview/)). Confidence: High that the confound is real.

*Eval libraries, mapped to E1–E5:* **Inspect AI** is unexpectedly strong on E5 — `eval_set()` runs one task across several models with retries and resumption, which *is* the model×strategy matrix, and `evals_df()`/`samples_df()` give pandas frames so cost-per-item aggregation is a groupby. Its gap is E1: no hosted dataset with versioning, correction workflow or labelling UI. **DeepEval** is the most idiomatic pytest fit, which maps cleanly onto per-stage separation (three test modules) and onto deterministic scorers. **Ragas is largely inapplicable** — its eight core metrics are retrieval-and-generation metrics, while agentic-cataloger's three stages are classification, schema-extraction-with-citation, and taxonomy proposal. Confidence: High.

### Database and Storage Technologies

This section is where the "self-host or not" decision is actually made, because the differences are large and asymmetric.

*Self-host footprints, lightest to heaviest:*


| Option                        | Services required                                                                      | Realistic solo-dev burden                                                                                                                                          |
| ----------------------------- | -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Arize Phoenix**             | **One container**; SQLite by default or `PHOENIX_SQL_DATABASE_URL` → existing Postgres | ~1 hour to stand up; **additive-zero infrastructure** against what agentic-cataloger already runs                                                                          |
| **Laminar**                   | frontend + app server + Postgres + ClickHouse + Quickwit (Helm adds RabbitMQ + Redis)  | Moderate; Signals need an enterprise key                                                                                                                           |
| **Langfuse**                  | web + worker + Postgres + **ClickHouse (mandatory)** + Redis + S3/MinIO                | Half a day, then a permanent RAM tax — ClickHouse alone wants 2 CPU / 8 GiB (16 recommended); all components must run UTC or queries silently return wrong results |
| **Opik**                      | ClickHouse + **Zookeeper** + MySQL + Redis + MinIO, ClickHouse via Altinity operator   | Heaviest; production self-host effectively means Kubernetes, and self-hosted Opik has **no user management** (RBAC/SSO are Enterprise)                             |
| **DIY (SigNoz / ClickStack)** | ClickHouse + Postgres + collector                                                      | You then rebuild price tables, cost rollups, payload search and all of H1 — i.e. re-create the "custom built, not easily reviewable" problem with nicer storage    |


Confidence: High (vendor architecture docs). The Langfuse burden is corroborated by a 2026 practitioner account: "Managing six containers for a small team or personal project is a burden… ClickHouse eating 2GB+ of memory still feels wasteful for my scale" ([jangwook.net](https://jangwook.net/en/blog/en/langfuse-self-hosted-llm-tracing-setup-guide-2026/)).

**The asymmetry that decides it:** Phoenix is the only option whose infrastructure footprint is additive-zero — it can point at the existing Postgres 18. And **Opik Free Cloud is $0 with 25k spans/month, 60-day retention and the full annotation-queue feature set**, which makes self-hosting Opik close to irrational for a solo project unless data residency forces it. Apache-2.0 keeps self-hosting available as an exit, which is the point.

*Relational storage that stays in agentic-cataloger's own Postgres regardless of vendor:*

- **H2 (dead-letter queue) must be built, not bought.** No vendor in this survey ships one. Annotation queues are review tasks over *already-recorded traces*; they have no notion of a durable work item that must be re-driven through the pipeline, no retry/backoff, and no ownership of the downstream write. Using one as a DLQ inverts the data flow — a trace records what happened, a DLQ row is a promise about what still must happen. In DDD terms H2 is a table (`deferred_items`: product ref, stage, reason code, attempt count, payload snapshot, `trace_id`, status) plus a repository and a re-drive command. Storing the observability deep link on the row gets a reviewer from queue item to full run in one click. Confidence: High.
- **Durable execution can reuse the same Postgres.** DBOS is a library: `@DBOS.workflow` / `@DBOS.step` checkpointing into *your own* Postgres (`workflow_status` PENDING row, step outputs in `operation_outputs`, background thread resumes on restart), ~1–2 ms per checkpoint, ceiling in the low thousands of transitions/sec because it is Postgres-bound. Temporal externalizes into a cluster and imposes determinism on workflow code (no direct I/O, no wall clock, no unseeded randomness in the workflow body) in exchange for scale agentic-cataloger does not need ([dreaming.press comparison](https://dreaming.press/posts/dbos-vs-temporal-durable-agents.html)). Two DBOS caveats: it checkpoints via **pickle**, so tool results must pickle and should stay under ~2 MB, and sources disagree on the Python SDK's version maturity — verify on PyPI before committing. Confidence: High on the architecture, Low on the version.
- **Golden set location is a genuine fork.** Keeping E1 in Postgres as a first-class domain table with migrations is arguably *more* DDD-coherent and gives full ownership of the correction audit trail. What a vendor dataset buys instead is **trace → dataset promotion**: Langfuse documents `source_trace_id`/`source_observation_id` on dataset items plus batch-add from the observations table with JSON-path field mapping ([datasets docs](https://langfuse.com/docs/evaluation/dataset-runs/datasets)). That single capability — turning a bad production output into a labelled golden item in two clicks — is how E1 grows, and it is the most expensive thing to rebuild.

*In-Memory and OLAP:* Redis appears only as a vendor dependency, never as something agentic-cataloger needs directly. ClickHouse appears as a hard dependency of Langfuse and Opik; adopting either self-hosted means adopting ClickHouse operations. Confidence: High.

### Development Tools and Platforms



#### Eval platforms


| Tool              | Eval core or side feature           | Hosting / license                     | E1 dataset + versioning    | E2 per-stage           | E3 cost/item                                   | E5 matrix view          | $0 tier                                               | First paid           |
| ----------------- | ----------------------------------- | ------------------------------------- | -------------------------- | ---------------------- | ---------------------------------------------- | ----------------------- | ----------------------------------------------------- | -------------------- |
| **Langfuse**      | Observability-first, evals co-equal | Self-host **MIT** (`/ee` gated)       | Yes + timestamp versioning | Projects/datasets      | Yes — cost deltas in compare view              | Yes (rebuilt Apr 2026)  | Self-host unlimited; cloud 50k units, 2 users, 30d    | **$29** Core         |
| **Opik (Comet)**  | Both, genuinely                     | Self-host **Apache-2.0**, full server | Yes                        | Projects + Test Suites | Span/trace/project rollup                      | Yes                     | Self-host unlimited; cloud 25k spans, 10 members, 60d | **$19** Pro          |
| **Arize Phoenix** | Both                                | Self-host **ELv2** (not OSI)          | "Versioned datasets"       | Task/evaluator shaped  | Yes — explicit total + per-run experiment cost | Yes                     | Unlimited self-host                                   | n/a                  |
| **Braintrust**    | **Eval-first**, strongest workflow  | Managed; self-host = Enterprise       | Yes + immutable snapshots  | Projects               | Partial                                        | Yes (`base_experiment`) | 1 GB, 10k **scores**, 14d                             | **$249** Pro         |
| **LangSmith**     | Observability-first                 | Managed; self-host = Enterprise       | Yes                        | Projects               | Partial                                        | Yes                     | 5k traces, 14d, **1 seat**                            | **$39**/seat         |
| **promptfoo**     | **Eval-first**, CLI                 | **MIT**, local                        | YAML/CSV, git-versioned    | Separate configs       | Tracks token + cost in CI                      | Yes, side-by-side       | Free                                                  | Enterprise, unpriced |
| **DeepEval**      | **Eval-first**, pytest-native       | Framework Apache-2.0                  | Cloud datasets             | pytest structure       | Platform                                       | Platform                | 2 seats, 1 project                                    | **$19.99**/seat      |
| **Inspect AI**    | **Eval-first**, research-grade      | **MIT**, fully local                  | Code-defined, git          | `@task` per stage      | Tokens in logs → pandas                        | `eval_set()` + pandas   | Free                                                  | n/a                  |
| **W&B Weave**     | Side feature of ML tracker          | Managed                               | Yes                        | Yes                    | Via trace data                                 | Yes                     | 1 GB/mo ingest                                        | **$60** Pro          |
| **Ragas**         | Metric library only                 | Apache-2.0                            | Thin                       | n/a                    | No                                             | No                      | Free                                                  | n/a                  |


**Two traps in that table.**

*Braintrust bills per score, and the bakeoff arithmetic breaks it.* Starter includes 10k scores/month. A 500-item golden set × 3 stages × 3 scorers = 4,500 scores for one run; four model×strategy configurations = 18,000 — past the free cap in an afternoon, at $2.50/1k, on a meter with **no hard spending cap** ([Braintrust pricing](https://www.braintrust.dev/pricing)). Ironic, because several independent 2026 comparisons rate Braintrust strongest on eval workflow specifically — the price, not the product, is what rules it out.

*W&B Weave bills ingested bytes at $0.10/MB over quota — that is $100/GB*, roughly 25× Braintrust's $4/GB. A maintainer worked a concrete example: uploading a 2 GB dataset on Pro costs **$51.20** ([wandb/weave#4391](https://github.com/wandb/weave/issues/4391)). Given that agentic-cataloger stores verbatim source catalogue text plus `evidence_span` payloads across repeated runs, byte-metering is the worst possible billing axis for this workload. Confidence: High.

#### Observability platforms


| Vendor               | Centre of gravity                        | Hosting                                                   | OTLP ingest                  | Cost tracking                                                        | Free tier                                                           | First paid                             |
| -------------------- | ---------------------------------------- | --------------------------------------------------------- | ---------------------------- | -------------------------------------------------------------------- | ------------------------------------------------------------------- | -------------------------------------- |
| **Pydantic Logfire** | **OTel-native full-stack APM**, AI-aware | Managed (self-host = Enterprise; server/UI closed source) | It *is* an OTel backend      | **SQL over spans** = arbitrary `GROUP BY`                            | **10M records/mo**, 30d, 1 seat + 2 guests, 3 projects, hard-capped | **$49**/mo Team (5 seats), $2/M        |
| **Arize Phoenix**    | OTel-native tracing + evals              | Self-host, **ELv2**                                       | ✅ HTTP + **gRPC**            | From OpenInference token attrs; custom prices                        | Unmetered self-host                                                 | n/a                                    |
| **Arize AX**         | Same + labelling queues, Alyx            | Managed (self-host = Enterprise)                          | ✅                            | ✅                                                                    | **25k spans, 1 GB, 15d, unlimited users + labelling queues**        | **$50**/mo (50k spans, 10 GB, 30d)     |
| **Langfuse**         | LLM tracing + prompts + evals            | OSS MIT + cloud                                           | ✅ HTTP only, **no gRPC**     | Best-in-class: custom models, tiered pricing, per trace/user/session | 50k units, 30d, 2 users, **1 queue**                                | **$29**/mo Core                        |
| **Opik**             | Tracing + eval + SME annotation          | Apache-2.0 self-host + cloud                              | ✅ HTTP/protobuf only         | Span/trace/project                                                   | 25k spans, 60d, 10 members                                          | **$19**/mo                             |
| **LangSmith**        | LangChain-first                          | Managed                                                   | ✅                            | Per-trace tokens                                                     | 5k traces, **14d**, 1 seat                                          | **$39**/seat                           |
| **HoneyHive**        | Agent tracing + review                   | Managed                                                   | ✅                            | Per step                                                             | 10k events, 30d, 5 users                                            | **Unpriced** publicly                  |
| **Datadog**          | General APM + LLM module                 | Managed                                                   | ✅ w/ `dd-otlp-source=llmobs` | Tag-based                                                            | ~40k LLM spans/mo *for existing DD customers*                       | APM $31–36/host + span ingest          |
| **Grafana Cloud**    | OTel-native LGTM + Agent Observability   | Managed / OSS                                             | ✅ for telemetry              | PromQL/TraceQL                                                       | 50 GB traces/14d + 30k generations/mo                               | $19/mo + $1.50/1k generations          |
| **Laminar**          | Agent-run debugging, transcript-first    | Apache-2.0 self-host                                      | ✅                            | 3-day rolling cost baselines                                         | 1 GB, 15d, 1 seat                                                   | $30/mo                                 |
| **Helicone**         | **Gateway/proxy** + logging              | Apache-2.0                                                | Proxy-first                  | Per request                                                          | 10k req/mo                                                          | $79/mo — reported **maintenance mode** |
| **Portkey**          | **Gateway** — judge as one               | Managed + OSS gateway                                     | ✅                            | Per request                                                          | 10k logs, **3-day retention**                                       | $49/mo                                 |
| **Literal AI**       | —                                        | **Dead** — shut down 2025-10-31, all data deleted         | —                            | —                                                                    | —                                                                   | —                                      |


**Logfire is the standout for E3 specifically**, and this is the single most decision-relevant finding in the observability area. It offers Postgres-flavoured **SQL directly over spans**, so "cost per product ID grouped by pipeline stage and model config" is a `GROUP BY`, not a feature request — every other vendor gives fixed dashboard dimensions plus an export. Combined with 10M records/month free (one to two orders of magnitude more headroom than the LLM-native vendors' free tiers, which matters for a pipeline emitting many spans per product) and a hard cap that makes overspending impossible on Personal, it fits E3 and E5 better than anything else at $0. Verified first-hand on [pydantic.dev/pricing](https://pydantic.dev/pricing) (page `last-reviewed: 2026-07-29`). Two limits to note: Query API is capped at **500 requests/day** on Personal and Team, and retention is 30 days — so long-lived bakeoff results need exporting. Confidence: High.

#### HITL surfaces — does anything satisfy H1 out of the box?

Scored on the four things that matter: queue exists / filtered routing of a subset / structured labels / promote corrections into an eval dataset.


| Vendor                     | Queue                                                          | Filtered routing                                      | Structured labels                        | Promote to dataset            | H1 verdict                                                     |
| -------------------------- | -------------------------------------------------------------- | ----------------------------------------------------- | ---------------------------------------- | ----------------------------- | -------------------------------------------------------------- |
| **Opik**                   | ✅ traces *and* threads, shareable SME link, progress tracking  | ✅ **programmatic**                                    | Feedback definitions per queue           | ✅ same product, all OSS       | **Satisfies H1 as-is**                                         |
| **HoneyHive**              | ✅ span-scoped                                                  | ✅ real-time automation on score/metadata/cost filters | Human evaluators                         | ✅                             | **Features excellent, pricing unknown past free tier**         |
| **Arize AX**               | ✅ best reviewer UX (assignment, session context, custom views) | ✅                                                     | Annotation configs                       | ✅ + **evaluator calibration** | **Strong, and free — but see the code-evaluator caveat below** |
| **Datadog**                | ✅                                                              | ✅ automation rules + sampling                         | Shared schemas + required reasoning      | ✅ golden datasets             | **Features excellent, cost model hostile**                     |
| **Braintrust**             | ✅ strongest triage/calibration ops                             | ✅                                                     | Review scores                            | ✅ one-click                   | **1 review scorer/project on free; $249 to unlock**            |
| **Langfuse**               | ✅ **unlimited self-hosted**, 1 on cloud Hobby                  | ◑ manual/UI; programmatic enqueue is an open request  | Score configs                            | ✅                             | **You would write the routing job**                            |
| **Logfire**                | ✖ no queue; project-wide Annotations page + filters            | ◑ approximate via SQL + saved views                   | Verdict, category, expected output, tags | ✅ JSONL export as eval cases  | **Usable, no assignment**                                      |
| **Phoenix OSS**            | ✖                                                              | Filter by annotation value                            | ✅ span/trace/session                     | ✅                             | **Annotations without a worklist**                             |
| **Label Studio / Argilla** | ✅ best rubric/audit ops                                        | You build it                                          | ✅                                        | You build it                  | **Days of glue, zero trace context**                           |


**Opik's implementation is the most H1-shaped thing found.** Filtered routing of a subset into a reviewer queue is roughly six lines from the pipeline:

```python
queue = client.create_traces_annotation_queue(
    name="Low-confidence trait extractions",
    instructions="Check the evidence span actually supports the trait",
    feedback_definition_names=["evidence_valid", "category_correct"],
)
traces = client.search_traces(
    project_name="agentic-cataloger-extract",
    filter_string="feedback_scores.confidence < 0.7",
)
queue.add_traces(traces)
```

Reviewers get a shareable link to a distraction-free interface with instructions, predefined metrics, progress tracking and comments ([annotation queues docs](https://www.comet.com/docs/opik/evaluation/advanced/annotation_queues.md)). Verified on Comet's pricing matrix: **Annotation Queues, dedicated annotation UI, custom feedback schemas, and trace-or-thread annotation are all included in the Open Source column**, as are Custom Metrics ("custom LLM-as-Judge, criteria-based, and python code based") and Test Suites with item- and suite-level assertions. Confidence: High (read first-hand 2026-07-31).

**One caveat found first-hand that the research streams missed.** Arize AX's own comparison matrix marks **"Custom code evaluators" as unavailable on both Free and Pro** (Enterprise only), alongside "Agent as a judge" ([arize.com/pricing](https://arize.com/pricing/), read 2026-07-31). If that reading is correct it materially weakens AX for E2, because agentic-cataloger's most valuable scorers are deterministic code — exact-match on category ID and `evidence_span ⊆ source_text`. The pricing table renders checkmarks as glyphs that did not survive extraction cleanly, so treat this as **Medium confidence and verify in-product before shortlisting AX**; it is a ten-minute check with real consequences. AX also limits annotations to spans from the last **31 days** without contacting support, and Free is capped at 1 Space and 25k spans/month.

**The pattern across the whole table:** "promote human corrections into a dataset" is universal — every serious vendor treats human labels as dataset ground truth and judge-calibration input. The differentiator is **automated filtered routing**, which only Opik (SDK), HoneyHive (rules), Datadog (rules) and Arize AX clearly have.

### Cloud Infrastructure and Deployment

*What $0 and ~$50/month actually buy:*


|                                                       | $0                                                                 | ~$20–50/mo                                               |
| ----------------------------------------------------- | ------------------------------------------------------------------ | -------------------------------------------------------- |
| Logfire                                               | **10M records/mo**, 30d, 1 seat, 3 projects, cannot overspend      | $49 Team, 5 seats, $2/M                                  |
| Opik                                                  | Self-host unlimited (Apache-2.0); cloud 25k spans, 10 members, 60d | **$19** Pro: 100k spans, 50 members, +$5/100k            |
| Phoenix                                               | **Self-host unlimited, no feature gates**, one container           | n/a                                                      |
| Arize AX                                              | 25k spans, 1 GB, 15d, unlimited users + labelling queues           | **$50** Pro: 50k spans, 10 GB, 30d                       |
| Langfuse                                              | Self-host unlimited (MIT); cloud 50k units, 2 users, 1 queue       | **$29** Core: 100k units, unlimited users, 90d, 3 queues |
| promptfoo / Inspect AI / DeepEval OSS                 | Everything, locally, forever                                       | n/a                                                      |
| LangSmith                                             | 1 seat, 5k traces, 14d                                             | $39 = **one seat**                                       |
| Braintrust                                            | 1 GB, 10k scores, 14d, **uncapped meter**                          | Nothing — next tier is **$249**                          |
| W&B Weave                                             | 1 GB/mo ingest                                                     | Nothing — $60, overage $100/GB                           |
| Datadog / Galileo / Autoblocks / Patronus / Scorecard | Free/dev tiers only                                                | Out of reach or unpriced                                 |


The ceiling does real work: it eliminates Braintrust's paid tier, Weave, Datadog, Galileo, Autoblocks and Patronus, and reduces LangSmith to a single seat. It leaves a cluster of MIT/Apache/ELv2 options that are free at this scale plus three managed tiers at $19–50.

*Cloud-provider eval services:* Vertex AI Gen AI Evaluation and Bedrock Evaluations charge only inference (Vertex computation-based metrics including Exact Match at $0.00003/1k input chars; Bedrock adds $0.21 per completed human task). Both are cloud-locked, neither offers dataset versioning with a correction workflow, and adopting either means adopting that cloud — a poor fit for a local-Postgres monolith. Worth stealing one framing from a practitioner analysis: judge cost runs ~$0.0011/row, so "optimize the thing that is expensive, which is not the judge" — regenerating candidate outputs across the whole set dominates ([drpranayjha](https://drpranayjha.com/vertex-ai-gen-ai-evaluation-service/)). For agentic-cataloger's *extract* stage, output tokens per product are large, so **E3's real signal is generation cost per item, not scoring cost** — any tool reporting only "eval cost" will mislead.

*Two deployment risks specific to an OTel-first design:*

1. **Datadog may bill you for merely emitting** `gen_ai.`***.** One analysis reports that the presence of recognised GenAI attributes on OTLP spans auto-activates token-based LLM Observability billing, with opt-out requiring attribute stripping in the collector ([openobserve](https://openobserve.ai/blog/datadog-pricing/)). The specific rate quoted there is **Low confidence** (no standalone SKU on Datadog's pricing page), but the mechanism is corroborated by Datadog's own `dd-otlp-source=llmobs` requirement. For a $50 ceiling: avoid.
2. **Grafana Agent Observability is two channels, not one.** Generation data goes to a dedicated API via thin SDKs; only standard `gen_ai.`* spans and metrics travel over OTLP. Grafana's docs are explicit that "Alloy and the OpenTelemetry Collector are **not** generation-ingest receivers." So the good conversation UI needs their SDK — a partial lock-in. Also note generations and eval tokens **are not metered until 2026-10-01**, so current free usage is a window, not a price.



### Technology Adoption Trends

*Migration Patterns — the 2026 market shifted enough to prune the field before any feature comparison:*


| Change                                            | Detail                                                                                                  | Effect                                         |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| **Humanloop is gone**                             | Anthropic acqui-hired the team Aug 2025; platform sunset 2025-09-08 and **all customer data deleted**   | Remove entirely                                |
| **Literal AI is gone**                            | Service ended 2025-10-31, all data deleted; own migration guide points at Langfuse/OTel                 | Remove entirely                                |
| **OpenAI hosted Evals has a death date**          | Read-only 2026-10-31, shutdown 2026-11-30                                                               | Do not build on it                             |
| **Langfuse → ClickHouse** (Jan 2026)              | Team joined; MIT and self-hosting explicitly unaffected; Enterprise now sold alongside ClickHouse plans | Watch packaging direction                      |
| **promptfoo → OpenAI** (Mar 2026)                 | MIT retained, folding into OpenAI Frontier                                                              | Governance note for a multi-model bakeoff tool |
| **Galileo → Cisco/Splunk** (completed 2026-05-22) | Folding into Splunk observability                                                                       | Sub-$50 self-serve tier unlikely               |
| **AutoGen + Semantic Kernel → maintenance mode**  | Superseded by Microsoft Agent Framework 1.0 GA                                                          | Do not start new work there                    |
| **Helicone reportedly in maintenance mode**       | Security/bug fixes only (Medium confidence, no vendor statement)                                        | Deprioritize                                   |


*Emerging Technologies — three trends that bear directly on the SPEC:*

**1. The OTel GenAI conventions are real but not stable, which weakens "instrument once, swap backends freely."** Verified: as of 2026-07-31 **no** GenAI span, event, metric or attribute is marked Stable — all are `Development`. The conventions moved to a dedicated repo (`open-telemetry/semantic-conventions-genai`, created 2026-05-05) which has **no tagged release**; core semconv v1.42.0 (2026-06-12) deprecated and moved all `gen_ai.`* content, and v1.43.0 ships none. Frameworks in the wild emit **multiple attribute generations simultaneously** ([gen-ai-spans.md](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-spans.md), [John Hodge survey](https://john-hodge.com/blog/opentelemetry-genai-semantic-conventions/)). Confidence: High.

Backend swapping is therefore **config-only but not fidelity-neutral**, and the missing fidelity is exactly what agentic-cataloger needs. Three verified failure modes:

- **Content location moved.** semconv v1.37+ emits prompts/completions as a span *event* rather than attributes; Langfuse showed `Input: null` for such spans while still tracking tokens and cost, until [PR #14930](https://github.com/langfuse/langfuse/pull/14930) fixed it ([issue #12657](https://github.com/langfuse/langfuse/issues/12657)). Since "read actual model output" is a stated requirement, verify content capture per candidate backend on *your* emitter.
- **Cost namespace differs.** Phoenix derives cost from OpenInference `llm.token_count.`*; Langfuse and Opik from `gen_ai.usage.*`. **Cost is not in the spec at all**, so this will never converge by standardisation. **Update (verified 2026-07-31):** Phoenix closed this gap from its side — since 15.10.0 it converts `gen_ai.`* → OpenInference at ingest, `gen_ai.usage.*` included, so the mismatch no longer forces an emitter choice or a mapping adapter for a Phoenix backend ([release note 05-15-2026](https://arize.com/docs/phoenix/release-notes/05-2026/05-15-2026-otel-semconv-conversion), [issue #13267](https://github.com/Arize-ai/phoenix/issues/13267)). The general warning stands for other backends.
- **Double-counting is a live bug class.** Phoenix dashboard token totals triple-counted when frameworks propagated token attributes onto parent agent spans; the fix aggregates `span_kind = 'LLM'` only ([#12768](https://github.com/Arize-ai/phoenix/issues/12768)). Any home-grown cost-per-item aggregation must filter to leaf LLM spans.

The mitigation fits DDD well: keep `opentelemetry-api` only in the domain behind a thin port, put SDK + exporter + attribute mapping in one infrastructure adapter, and do fan-out in an **OTel Collector** with multiple exporters — which also yields genuine dual-write for a shadow comparison of two backends, plus a place for redaction and per-exporter attribute rewriting. Cost: one more process to run.

**2. Code Mode's mechanism is the same one already committed to in CAP-6.** Anthropic reports 150,000 → 2,000 tokens (98.7%) on a workflow by exposing MCP servers as files the agent explores on demand instead of loading all definitions upfront ([Anthropic](https://www.anthropic.com/engineering/code-execution-with-mcp)); productized as Tool Search (~85% reduction on definitions) and Programmatic Tool Calling (43,588 → 27,297 tokens, 37%) ([Anthropic](https://www.anthropic.com/engineering/advanced-tool-use)). The savings come from two separable things worth measuring independently: **progressive disclosure** of definitions, and **keeping intermediate data out of context**. Note the symmetry — `codemode.search()` is architecturally the same idea as agentic-cataloger's killed full-taxonomy dump, applied to tool catalogues. The industry converged on the mechanism the SPEC already chose for category context.

**A security consequence that cannot be deferred, despite security being out of scope.** O3 only works if code touches something. The 2026 consensus is that a read-only role is necessary and **not sufficient** — prompt injection is OWASP LLM Top-10 #1, and agentic-cataloger ingests *externally-controlled supermarket catalogue text*, so a poisoned description field is an injection vector; "a guardrail the agent can read is a guardrail the agent can ignore." Also relevant: `smolagents`' own docs state `LocalPythonExecutor` "is **not** a security sandbox… must not be used as a security boundary," so a real O3 arm needs `executor_type="e2b"|"modal"|"docker"`. **The design that dissolves most of this:** give the O3 sandbox an HTTP/CLI client against agentic-cataloger's own application API rather than a database connection. Then existing validators and the persist-after-validate path remain the only writers, the sandbox needs no DB credentials, and O1/O2/O3 differ *only* in surface — which is what makes the comparison clean. Security and bakeoff-fairness point the same way here. (Sourced on the security findings; the design conclusion is inference.)

**3. MCP vs CLI is unresolved, and the resolution is "design beats protocol."** Two benchmarks disagree in *direction*: Scalekit measured MCP consuming 4–32× more tokens than CLI for identical operations (one repo-language check: 1,365 tokens via CLI vs 44,026 via MCP); Mao and Pradhan's 756 runs found native MCP at 91.7% success vs CLI 83.3%, with CLI using **2.9× more** billed tokens. The AXI authors reconcile it: their CLI arm was auto-generated from API specs rather than designed for agents. AXI's own numbers make the point — a hand-designed agent-first CLI beat both raw `gh` CLI and GitHub MCP on every metric (100% success, $0.050/task, 3 turns vs MCP's 87%, $0.148, 6 turns), widening to 12× on a complex CI investigation ([axi.md](https://axi.md/)).

**Practical consequence:** O2 must be an AXI-style CLI (pre-computed aggregate fields, explicit empty states, structured parseable errors, data separated from debug output), or the bakeoff will measure "our CLI is badly designed for agents" and mislabel it "O2 loses." The cheapest honest implementation is one command layer with two adapters over it — a Typer/Click surface and a tool/MCP surface generated from the same command objects. The strongest counter-argument to weigh: "a good CLI is MCP with extra steps," since progressive disclosure, consistent auth and a skills layer must all be hand-built and kept in sync forever. That bites hardest at large tool counts, which is not agentic-cataloger's situation (a handful of verbs: `category search`, `category create`, `product assign`, `traits extract`).

*Community Trends — framework vs plain code:* there is a 2026 consensus and it is narrower than either camp's headline: **start with the loop; adopt a framework when you can name the pain.** The thin-harness strand argues the abstractions were scaffolding for weaker 2023 models and that the load-bearing replacement is plain structured execution traces you can grep ([tianpan.co](https://tianpan.co/blog/2026-04-13-post-framework-era-agents-api-client-while-loop)); the most honest account corrects itself, noting LangChain was replaced by "a custom harness plus a few specialized building blocks," not by nothing, with a concrete migration trigger — "when the incident stack trace has more frames in `langchain_`* than in your own code" ([Wasowski](https://medium.com/@wasowski.jarek/after-a-year-with-langchain-in-production-i-replaced-it-with-200-lines-of-python-d043a61afcc7)). The counter-argument is stronger than its caricature: the real problems are distributed-systems problems — retry, persistence, event routing, step-level observability — so the answer is durable execution as the harness with a thin agent loop on top ([Inngest](https://www.inngest.com/blog/your-agent-needs-a-harness-not-a-framework)). Named triggers where a framework earns its keep: durable resumable state, multi-agent handoffs, parallel fan-out, HITL checkpoints, tracing at scale.

Applied here: **bulk catalogue ingest supplies the durability trigger, and a five-way bakeoff supplies the "control flow must stay swappable" anti-trigger.** Those point in opposite directions on framework adoption and the same direction on durable-execution-as-substrate. That is also a bakeoff-fairness argument: if durability lives in the substrate, all of O1–O5 inherit resumability equally; if LangGraph's checkpointer covers O4 while O1–O3 hand-roll retries, O4 wins on robustness for reasons unrelated to orchestration shape.

*Evidence-quality caution:* a large share of 2026 "framework comparison" and "pricing roundup" pages are low-provenance SEO content with confident numbers that trace to no primary measurement. Several publish free-tier figures that vendor pages directly contradict (one claims Langfuse free = 1M spans and Pro = $249 against the vendor's 50k units and $199; another claims LangSmith free = 1,000 traces and $99/mo against the vendor's 5k traces and $39/seat). Vendor-published competitive content (Braintrust, Comet, Confident AI, Galileo, Laminar, Arize) has been used only for verifiable facts about *competitors'* architecture or licensing, never for rankings.

### Cross-Technology Analysis

Three patterns connect the language, framework and platform choices:

1. **The Python + DDD constraint and the bakeoff constraint select the same vendors.** Both reward tools that sit behind an adapter and accept a plain callable — `run_experiment(task=my_callable)`, `Eval(task=...)`, `@task`, plain-function tools. Both penalise tools that want to own control flow or domain objects. So "keeps the domain layer clean" and "does not bias the bakeoff" are, in practice, one selection criterion.
2. **Cost-per-item is nowhere first-class as an assertable metric.** It is displayed and aggregated well by Phoenix (explicit total-experiment and per-run cost), Langfuse (cost deltas in the rebuilt Experiments view) and Opik (span→trace→project rollup), and queryable arbitrarily only in Logfire's SQL. But no vendor lets you *gate* on it. E3's last mile is always custom — and every vendor's figure is an estimate from a price table that goes stale exactly when E5 introduces a newly released model (Opik returns `None` for unsupported models; Phoenix warns "actual billing may differ"). Reconcile against provider billing at least once.
3. **The eval/observability split maps onto agentic-cataloger's two loops.** "Stare at a trace to find what broke" is observability; "run structured experiments to decide what ships" is eval. E1/E2/E3/E5 are all offline-experiment-shaped, but CAP-9 and the inspectability question are trace-shaped. That is the real argument for evaluating a two-tool pairing rather than assuming one platform.

*Candidate pairings that work, at $0–50/mo:*

- **Logfire (spans, SQL cost, 10M free) + Opik Free (H1 queue + datasets)** — Logfire absorbs high-volume pipeline telemetry with room to spare and gives arbitrary `GROUP BY` for cost-per-item; only the *sampled low-confidence subset* is mirrored into Opik, keeping it inside the 25k-span tier. Both accept OTLP: one collector, two exporters. Total **$0**.
- **Phoenix self-hosted (additive-zero infra, next to existing Postgres) + Opik Free or Arize AX Free (queues)** — same shape, own the trace store.
- **Opik alone** — the only single platform where tracing, datasets, experiments, code-based custom metrics and annotation queues are all present at $0 (self-host or cloud), verified on the pricing matrix.
- **Phoenix alone** — a single platform once H1 is accepted as first-party work rather than a vendor feature. Tracing, versioned datasets, experiments, code-based evaluators and the run UI are all present with no feature gates, at the lightest self-host footprint in the survey. This is the shape selected on 2026-07-31; see *Selection decision* below for what the two constraint relaxations were and what they cost.

*Pairings that conflict:* Phoenix + Langfuse simultaneously (attribute-convention collision — Phoenix wants OpenInference `llm.token_count.`* for cost, Langfuse prefers `gen_ai.*`; emitting both risks the double-counting bug class); anything + Datadog on the same OTLP pipeline (GenAI attributes may trigger metered billing); Weave as the high-volume sink (byte metering vs large payloads); LangSmith as the golden-set store on the cheap path (**manual** annotation-queue adds do not extend retention, so reviewed traces expire at 14 days — the feature you want and the price you want are mutually exclusive); Braintrust Starter as the only H1 (1 review scorer per project cannot express a multi-dimension rubric).

### Quality Assessment

*High confidence:* 2026 market changes (acquisitions, shutdowns); OTel GenAI conventions still `Development`; the four pricing pages verified first-hand; self-host footprints; Opik OSS feature inclusion; Logfire's SQL-over-spans and free-tier size; the Weave and Braintrust metering traps; AutoGen/SK maintenance mode; Anthropic/Cloudflare Code Mode token figures; the AXI benchmark and its contradiction with Mao/Pradhan.

*Medium confidence, worth verifying before shortlisting:* Arize AX excluding custom code evaluators from Free and Pro (**highest-value ten-minute check in this document** — note it does not apply to Phoenix OSS, which has no feature gates); Helicone's maintenance-mode status.

*Resolved after this section was written (verified 2026-07-31, see Selection decision):* Phoenix OSS has annotations but **not** queues — labeling queues are AX-only, now confirmed by Arize's own platform comparison and the AX-scoped queue docs. Phoenix **does** consume `gen_ai.usage.`*, via ingest-time conversion to OpenInference since 15.10.0. Langfuse's arbitrary cost group-by is **no longer a requirement** — E3 was relaxed to an average.

*Resolved conflicts:* Langfuse annotation queues **are** available and unlimited in OSS self-host — the widely repeated "Enterprise-only" claim traces to bot answers on GitHub issues, and is contradicted by the entitlements source (`oss: { "annotation-queue-count": false }`, where `false` means unlimited) and by the official self-host feature table. Ironically the *cloud* Hobby tier is the restricted one at 1 queue. Opik Pro is **$19/mo** (a secondary source saying $39 is wrong). DeepEval is **Apache-2.0**, not MIT.

*Research gaps:* no published 2026 benchmark varies control flow (O4/O5) on a shared harness, so that part of CAP-10 has no prior art to copy; DBOS Python SDK maturity is unresolved across sources; HoneyHive and Scorecard have no public pricing past their free tiers; adapter-friendliness — whether a given SDK genuinely stays out of a DDD domain layer — cannot be settled from documentation and needs a short local spike.

*Source:* verified vendor pages listed at the top of this section, plus per-claim citations inline. Research streams: [eval tooling survey](a222d2a1-7331-43bb-8fde-cf5d95482033), [orchestration survey](7a607bde-2107-4066-9125-8f836c7c2aab), [observability and HITL survey](4cb66143-b8f1-4764-a9ee-93f3767bad80).

---



## Selection decision — Arize Phoenix as a single self-hosted platform

**Decided 2026-07-31 with Nathan.** **Verdict:** self-hosted Phoenix wins — it covers everything essential (traces, datasets, experiments, code evaluators, cost rollups, run UI), is decently popular, and has the simplest deployment/hosting path in the survey (one container on existing Postgres). Observability, inspectability and the eval harness consolidate there; the reviewer surface (H1) and the dead-letter queue (H2) are first-party. No paid tier, no second vendor, no custom agent-run UI.

### What changed the analysis

The body of this report leaned toward a two-tool pairing (Logfire for spans and SQL cost, Opik for queues and datasets). Three verifications and two constraint relaxations removed the reasons for that shape.

*Verified first-hand on 2026-07-31:*

1. **Phoenix converts OTel GenAI attributes to OpenInference at ingest.** Since `arize-phoenix` **15.10.0** (release note dated 2026-05-15), `gen_ai.`* spans decode into the OpenInference tree server-side and zero-config: `gen_ai.input.messages` → `llm.input_messages.*`, `gen_ai.output.message` → `llm.output_messages.*`, tool definitions and results → `llm.tools.*` / `tool.*`, `gen_ai.usage.*` **→** `llm.token_count.prompt`**/*`*completion`, `gen_ai.system` / `gen_ai.request.model` → `llm.provider` / `llm.model_name`. Existing OpenInference attributes take precedence; conversion only fills gaps ([release note](https://arize.com/docs/phoenix/release-notes/05-2026/05-15-2026-otel-semconv-conversion), implementation in [#13267](https://github.com/Arize-ai/phoenix/issues/13267) — `phoenix.trace.gen_ai.conversion` wired into `decode_otlp_span`, with a hot-path bail so non-GenAI spans skip the pipeline). Confidence: High. This retires the "cost namespace differs" objection and the "content moved to a span event" objection for a Phoenix backend, and it means the emitter can be a native OTel one (PydanticAI, MS Agent Framework, OTel contrib) without an attribute-mapping adapter. For *new* instrumentation Arize still recommends OpenInference, since GenAI semconv remains `Development` and span kinds have no `gen_ai` equivalent ([conventions comparison](https://arize.com/docs/phoenix/tracing/concepts-tracing/otel-openinference/semantic-conventions)).
2. **Cost requires five attributes and fails silently.** `llm.token_count.prompt`/`completion`/`total`, `llm.model_name`, `llm.provider`, plus a Settings → Models entry whose **name-pattern regex matches the traced model name exactly**. A miss renders $0 with token counts still visible — the single most common Phoenix cost complaint, and the DSPy/LiteLLM case in [#8465](https://github.com/Arize-ai/phoenix/issues/8465) shows the failure precisely (`anthropic/claude-sonnet-4-…` not matching the built-in pattern). Optional breakdowns exist for cache read/write and reasoning tokens ([cost tracking docs](https://arize.com/docs/phoenix/tracing/how-to-tracing/cost-tracking)). Treat cost visibility as a setup check per model, not an assumption. Confidence: High.
3. **Phoenix OSS has annotations, not queues — confirmed, and the earlier ambiguity is explained.** Phoenix supports categorical / continuous / free-form annotations on spans, traces and sessions, with annotation configs as rubrics, author-and-source provenance (human, LLM, code, user feedback), and propagation into datasets ([how-to-annotate-traces](https://arize.com/docs/phoenix/tracing/llm-traces/how-to-annotate-traces)). Queues with assignment, reassignment, filtered routing, Alyx-generated custom views and inter-annotator agreement are **Arize AX** ([labeling queues](https://arize.com/docs/ax/evaluate/labeling-queues), and the June 2026 AX release notes that added trace-level queue records and custom views). Arize's own platform comparison lists Phoenix's human-review column as annotations only. The confusion in secondary sources comes from the `arize` SDK's `client.annotation_queues.`* methods, which target AX spaces, not a Phoenix instance. Confidence: High.

*Constraint relaxations from Nathan (these are the actual decision drivers):*

1. **E3 does not need per-product cost.** A stage-level average — total stage cost ÷ items processed — is sufficient. This removes the only capability where Logfire was uniquely strong (arbitrary `GROUP BY` over spans) and simultaneously removes the open Langfuse question about grouping cost by a metadata key. Phoenix's project- and experiment-level cost rollups, including total experiment cost and cost per experiment run, cover it directly.
2. **A first-party reviewer queue is wanted, not merely tolerated.** H1 needs domain display and domain actions — reassign leaf, edit trait, accept/reject evidence span, re-drive item — which is a superset of what any vendor annotation queue does (label capture over an already-recorded trace). This removes Opik's decisive advantage. It also composes with a finding already in this report: H2 must be built regardless, since no surveyed vendor ships a DLQ. H1 therefore becomes a view over `deferred_items` with a Phoenix trace deep link per row, not a new subsystem.



### Why Phoenix specifically, given those relaxations

Once cost-grouping and queues are off the requirements list, the criteria reduce to trace UI depth, dataset and experiment support with code-based evaluators, cost rollups, footprint and license — and Phoenix wins the first four at the lowest cost of the fifth:

- **Footprint is additive-zero.** One container, `PHOENIX_SQL_DATABASE_URL` at the existing Postgres 18. Nothing else in the survey avoids ClickHouse (Langfuse, Opik self-host), Zookeeper (Opik) or a multi-service Helm chart (Laminar).
- **No feature gates.** The AX "custom code evaluators are Enterprise-only" caveat — flagged in this report as the highest-value check — does not apply to Phoenix OSS. The scorers that matter here are deterministic Python (exact-match on category ID, `evidence_span ⊆ source_text`).
- **It has real auth.** Phoenix self-host ships authentication, RBAC and an OAuth2 authorization server, so a human reviewer can have an account. Self-hosted Opik has no user management (RBAC/SSO are Enterprise) — relevant precisely because H1 is a human surface.
- **Adapter-friendly.** Experiments take a plain callable and code evaluators, so the domain layer stays framework-free and every orchestration arm scores on one harness.
- **It ships an MCP server.** `PHOENIX_ENABLE_MCP_SERVER` mounts a remote MCP server at `/mcp` (beta, default on) alongside a CLI with browser OAuth2 login ([configuration](https://arize.com/docs/phoenix/self-hosting/configuration)). Incidental to the selection — the in-product MCP decision below concerns agentic-cataloger's own tools, not Phoenix's — but it makes trace and experiment inspection available to an agent or IDE without extra work.



### What is knowingly given up

- **ELv2, not OSI open source.** Fine for internal and portfolio use; it only binds if Phoenix were ever offered as a hosted service. The practical edge is that routing, assignment, agreement analysis, evaluator calibration and managed monitors are the AX upsell boundary — "Phoenix forever" means those stay hand-built or unbuilt.
- **No cost gating and no arbitrary cost queries.** Accepted per relaxation 4. Note also that no vendor in the survey allows gating on cost, so this was never a differentiator.
- **Single-vendor attribute gravity.** OpenInference is Arize-defined. Mitigation is unchanged and cheap: OTel behind a domain port, exporter in one adapter, and a Collector if a second backend ever needs a fan-out.
- **Two operational duties self-hosting creates.** Retention and disk are yours — trace payloads carry verbatim catalogue text and `evidence_span` values, so set per-project retention immediately and keep Phoenix in its own database rather than sharing the application's. And when aggregating cost, filter to leaf `span_kind = 'LLM'` spans; parent-span token propagation double-counts ([#12768](https://github.com/Arize-ai/phoenix/issues/12768)).



### Companion decision — in-product capability surface starts at MCP

Separate from vendor selection: agentic-cataloger's own agent tools (`category search`, `category create`, `product assign`, `traits extract`) are exposed as **MCP / tool calls (O1)** to begin with, and the surface question is revisited when a concrete limit appears rather than benchmarked up front. The implementation constraint from this report survives that decision and is what keeps the option open: build **one command layer** and let the MCP surface be a thin adapter over it, so an AXI-style CLI (O2) or a Code Mode sandbox calling the application API (O3) can be added later without reworking the domain. The two named triggers to watch are token blowup on tool definitions (the case for progressive disclosure / Tool Search) and intermediate data that should never enter context (the case for programmatic tool calling). Consequence for CAP-10: the bakeoff obligation narrows to **control flow (O4/O5) and product supply (P)** — the two axes where no prior art exists and where a wrong early lock-in is expensive.

