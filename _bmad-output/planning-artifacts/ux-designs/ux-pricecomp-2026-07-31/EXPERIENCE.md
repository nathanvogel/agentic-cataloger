---
name: pricecomp Deferred
status: final
updated: 2026-07-31
sources:
  - _bmad-output/specs/spec-2026-agent-workflow/SPEC.md
  - _bmad-output/specs/spec-2026-agent-workflow/glossary.md
  - docs/specs/2026-scope.md
---

# pricecomp Deferred — Experience Spine

Visual tokens live in `DESIGN.md`; cross-refs use `{path.to.token}`. Spines win on conflict with any mock or import.

→ Composition reference: `mockups/deferred-list.html` (Deferred list + inline detail). Phoenix is external — spine-only.

## Foundation

**Form-factor:** desktop-first responsive web. Single route in the pricecomp operator web app (or a tiny standalone page) — not a native app, not multi-surface.

**UI system:** None mandated. Implement with whatever the Python monolith front-end chooses; this spine specifies behavior. Visual identity is entirely in `DESIGN.md`.

**Product role:** Read-only window onto `deferred_items` (SPEC H2 table; H1 reads from the same table). Purpose: *understand where the agent fails*. Not a review console with domain writes.

**Scope vs SPEC CAP-9 (reconciled 2026-08-01):** the SPEC's 2026-08-01 scope reduction adopted this read-only posture — CAP-9 now requires a read-only dashboard plus a CLI re-drive command, and reviewer domain writes (reassign leaf, edit trait, accept/reject evidence) are deferred. This spine and the SPEC agree; no sync debt remains. Evolution: grow into actionable H1 when the queue proves worth acting on in-app, replace with another workflow, or drop if unused. Trace inspectability stays in Phoenix (SPEC non-goal: no custom E4 run UI).

## Information Architecture

| Surface | Reached from | Purpose | Mock |
|---|---|---|---|
| **Deferred list** | App open / “Deferred” | Scan open deferred items; filter by stage and reason | `mockups/deferred-list.html` |
| **Row detail (inline)** | Expand a list row | Payload snapshot, evidence context, Phoenix deep link | same mock (expanded row) |
| **Phoenix (external)** | “Open trace” | Full run/trace UI — out of this product’s chrome | spine-only |

No other surfaces in MVP: no settings, no auth UI (security out of scope per SPEC), no analytics, no bulk-action tray.

IA closure: “see deferred actions / where it fails” → Deferred list + row detail; Phoenix covers deep inspectability.

## Voice and Tone

Microcopy only. Brand posture lives in `DESIGN.md`.

| Do | Don't |
|---|---|
| “12 deferred” | “Attention needed!!! 🚨” |
| “No deferred items. Last ingest completed without deferrals.” | “You're all caught up! Great job.” |
| Reason codes as stored (`unknown`, `defer`, `low_confidence`) | Soft euphemisms (“needs a look”) |
| “Open trace” | “View AI insights” |
| Stage names matching pipeline (`assign`, `extract`, …) | Invented UI stage labels |

## Component Patterns

Behavioral. Visuals → `DESIGN.md` Components.

| Component | Use | Behavioral rules |
|---|---|---|
| **Deferred row** | List | Entire row expandable (click/Enter). Does not navigate away. Sort: newest first. |
| **Reason chip** | Row | Display-only on the row. Filter-bar chips filter; row chips do not. |
| **Stage filter** | Filter bar | Single-select. Clearing returns to all stages. |
| **Reason filter** | Filter bar | Single-select. AND with stage. |
| **Open trace** | Row / detail | New browser tab. Missing `trace_id`/URL → disabled + muted “No trace”. |
| **Payload snapshot** | Detail | Read-only monospace. Truncate long JSON; “Show more” expands in place. Never editable. |
| **Empty state** | List | Distinguish globally empty vs filtered-empty copy. |

## State Patterns

