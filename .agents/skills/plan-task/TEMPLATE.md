# Dev Plan: <Title>

- **Date**: YYYY-MM-DD
- **Author**: <name or handle>
- **Status**: Draft | Approved | Executing | Done | Abandoned
- **Primary services**: e.g. `backend`, `scripts`
- **Related specs / ADRs**: links only

## 1. Problem

What problem are we solving, for whom, and why now? 2–5 sentences max.

## 2. Goals and non-goals

**Goals**

- Measurable outcome 1
- Measurable outcome 2

**Non-goals**

- Explicit thing we are *not* doing in this task

## 3. Success criteria

Testable, unambiguous. These become the acceptance criteria the executor verifies.

- Given ... when ... then ...
- Artifact: code change / docs / both / none
- Validation: automated test / manual step / peer review

## 4. Scope lock-in

Copy the block from step 4 of the skill, as approved.

## 5. Approach

High-level solution in prose + bullets. Include sequence of changes if ordering matters.

### 5.1 File inventory

- Create: `path/to/new.ts`
- Modify: `path/to/existing.ts` (what changes, conceptually)
- Delete: `path/to/old.ts`
- Migrations: `backend/migrations/versions/XXX_xxx.py` (if any)

### 5.2 Data / contract changes

- API changes (OpenAPI, events, webhooks) — include backward-compat notes.
- DB schema changes — include up/down migration plan.
- Env vars, feature flags, secrets — where and who owns them.

### 5.3 External touch points

- Other packages/services, SDKs, CMS, IaC, third-parties.
- Any coordination required (who to notify, when).

## 6. Pitfalls and mitigations

One row per real pitfall. Delete rows that don't apply.

| Pitfall | Impact | Mitigation | Owner |
| --- | --- | --- | --- |
|  |  |  |  |

Accepted risks (explicitly chosen to live with):

- ...

## 7. Technical decisions

### Decision: <short name>

- **Choice**: ...
- **Options considered**: A, B, C
- **Why**: ...
- **Rejected because**: A — ..., B — ...

Repeat per decision. For durable architectural decisions, create an ADR under `docs/decision_records/` and link here.

## 8. Testing strategy

- Unit: what gets covered, roughly which files.
- Integration / e2e: flows, environments, fixtures.
- Manual: steps, if any, with expected results.
- Regression guard: the specific scenario that must not break again.

## 9. Observability

- Logs to add/keep (structured, `trace_id`).
- Metrics / alarms touched.
- Trace scope / tags if relevant.

## 10. Rollout and rollback

- Data migration plan, including backfill and ordering with deploy.
- Rollback path: steps, data implications, time to revert.

## 11. Open questions

- Q1 — owner, blocking/non-blocking.
- Q2 — ...

## 12. Hand-off block

Paste the step-10 hand-off prompt here, so the executor sees it inline when they open the plan.

```
HAND-OFF PROMPT
- Plan: docs/plans/YYYYMMDD-<main-component>-<slug>.md
- Primary packages/services: ...
- Start by reading: ...
- Non-negotiables: ...
- First concrete action: ...
- Done when: ...
```

## 13. Changelog

- YYYY-MM-DD — initial draft
- YYYY-MM-DD — scope tightened after review
