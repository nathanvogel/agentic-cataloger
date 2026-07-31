---
name: pricecomp Deferred
description: Minimal operator surface for inspecting agent deferred items — portfolio-presentable, deliberately thin.
status: final
updated: 2026-07-31
sources:
  - _bmad-output/specs/spec-2026-agent-workflow/SPEC.md
  - _bmad-output/specs/spec-2026-agent-workflow/glossary.md
  - docs/specs/2026-scope.md
colors:
  background: '#F7F6F3'
  surface: '#FFFFFF'
  surface-muted: '#EEF0F2'
  on-surface: '#1A1D21'
  on-surface-muted: '#5C6570'
  border: '#D5DAE0'
  border-strong: '#9AA3AD'
  primary: '#1F4B63'
  on-primary: '#FFFFFF'
  accent: '#C45C26'
  on-accent: '#FFFFFF'
  reason-unknown: '#8A6D1F'
  reason-unknown-bg: '#F5EED8'
  reason-defer: '#1F4B63'
  reason-defer-bg: '#E4EEF3'
  reason-lowconf: '#6B4F7A'
  reason-lowconf-bg: '#EFE8F3'
  link: '#1F4B63'
  focus-ring: '#1F4B63'
typography:
  display:
    fontFamily: 'IBM Plex Sans'
    fontSize: 28px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: '-0.02em'
  title:
    fontFamily: 'IBM Plex Sans'
    fontSize: 18px
    fontWeight: '600'
    lineHeight: '1.3'
  body:
    fontFamily: 'IBM Plex Sans'
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
  label:
    fontFamily: 'IBM Plex Sans'
    fontSize: 12px
    fontWeight: '500'
    lineHeight: '1.4'
    letterSpacing: '0.04em'
  mono:
    fontFamily: 'IBM Plex Mono'
    fontSize: 12px
    fontWeight: '400'
    lineHeight: '1.45'
rounded:
  sm: 2px
  md: 4px
  lg: 6px
  full: 9999px
spacing:
  unit: 8px
  gutter: 24px
  margin-desktop: 32px
  margin-mobile: 16px
  content-max: 1100px
components:
  page-shell:
    background: '{colors.background}'
    foreground: '{colors.on-surface}'
  deferred-row:
    background: '{colors.surface}'
    border: '{colors.border}'
    radius: '{rounded.md}'
  reason-chip:
    radius: '{rounded.full}'
    typography: '{typography.label}'
  phoenix-link:
    color: '{colors.accent}'
    typography: '{typography.mono}'
  filter-chip:
    border: '{colors.border-strong}'
    radius: '{rounded.full}'
    typography: '{typography.label}'
---

# pricecomp Deferred — Design Spine

Paired with `EXPERIENCE.md`. Spines win on conflict with mocks or imports.

→ Composition reference: `mockups/deferred-list.html`.

## Brand & Style

**pricecomp Deferred** is a single-purpose operator view: show what the agent deferred so a human can see *where the pipeline fails*. Hobby-scale in scope, **portfolio-presentable** in craft — quiet, technical, intentional. Not a marketing site; not a dashboard of cards.

Aesthetic posture: **technical ledger**. Dense enough to scan failure patterns; spare enough that an interview screenshot still reads as deliberate. The product name is the strongest brand mark in the header — chrome stays subordinate.

Cool neutrals, one ink primary, one warm accent reserved for “Open trace.” IBM Plex Sans/Mono. Light mode only for MVP.

## Colors

- **Background (`#F7F6F3`)** — warm-neutral paper; long scan sessions without clinical white or cream-editorial tone.
- **Surface (`#FFFFFF`)** — deferred rows and expanded detail.
- **Primary ink (`#1F4B63`)** — header emphasis, active filters. Means “this tool.”
- **Accent (`#C45C26`)** — Phoenix deep-link only. Means “leave this UI for the trace.”
- **Reason chips** — muted fills for `unknown` / `defer` / `low_confidence` so stage×reason patterns read at a glance without traffic-light drama.
- **Muted text / borders** — hierarchy and separators only.

Avoid: purple/indigo AI gradients, glow, multi-shadow elevation, dark-mode-first chrome, emoji status.

## Typography

- **IBM Plex Sans** — UI chrome, titles, body, product names.
- **IBM Plex Mono** — product IDs, reason codes, stage names, trace IDs, timestamps, payload JSON.
- Display is restrained (28px / semibold) — product name + page title, not a marketing hero.

## Layout & Spacing

Single column, `{spacing.content-max}` (~1100px). Header → filters → list. Expanded detail opens **in-row**, not a modal, so list context stays visible.

Desktop-first. On narrow viewports, filters wrap and row metadata stacks under the product name. Readable on mobile; not designed as a mobile product.

## Elevation & Depth

None as hierarchy. Rows are flat with 1px `{colors.border}`. Expanded row uses `{colors.surface-muted}` fill only. No drop shadows.

## Shapes

Tight radii (`2–6px`). Chips use `{rounded.full}` for reason/filter only. No large card radii, no floating panels.

## Components

| Component | Visual spec |
|---|---|
| **Page shell** | `{colors.background}`; header with product name (`{typography.display}`) + “Deferred”; open-count in muted mono; Refresh control. |
| **Filter chip** | Outline `{colors.border-strong}`; active fill `{colors.primary}` / `{colors.on-primary}`. Stage and reason only. |
| **Deferred row** | Full-width: product name (sans) + supermarket/id (mono) · stage (mono) · reason chip · attempts · relative time · Phoenix link. |
| **Reason chip** | Pill; color by reason token set. Text is the reason code string. |
| **Expanded detail** | Indented under row: payload snapshot (mono), optional `evidence_span`, Phoenix URL. No edit controls. |
| **Phoenix link** | “Open trace” in `{colors.accent}` + mono `trace_id`. External only. |
| **Empty state** | Centered short sentence; no illustration; no CTA (pipeline creates items). |

## Do's and Don'ts

**Do**

- Make failure *pattern* scannable: stage × reason visible without opening every row.
- Keep the product name as the strongest brand mark on the page.
- Prefer monospace for machine values; sans for human-readable product titles.
- Design so the surface can be deleted later without orphaning a design system.

**Don't**

- Don't build a multi-page app shell, sidebar nav, or settings for this MVP.
- Don't add charts, KPI strips, or “health score” widgets.
- Don't imply write actions while the experience is read-only.
- Don't restyle Phoenix; deep-link out and let Phoenix own the trace UI.
