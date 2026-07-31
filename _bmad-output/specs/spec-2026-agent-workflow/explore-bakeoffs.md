# Explore bakeoffs — do not pre-pick

Design the eval harness before declaring winners. Shared metrics: assign accuracy (E1), per-stage scores (E2), token-cost-per-item (E3), reproducibility/inspectability; model/context bakeoff (E5). Minimum: same eval set + same ingest slice for every candidate before any option is preferred in writing.

## Orchestration (O1–O5; O6 killed)

| ID | Candidate |
| --- | --- |
| O1 | Tool-calling agent (function/MCP tools) |
| O2 | CLI-like interface for agent + human |
| O3 | Code Mode (agent writes code that calls APIs) |
| O4 | LangGraph / state-machine fixed sequence |
| O5 | Hybrid: graph of stages, tools only inside a stage |

## Product / adjacent supply (P2, P3, P4, P9, P10)

| ID | Candidate |
| --- | --- |
| P2 | One product at a time |
| P3 | Embedding-neighbor products |
| P4 | Agent search products on demand |
| P9 | Hybrid: neighbors + agent search |
| P10 | Cluster batch by embedding; one call per cluster |

**Supply “good” looks like:** category-assign quality vs tokens/item; recall of true substitutes in context.

**Excluded from experiments:** P1, P5, P6, P7, P8 (see `kill-pile.md`).

## Related explore (lock later, not now)

| Area | Candidates | Notes |
| --- | --- | --- |
| Parse | R1, R2, R5, R6 | Structured out vs tool/CLI args SoT; retry; deterministic validators |
| Persist path | D1 vs D2 | Agent save vs orchestrator-after-validate |
| Assign timing | A2 vs A3 | After category confirmed vs deferred batch |
| HITL surfaces | H1 + H2 | Both required directionally; UI depth TBD |
| Category context maturity | C4 | Defer until C2 + eval harness exist |

Full ratings and notes: adopted companion `morphological-matrix.md`.
