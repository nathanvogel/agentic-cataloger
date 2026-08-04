# Deferred page — UX spec

Coded mockup: [`docs/mockups/deferred-list.html`](../mockups/deferred-list.html).

Condensed from BMAD's UX design/experience spines (now deleted). One read-only operator page onto the `deferred_items` table — see [architecture.md § Non-blocking human review](architecture.md#non-blocking-human-review). Purpose: let an operator (or an interviewer looking over their shoulder) see *where the agent is failing*, without pretending this is a review console.

## Role & scope

- Single route, desktop-first responsive web. Not a native app, not a dashboard suite.
- Read-only. No edit controls, no bulk actions, no drag-and-drop, no status transitions from the UI, no assignment, no comments. Re-drive exists only as a CLI command hitting the same command handler the pipeline uses — deliberately outside this surface.
- No auth UI (security is out of scope for this initiative), no settings, no charts/KPI strips/health scores.
- If this page ever goes unused, it should be easy to delete — Phoenix + `SELECT * FROM deferred_items` remain the fallback.

## Visuals

Light mode only. Cool neutrals, one ink primary, one warm accent reserved for "Open trace" only.

| Token | Value | Use |
| --- | --- | --- |
| background | `#F7F6F3` | page |
| surface | `#FFFFFF` | rows, expanded detail |
| surface-muted | `#EEF0F2` | expanded-detail fill |
| on-surface / on-surface-muted | `#1A1D21` / `#5C6570` | text |
| border / border-strong | `#D5DAE0` / `#9AA3AD` | dividers, filter outline |
| primary | `#1F4B63` | header emphasis, active filter chip |
| accent | `#C45C26` | "Open trace" link only |
| reason: unknown | `#8A6D1F` on `#F5EED8` | |
| reason: defer | `#1F4B63` on `#E4EEF3` | |
| reason: low_confidence | `#6B4F7A` on `#EFE8F3` | |

Type: IBM Plex Sans for chrome/titles/body/product names; IBM Plex Mono for machine values (IDs, reason codes, stage names, trace IDs, timestamps, payload JSON). Display type is restrained — 28px/600, not a marketing hero. Tight radii (2–6px; pill/`full` for chips only). No drop shadows, no elevation as hierarchy, no purple/indigo AI gradients, no emoji status, no dark mode.

## Layout

Single column, ~1100px max width. Header → filter bar → list. Expanding a row opens detail **in-row** (never a modal) so list context stays visible. On narrow viewports, filters wrap and row metadata stacks under the product name.

## Components

- **Page shell** — product name in display type + "Deferred", an open-count in muted mono (e.g. `7 open`), a manual Refresh control. No sidebar, no multi-page shell.
- **Filter bar** — stage filter and reason filter, each single-select, ANDed together; clearing returns to "all". Filter state lives in URL query params (`?stage=&reason=`) so a filtered view is shareable/bookmarkable.
- **Deferred row** — full width, flat, 1px border: product name (sans) + retailer/id (mono) · stage (mono) · reason chip · attempt count · relative time · "Open trace" link. Sorted newest first. Whole row expands/collapses on click or Enter; row chips are display-only (only filter-bar chips filter).
- **Expanded detail** — indented, `surface-muted` fill: read-only payload snapshot (mono, truncated with a "Show more"), the `evidence_span` if present, and the Phoenix trace URL. Never editable.
- **Open trace** — "Open trace" + mono `trace_id` in accent color, opens a new tab, click stops propagation so the row doesn't also toggle. Missing `trace_id` → disabled control with muted "No trace"; row still shows.
- **Empty state** — centered one-liner, no illustration, no CTA. Distinguish "no deferred items at all" from "no items match these filters" (latter gets a clear-filters control).

## States

| State | Treatment |
| --- | --- |
| Loading | skeleton rows matching row anatomy |
| Load error | inline "Couldn't load deferred items." + Retry |
| Stale | manual Refresh only — no websocket/polling in MVP |
| Missing trace | Phoenix control disabled, row still shown |
| Long payload | truncate + "Show more", never a modal |

## Interaction & accessibility (keep it light)

- Filters apply immediately and reflect in the URL.
- Reason codes and stage names render exactly as stored (`unknown`, `defer`, `low_confidence`, `assign`, `extract`, ...) — no euphemisms, no invented labels.
- Basic accessibility floor: `aria-expanded` on the row toggle, reason/stage conveyed as text (not color alone), visible focus ring, external Phoenix link announces it opens a new tab.
- Keyboard shortcuts (`j`/`k` row focus, `Enter` toggle, `o` open trace) are a nice-to-have — implement only if the basic list+filter+expand flow is done first.

## Reference flow

An operator finishes a filtered ingest, opens Deferred, filters by stage, sees the failure pattern cluster on one reason code, expands a row to check the payload/evidence, and opens the Phoenix trace to confirm the prompt — all without leaving the list. That's the whole point of the page: surfacing *where* the agent fails, not managing a queue.
