---
name: plan-task.local
description: Interactive planning workflow for upper-small to large development tasks. Produces a committed dev-plan document under docs/plans/ that is ready to hand off as prompt material to a coding agent. Use when the user asks to "plan a task", "scope a feature", "draft an implementation plan", "prep work for another agent", or anything similar before code is written. Not for one-line fixes.
---

# plan-task.local

Interactive planning workflow for upper-small to large development tasks. The output is a committed dev-plan document that another coding agent can pick up and implement with minimal additional context.

## When to use

- User asks to plan, scope, design, or prep a development task.
- Task feels bigger than a trivial fix (crosses files / packages / requires decisions).
- User mentions handing off work to another agent.

## When NOT to use

- One-line or mechanical fixes (typos, rename, bump a constant) → skip planning, just do it.
- Pure research questions with no implementation target → use a research report instead.
- Incident response / hotfixes → use the repo's debug/incident workflow if one exists.

If relevant package `README.md` files and root `AGENTS.md` are not already in context, read them before planning.

## Inputs and Outputs

- **Input**: free-form user request, optional ticket/issue link, optional rough sketch.
- **Output**:
  - `docs/plans/YYYYMMDD-<main-component>-<slug>.md` — the dev-plan (committed), where `<main-component>` is the main package/module/service affected (use a name from the repo, not a guessed label).
  - `docs/plans/YYYYMMDD-<main-component>-<slug>-post-mortem.md` — optional, filed after execution.
- **Companion files in this skill** (if present):
  - [TEMPLATE.md](TEMPLATE.md) — the dev-plan template.
  - [PITFALLS.md](PITFALLS.md) — optional pitfall bank for step 6. Prefer a repo-local pitfalls doc if orientation docs point to one; otherwise use this companion or the generic list only.

## Interaction style

Prefer the agent harness' structured prompt tools (e.g. Cursor's `AskQuestion`) when asking the user to choose between discrete options. Fall back to conversational chat when the question is open-ended or when the tool is unavailable.

- **Prefer multiple choice** — offer 2–4 concrete options rather than open-ended questions when possible.
- **Lead with your recommendation** — state which option you'd choose and why before asking.
- **Keep rounds short** — ≤5 items in a structured prompt; in chat, prefer one question at a time.
- **Present 2–3 approaches** before settling on a direction — briefly name trade-offs; don't pick alone on hard calls.

## The 11 steps

Copy this checklist into your working context and tick items as you go.

```
Plan progress:
- [ ] 1. Understand the request
- [ ] 2. Interactive discovery
- [ ] 3. Simplification check
- [ ] 4. Confirm scope
- [ ] 5. Codebase exploration
- [ ] 6. Pitfall analysis
- [ ] 7. Technical decisions
- [ ] 8. Finalize task document
- [ ] 9. Plan review
- [ ] 10. Hand-off
- [ ] 11. (optional) Post-mortem filing
```

### 1. Understand the request

- Restate the request in your own words in 2–4 bullets.
- Identify the primary package(s) / service(s) / module(s) touched, using concrete names from the repo.
- Surface any attachments: ticket/issue, spec doc, Figma, chat thread, screenshots.
- Stop here if the request is ambiguous about user, value, or outcome. Ask in step 2.

### 2. Interactive discovery

Ask the user whatever is needed to unambiguously size and scope the work. Typical questions:

- Target users / personas and the value they get.
- Success criteria: what must be true when the task is "done"?
- In-scope vs out-of-scope (explicit non-goals).
- Environments: local/dev only, staging, production?
- Hard constraints: deadlines, compatibility, downtime tolerance, security/compliance.
- Preferred approach, if any (user may already have an opinion).
- Whether this plan will be executed by a specific agent model or by a human.

Follow **Interaction style** above for how you ask. Typical flow: recommend → options with trade-offs → user picks → next question.

**Source exploration stays off-limits until step 5**, with two exceptions:

- Reading orientation docs (`AGENTS.md`, package `README.md`s, and specs those point to) is always fine.
- **Bounded factual lookups**: if those docs don't answer a specific fact needed to size or scope (e.g. "what columns does table X have?", "what does the current settings screen show?"), do one or two targeted searches — a single grep, reading one specific file, or a natural follow-up (grep to find the file, then read it). If finding the answer needs more than that, or means following code flow across files, defer to step 5.

### 3. Simplification check