| State | Surface | Treatment |
|---|---|---|
| Loading | Deferred list | Skeleton rows matching row anatomy. |
| Empty (true) | Deferred list | “No deferred items.” + one line that ingest may still create them. |
| Empty (filtered) | Deferred list | “No items match these filters.” Control to clear filters. |
| Missing trace | Row | Phoenix control disabled; row remains. |
| Stale list | Deferred list | Manual Refresh in header; no websocket in MVP. |
| Error load | Deferred list | “Couldn’t load deferred items.” + Retry. |
| Long payload | Detail | Truncated with expand; never modal. |

## Interaction Primitives

- **Click / Enter** on row → expand/collapse detail.
- **Click** “Open trace” → new tab (stop propagation so row doesn’t toggle).
- **Filters** → immediate filter; state in URL query params (`?stage=&reason=`) for shareable portfolio demos.
- **Keyboard:** `j`/`k` move focus between rows; `Enter` toggles; `o` opens Phoenix when focused.
- **Banned in MVP:** drag-and-drop, bulk select, inline edit, status transitions from the UI, assignment, comments.

## Accessibility Floor

- Text contrast meets WCAG 2.2 AA against `{colors.background}` / `{colors.surface}` (verify reason-chip pairs).
- Expand/collapse exposes `aria-expanded`; detail region labeled.
- Reason and stage conveyed as text, not color alone.
- Focus ring uses `{colors.focus-ring}`.
- External Phoenix link announces as opening in a new window.

## Responsive & Platform

| Breakpoint | Behavior |
|---|---|
| Desktop (primary) | Single column ≤1100px; row grid shows all columns. |
| Narrow | Filters wrap; row metadata stacks under product name. |

Web only. Not a native mobile app.

## Key Flows

### Flow 1 — After ingest, find the failure pattern (Nathan, solo builder, portfolio demo)

1. Nathan finishes a filtered ingest of Coop dairy SKUs. Pipeline completes without blocking.
2. He opens **Deferred**. Header shows “Deferred” and a mono count, e.g. `7 open`.
3. He filters stage → `extract`. List shrinks; reasons cluster on `unknown`.
4. He expands one row: payload shows quantity fields the agent refused to invent; `evidence_span` empty.
5. **Climax:** Without leaving the list, he sees the pattern — extract/unit failures, not assign mistakes. He opens one Phoenix trace to confirm the prompt, then closes the tab. Deferred remains his map of *where* the agent fails.

Failure: list API errors → inline Retry; the interview narrative still works from honest empty/error states.

### Flow 2 — Interview walkthrough (Nathan presenting to a hiring manager)

1. Nathan loads a bookmark with `?stage=assign&reason=low_confidence` already applied.
2. Rows show products the agent deferred rather than forcing a leaf.
3. He expands a row, narrates reason code and stage, clicks **Open trace**.
4. **Climax:** Phoenix shows the tool calls; Deferred showed the queue. Two tools, one story: non-blocking HITL + inspectability — without claiming a full review console.

Failure: Phoenix link missing on a demo fixture → disabled control; payload snapshot still completes the story.

## Concern scan (MVP)

| Concern | Stance |
|---|---|
| Accessibility | AA floor; portfolio screenshots stay readable. |
| Platforms | Web desktop-first only. |
| Brand | Presentable minimal ledger; disposable if unused. |
| Motion | Optional ~150ms expand; no celebration motion. |
| i18n | English only. |
| Dark mode | Out. |
| Offline | Out; show load error. |
| Notifications | Out — operator comes to the page. |
| Content density | High — ledger, not cards. |
| Auth | Out of scope per SPEC security non-goal. |

## Open / evolution

- **Later:** domain actions per the deferred CAP-9 writes may land here or replace this surface.
- **Exit:** if unused, delete the route; Phoenix + SQL on `deferred_items` remain.
- **Re-drive:** exists in MVP as a CLI command against the same application command handler, deliberately outside this surface.
