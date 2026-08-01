# Explore bakeoffs — do not pre-pick

Design the eval harness before declaring winners. Shared metrics: assign accuracy (E1), per-stage scores (E2), average cost per item (E3 — total stage cost ÷ items processed), reproducibility/inspectability; model/context bakeoff (E5). Minimum: same eval set + same ingest slice for every candidate before any option is preferred in writing.

O1–O5 are two independent axes, and only the second is bakeoff-gated:

- **Capability surface** (how the model reaches the domain): O1 tool calls, O2 command surface, O3 code. **Started at O1 by decision (2026-07-31)** — see SPEC Constraints. Not a bakeoff arm at MVP.
- **Control-flow ownership** (who decides stage order): O4 explicit graph, O5 graph outside / agent loop inside, model-driven loop. Still bakeoff-gated.

## Orchestration (O1–O5; O6 killed)

| ID | Candidate | Status |
| --- | --- | --- |
| O1 | Tool-calling agent (function/MCP tools) | **Adopted first** — thin MCP surface over one command layer |
| O2 | CLI-like interface for agent + human | Later arm; only if O1 hits a named limit. Must be AXI-style (pre-computed aggregates, explicit empty states, structured errors) or it measures bad CLI design |
| O3 | Code Mode (agent writes code that calls APIs) | Later arm; sandbox must call the application API, never the DB |
| O4 | LangGraph / state-machine fixed sequence | **Bakeoff (MVP arm)** |
| O5 | Hybrid: graph of stages, tools only inside a stage | **Bakeoff (MVP arm)** |

## Product / adjacent supply (MVP arms: P2, P4)

| ID | Candidate | Status |
| --- | --- | --- |
| P2 | One product at a time | **Bakeoff (MVP arm)** |
| P4 | Agent search products on demand | **Bakeoff (MVP arm)** |
| P3 | Embedding-neighbor products | Deferred — needs embeddings (out of MVP, 2026-08-01) |
| P9 | Hybrid: neighbors + agent search | Deferred — needs embeddings |
| P10 | Cluster batch by embedding; one call per cluster | Deferred — needs embeddings |

**Supply “good” looks like:** category-assign quality vs tokens/item; recall of true substitutes in context.

The MVP bakeoff is therefore **2 control-flow × 2 supply**, and it requires no vector store. P3/P9/P10 become live arms only if embeddings are reintroduced.

**Excluded from experiments:** P1, P5, P6, P7, P8 (see `kill-pile.md`).

## Related explore (lock later, not now)

| Area | Candidates | Notes |
| --- | --- | --- |
| Parse | R1, R2, R5, R6 | Structured out vs tool/CLI args SoT; retry; deterministic validators |
| Persist path | D1 vs D2 | Agent save vs orchestrator-after-validate |
| Assign timing | A2 vs A3 | After category confirmed vs deferred batch |
| HITL surfaces | H1 + H2 | Both required and both first-party; H1 is read-only in MVP (2026-08-01) |
| Category context maturity | C4 | Deferred with embeddings; revisit only if C2 search shows a measured recall/cost limit |

## Deferred by the 2026-08-01 scope reduction

Each of these is a *later arm or later hardening*, not a killed option. Revisit criteria are named so nothing is reopened on vibes.

| Deferred | Revisit when |
| --- | --- |
| Embeddings / pgvector, embedding ingest filter, P3/P9/P10, C4 | C2 search shows a measured context-recall or cost ceiling on the eval harness |
| Indexed comparison-price projection | Derive-on-read comparison queries are measured too slow at the target catalog size |
| Snapshot completeness attestation, absence deactivation, replay ordering | A second source adapter or a source that genuinely delists products is onboarded |
| Concurrency machinery (topology CAS, generation watermarks, leases/fencing, transactional queue producer) | More than one worker or writer runs concurrently |
| Reviewer domain writes (leaf reassign, trait edit, evidence accept/reject in UI) | The read-only dashboard proves the queue is worth acting on in-app rather than by CLI |
| Third LLM provider | E5 needs a model family the two adapters do not cover |
| Periodic scheduled hygiene | Post-bulk hygiene is shown to miss drift between runs |
| Gated cutover ceremony (freeze/restore drill, observation window, routing rollback) | The system holds data that cannot be recovered by re-import |
| Byte-offset / NFC evidence addressing and carry-forward invalidation | Evidence disputes or multi-revision source drift actually appear |

Full ratings and notes: adopted companion `morphological-matrix.md`.