Before diving deeper, challenge the task:

- Is there a materially smaller version that delivers 80% of the value?
- Can it be split into a trivial first PR + a follow-up?
- Is there an existing feature that already solves this with config?
- Are any requirements nice-to-have that can be deferred?

Then explicitly ask the user:

> "Given these simpler options, do you want to: (a) proceed with the full plan, (b) downshift to a light plan (inline answer, no committed doc), or (c) adjust scope and continue?"

If the user picks **(b) light plan**, skip to an inline summary: goal, 3–7 bullet approach, risks, acceptance criteria. Do not create a plan document. Stop the workflow here.

### 4. Confirm scope

Write a short scope lock-in block and get explicit user confirmation before doing any exploration. This avoids wasting tokens on wrong exploration.

```
SCOPE LOCK-IN
- Goal: ...
- In scope: ...
- Out of scope: ...
- Primary packages/services: ...
- Success criteria: ...
Confirm? (yes / adjust)
```

Only proceed on a "yes" or equivalent.

### 5. Codebase exploration

Map the actual code that will be touched. Pick whichever tools fit the question:

- Needle queries ("where is `FooService` defined?") → `Grep` / `Glob` / `Read`.
- Broad/unclear scope ("how does this pipeline work?") → semantic search, or launch an `explore` subagent for a thorough sweep.
- Runtime behaviour → use whatever log/observability path the repo documents (service logs, local log dirs, MCP tools, dashboards). Don't invent a logging setup.
- API contracts → follow paths from orientation docs (OpenAPI/specs under `docs/`, package READMEs, etc.).
- DB / schema → follow paths from orientation docs (migrations dir, generated types, schema files).

Produce (kept in your own notes, distilled into the plan later):

- File inventory: files that will be created / modified / deleted.
- Call graph sketch for the changed code path.
- Data/state changes: migrations, env vars, feature flags, generated types.
- External touch points: other packages/services, public APIs, SDKs, CMS, IaC.

### 6. Pitfall analysis

**Blast radius / consumer tracing (do this first).** For every data structure, API/response shape, schema column, config key, event/queue payload, or external-system setting this plan changes, enumerate *who else reads, derives from, or displays it* across the codebase. Trace actual consumers; don't rely on a fixed checklist of surfaces. Treat each ripple as a **scope decision and raise it to the user** (include now vs deliberate follow-up) rather than discovering it at implementation or PR time.

Then run both lists:

**Generic pitfalls (always check):**

- Hidden coupling: callers, tests, snapshots, mocks, fixtures.
- Backward compatibility of public APIs, events, queue payloads, DB columns.
- Auth / authz regressions on touched endpoints.
- Performance cliffs: N+1, unbounded lists, blocking calls on hot paths.
- Error handling: what happens on timeout, partial success, retries.
- Security: secrets, PII, untrusted input, SSRF, injection.
- Observability: logs/traces/metrics for the new path.
- Tests: coverage for the changed behavior + the regression path.
- Rollout reversibility: can we revert without data loss?

**Repo-specific pitfalls:** if a pitfalls doc exists (companion [PITFALLS.md](PITFALLS.md), or a path named in orientation docs), filter to the ones relevant to the packages/services identified in step 1. Skip this sub-step if none exists.

For each real pitfall (and each blast-radius ripple you keep in-scope), write a one-liner in the plan describing mitigation or an explicit "accepted risk" / "follow-up".

### 7. Technical decisions

For every non-trivial choice, record:

- Decision.
- Options considered (2–3 is plenty).
- Why this option was picked.
- Rejected-because bullets for the others.

Candidates: framework/library, data model shape, sync vs async, feature-flag vs branch, unit vs integration test level, release/rollout tagging if the repo uses it, etc.

For architectural choices that outlive the PR, point to a future ADR in `docs/decision_records/` rather than embedding the full analysis in the plan.

### 8. Finalize task document

Create `docs/plans/YYYYMMDD-<main-component>-<slug>.md` using [TEMPLATE.md](TEMPLATE.md) if present; otherwise use a clear section structure covering goal, scope, approach, file inventory, pitfalls, decisions, rollout, and acceptance criteria. Rules:

- `YYYYMMDD` = today's date in the user's local timezone (from user_info / system clock).
- `<main-component>` = short kebab-case name of the primary package/module/service.
- `<slug>` = short kebab-case feature name (e.g. `playback-resume`, `invoice-pdf`).
- Every section filled or explicitly marked `N/A`.
- No secrets, no copy-pasted `.env` values, no raw PII beyond public ticket IDs.
- Prefer links over duplication (ticket links per user/repo rules, existing spec files, ADRs).
- Keep it skimmable: a senior engineer should get the plan in under 5 minutes.

**Tests.** Most tasks warrant automated tests; docs-only / pure lint / no-behavior bumps may not — if not, say so explicitly. When they do, list a few that assert *product decisions*, not coverage for its own sake. Tag each as:

- **core** — when X, then Y
- **boundary** — when X but Z, then W (only real product edges)
- **invariant** — X must never cause Q

If you can't name which decision a test protects, drop it. Use frameworks and paths already in the touched packages.

### 9. Plan review

If a `plan-reviewer` (or equivalent) subagent exists in this environment, launch it against the plan with fresh context (no planning conversation). Ask it to look for technical holes only — not product scope or priorities:

- Missing / impossible state branches
- Race, retry, or partial-failure gaps
- Unenforced cross-call-site invariants (things N places must each remember)
- Public-contract or generated-type drift
- For each Critical finding: whether at least one proposed test would catch it

Address findings (fix or keep with a concrete reason). One re-review after fixes is enough unless the user wants more; do not spin on endless FAIL loops.

If no such agent exists, self-review with this checklist:

- [ ] Goal and success criteria are testable.
- [ ] Scope lock-in matches what's actually described.
- [ ] File inventory lists concrete paths, not vague areas.
- [ ] Each pitfall has a mitigation or accepted-risk.
- [ ] Technical decisions are captured with rejected alternatives.
- [ ] Rollout/rollback path is explicit.
- [ ] Acceptance criteria map 1:1 to verifiable steps.
- [ ] Proposed tests (if any) map to product decisions (core / boundary / invariant), not vague coverage.
- [ ] No ambiguous pronouns ("it", "this") without antecedent.
- [ ] No TODO/TBD left unresolved (or they are explicit open questions for the executor).

Then show the plan (and any reviewer findings you kept or fixed) to the user and ask for approval or edits.

### 10. Hand-off

Output a hand-off block designed as **prompt material for another coding agent**:

```
HAND-OFF PROMPT (copy into new agent session)
- Plan: docs/plans/YYYYMMDD-<main-component>-<slug>.md
- Primary packages/services: <list>
- Start by reading: <plan path>, then <key source files>
- Non-negotiables: <top 3 from the plan>
- First concrete action: <e.g. "write failing test X in path Y">
- Done when: <top-level acceptance criterion>
```

Also tell the user:

- The exact path of the committed plan.
- Whether a separate ticket/issue update is expected (follow user or repo rules for the tracker in use).
- Any open question that blocks the executor.

### 11. (Optional) Post-mortem filing

Triggered explicitly by the user after the task is executed (merged / shipped / abandoned). Create `docs/plans/YYYYMMDD-<main-component>-<slug>-post-mortem.md` as a sibling to the plan. Keep it short:

- What actually shipped vs the plan (delta).
- What took longer or shorter than expected, and why.
- Pitfalls that materialized, and any new pitfalls discovered → propose updates to the repo/companion pitfalls doc if generalizable.
- Reusable snippets / commands / patterns worth extracting into a skill or doc.
- Follow-ups: new backlog items, tech debt, owner, priority.

Commit the post-mortem in the same PR as any follow-up docs updates.

## Do's and Don'ts

- **DO** confirm scope before exploring — cheap course-corrections.
- **DO** prefer existing repo conventions (commit style, hooks, codegen, CI scripts — whatever orientation docs specify).
- **DO** link out to existing specs/docs rather than copy/paste.
- **DON'T** ship a plan without an acceptance-criteria section — the executor will drift.
- **DON'T** hide decisions in prose. Use the decisions section.
- **DON'T** bypass pre-commit/hooks or suggest `--no-verify` in the plan unless the user explicitly allows it.
- **DON'T** include secrets or raw customer data, even if the ticket does.

## Verification checklist

- [ ] Plan file path follows `docs/plans/YYYYMMDD-<main-component>-<slug>.md`.
- [ ] All 11 steps were at least considered (step 11 may be deferred).
- [ ] User explicitly approved the scope lock-in (step 4) and the final plan (step 9).
- [ ] Hand-off block present and self-contained.
