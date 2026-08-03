---
name: plan-task
description: Two-phase planning process (Product Definition and Technical Specification) for features. Use when the user asks "what should I work on next", asks you to plan a feature, asks to add or modify functionality across packages/services, or wants to convert a backlog entry into an actionable spec.
---

# Task Planning

## IMPORTANT: Planning Process Guidelines

**Phase 1 (Product Definition) focuses on understanding user needs and product behavior without diving into code details.** Phase 2 (Technical Specification) includes thorough codebase exploration to understand implementation details, edge cases, and technical constraints.

**ITERATIVE DOCUMENTATION:** Create the task `.md` file early — as soon as you understand the broad product strokes. Update the document incrementally as questions are answered and clarity is gained. Don't wait until the end to write everything at once. Add or remove content based on decisions made during the conversation.

## Discover Project Context

Do **not** assume a fixed product, service list, or stack. At the start of every planning session, load the repo's own orientation docs and treat them as authoritative:

1. Resolve `<repo_root>` (see Path Conventions).
2. Read, in order as they exist: `<repo_root>/CLAUDE.md`, `<repo_root>/AGENTS.md`, `<repo_root>/README.md`.
3. From those docs (and any paths they point to), note:
   - Product / system purpose in one sentence
   - Packages, services, or top-level modules and what each owns
   - Language/runtime conventions and where code-style specs live
   - Auth, data stores, queues, billing, observability, public APIs — whatever this repo actually has
   - Default branch name (usually `main`; confirm via `git symbolic-ref refs/remotes/origin/HEAD` or remote tracking)
4. Prefer concrete names from the repo (`path/to/pkg`, CLI commands, table names) over inventing parallel vocabulary.

If orientation docs are thin or missing, say so briefly and rely on directory layout + targeted questions in Phase 1 — do not invent a services table.

## Path Conventions

Throughout this skill, `<repo_root>` refers to the main repository root, resolved at invocation time via `git rev-parse --show-toplevel` from the planner's working directory. The planner runs from the main checkout, so this resolves correctly for reads like `<repo_root>/CLAUDE.md`. When constructing sub-agent prompts that reference repo files (e.g., a plan-reviewer prompt), interpolate the resolved absolute path before invoking — sub-agents should receive concrete paths, not the `<repo_root>` token.

`<default_branch>` is the repo's primary branch (typically `main`). Prefer the remote HEAD if discoverable.

## Planning Constraints

**These rules apply to both Phase 1 and Phase 2, without exception:**

- **Do not edit any files during planning** other than the task document in the worktree's `docs/plans/`. This includes source code, skill/agent files (`.agents/skills/`, `.agents/agents/`, `.cursor/skills/`), and process docs (`CLAUDE.md`, `AGENTS.md`, architecture/style specs). If the task is about improving one of these files, plan the change in the task document — do not make the edit now. (Orientation and style docs must be *read* during planning — the prohibition covers editing, not reading.)
- **Carve-out — flow gaps the work itself surfaces.** If planning (or implementing) *this* feature uncovers a gap in the planning flow or its tooling — a reviewer/agent definition, this skill, or a process doc — fix it **on this feature's branch so it ships in the same PR as the work that uncovered it**. Not on a separate branch, and not merely filed as a backlog item to do later. Record the bundled fix in the task document. This is the inverse of the unrelated-scope rule: a fix the work *surfaced* belongs with that work; an unrelated improvement still does not. (The "plan it, don't edit" rule above still governs when the feature **is** the process change itself.)
- **Backlog entries** in `docs/plans/backlog/` may be deleted (not edited) when the task originated from that backlog entry — see Step 5. If `docs/plans/backlog/` does not exist, skip backlog promotion rather than creating the tree unless the user asks.
- **Do not run builds or tests** during planning (whatever the repo's commands are: `yarn test`, `npm test`, `uv run pytest`, `cargo test`, etc.).
- **Do not run service / app dev servers** during planning.
- The feature branch and worktree are created during planning to version the spec — git commands for that purpose are permitted.

## Task Planning Process

When the user asks "what should I work on next" or asks you to plan a feature:

### Phase 1: Product Definition (No Code Exploration)

**MANDATORY:** At the start of Phase 1, create a todo list with one task per step below. Complete each task in order — mark it in progress before starting and completed when done. Do not skip ahead.

- [ ] **Step 1: Check Active Work & Backlog** — Run `git worktree list` to see what branches have active planning worktrees — those tasks are already in progress; don't surface them to the user. Then, if `docs/plans/backlog/` exists, list files there for previously noted items. Backlog filenames are dated (`YYYY-MM-DD-<slug>.md`); the bare `<slug>` is the identity used by branches, worktrees, and the active spec. **Filter the backlog by cross-referencing task docs:** for each active worktree (other than the main one), list the files in its `docs/plans/` directory. A backlog item is "claimed" if its filename stem (after stripping the leading `YYYY-MM-DD-` date) matches either (a) the slug portion of an active worktree path, or (b) a task filename stem found inside any active worktree's `docs/plans/`. Only suggest backlog items with no claimed match. If any are relevant or timely, suggest them alongside the user's request (or as options if they asked "what should I work on next"). Also check `git branch -r` and open PRs for in-flight work on similar areas — if the user's request overlaps, flag that before proceeding.

  **Backlog entries are not pre-validated specs.** They are written quickly, may contain wrong assumptions, incorrect file paths, or outdated analysis. A detailed-looking backlog entry does not mean planning can be abbreviated. The full planning process frequently reveals that the backlog entry's diagnosis is wrong, its scope is incomplete, or the proposed approach has issues. Treat every backlog entry as a starting hypothesis, not a finished plan.

- [ ] **Step 2: Review Project Context** — Follow **Discover Project Context** above. Use orientation docs to answer broad "does X already exist?" or "which package owns Y?" questions yourself. For deeper module-level context, read specs the orientation docs point to (architecture, API specs, domain notes). Reading those is required documentation review, not "source code exploration."

- [ ] **Step 3: Understand User Request** — Focus on the product or technical goal. What problem is being solved? Who experiences it?

- [ ] **Step 4: Interactive Discovery** — Ask ONE question at a time to clarify:
   - User/operator behavior (who triggers this, what do they see?)
   - Boundaries (which packages, services, or modules are touched?)
   - Data flow (where does the data originate, where does it live, who reads it?)
   - Scaling / concurrency concerns relevant to *this* product
   - Money / billing / quotas, if the product has them
   - Public contract impact (APIs, CLIs, schemas, embeds, or other external surfaces)
   - **Source code is off-limits during Phase 1, with two exceptions:**
     - Reading orientation docs (`CLAUDE.md`, `AGENTS.md`, `README.md`) and linked specs is always permitted — these are documentation, not source code.
     - **Bounded factual lookups**: if those docs don't answer a specific fact needed to scope the feature (e.g., "what columns does table X have?", "what does the current settings screen show?"), do one or two targeted searches — a single grep, reading one specific file, or a natural follow-up (e.g., grep to find the file, then read it). If finding the answer requires more than that, or involves following code flow between files, defer to Phase 2.
     - Everything else — implementation patterns, class hierarchies, code flow — is Phase 2 territory.
   - **Prefer multiple choice** — Offer 2-4 concrete options rather than open-ended questions when possible.
   - **Lead with your recommendation** — State which option you'd choose and why.
   - **Present 2-3 approaches** — Before settling on a direction, briefly present alternatives with trade-offs.

- [ ] **Step 5: Create Branch, Worktree, and Initial Task Document** — Once broad strokes are understood (after 1-2 discovery questions, not after all questions are answered):
   - Pick a short kebab-case slug for the feature (e.g., `ingest-selection`, `api-rate-limit`).
   - Ensure `.worktrees/` is gitignored in this repo; if not, add it on the feature branch as part of setup (or ask the user).
   - Create the feature branch and a native git worktree for spec authoring:
     ```bash
     git fetch origin <default_branch>
     git worktree add -b feature/<slug> .worktrees/<slug> origin/<default_branch>
     ```
     This is a native `git worktree` — lightweight, lives at `.worktrees/<slug>/`. The native worktree is a **spec-authoring + code + unit-test sandbox**: edits, commits, lint, typecheck, and unit tests usually work here. Shared local resources (DB, ports, containers) may still be shared with the main checkout — see **Implementation Handoff** for modes when isolation matters.
   - Create the task `.md` file **inside the worktree** at `.worktrees/<slug>/docs/plans/<slug>.md` with the objective and what's known so far. Create `docs/plans/` if missing.
   - Commit the task document from inside the worktree (single Bash call):
     ```bash
     cd .worktrees/<slug>
     git add docs/plans/<slug>.md
     git commit -m "docs(plan): add task spec for <slug>"
     ```
     During planning the commit message is short and structural — `docs(plan): add task spec for <slug>` is the standard form. If the repo has a dedicated commit agent/skill, use it for later implementation commits; planning commits may be direct.
   - If the task originated from `docs/plans/backlog/`, delete the corresponding `.md` file (it's dated, e.g. `2026-05-15-<slug>.md`) from the backlog on the feature branch and commit (single Bash call):
     ```bash
     cd .worktrees/<slug>
     git rm docs/plans/backlog/<YYYY-MM-DD-slug>.md
     git commit -m "chore(plan): promote <slug> from backlog"
     ```
     If `docs/plans/backlog/README.md` exists, follow its lifecycle notes.

- [ ] **Step 6: Continue Discovery & Refine Task Document** — Continue asking product questions (one at a time). After each answered question, update the task document and commit:
   - Add or remove content based on decisions — the document should reflect current understanding, not history of the conversation.
   - Commit spec updates from within the worktree directory as the spec evolves.
   - Clarify the user experience and operator experience.
   - Establish feature boundaries and scope (what's in, what's deferred).
   - Think of edge cases and places where the design might fail.

- [ ] **Step 7: Simplification Check** — Re-read the product spec and consider whether any part is over-designed. Look for:
   - Manual configuration that could be derived automatically.
   - A new system being proposed when an existing system could be extended.
   - A multi-step user workflow that could be collapsed into fewer steps.
   - A new dependency where an existing dependency already does the job.
   - If you find an obvious simplification, surface it to the user with a concrete suggestion. If nothing jumps out, move on silently — do not force output or ask a question.
   - Do not second-guess explicit decisions the user already made during discovery.

- [ ] **Step 8: Documentation Impact Check** — Evaluate whether this work changes anything an end user would go to the documentation to understand or implement, or anything a user's own coding agent would need in order to integrate with or use the product. Deliberately do **not** apply a fixed checklist of surfaces — what counts will change as the product grows. The test is whether the change alters how someone *outside the team* uses, integrates with, or reasons about the product. Prefer the repo's public/docs paths when orientation docs name them.
   - If there's no such impact, note "no public-facing impact" in the task doc and move on — don't ask a question.
   - If there is, ask the user (one question, in the discovery style) whether those docs need updating and which pages. Treat any resulting doc work as **part of this task's scope, not a follow-up**: it ships in the same PR as the change it describes, and goes in the task doc alongside the other changes (files to modify, acceptance criteria).
   - Documentation drift is silent — code review rarely catches a doc that simply wasn't written. This step is the checkpoint that surfaces it while the work is still being scoped.

- [ ] **Step 9: Review Product Scope** — Summarize the product definition and confirm understanding:
   - **MANDATORY:** Ask user: "Are you ready to proceed to technical specification?"
   - **STOP:** Wait for user confirmation before proceeding to Phase 2.

### Phase 2: Technical Specification (REQUIRES USER APPROVAL)
**CRITICAL:** Only proceed after explicit user confirmation from Phase 1.

**MANDATORY:** At the start of Phase 2, create a todo list with one task per step below. Complete each task in order — mark it in progress before starting and completed when done. Do not skip ahead.

- [ ] **Step 10: Deep Codebase Exploration** — Use an explore/sub-agent or direct search tools to study the codebase:
   - Identify the modules, packages, services, or components that will be touched.
   - Study existing patterns in the affected areas (framework wiring, data access, UI state, CLI structure — whatever applies).
   - **Study existing code style** — read the style/spec docs the orientation files name for the languages involved. Those are authoritative for naming, type safety, and anti-patterns.
   - For cross-cutting work, also read relevant supplementary specs (API, data model, observability, etc.) when they exist.
   - Update the task document with findings.

- [ ] **Step 11: Implementation Pitfall & Downstream-Impact Analysis** — Think deeply about what could go wrong, grounded in *this* codebase:
   - **Downstream impact / blast radius (proactive — surface to the user).** This is the internal-codebase counterpart to Step 8's external/docs impact check. For every data structure, API/response shape, schema column, config key, or external-system setting this plan changes, enumerate *who else reads, derives from, or displays it* across the codebase. A change is rarely local; treat each ripple as a **scope decision and raise it to the user** (include now vs. deliberate follow-up) rather than discovering it at implementation or PR time. Do **not** rely on a fixed checklist of surfaces — trace the actual consumers.
   - Race conditions and state synchronization across processes or services, if concurrency exists here.
   - Retry / idempotency hazards for webhooks, jobs, or external callbacks the repo uses.
   - Migration ordering and deploy coordination when schema or config must land in order.
   - Generated artifact drift (OpenAPI clients, ORM types, protobufs, etc.) — if the task touches generated files, note that the generator must run; the implementation agent must never hand-edit those outputs. If a generator can't run in this environment, that's a blocker to surface, not something to work around by approximating the output.
   - Hidden complexity that isn't obvious from the product requirements.

- [ ] **Step 12: Interactive Technical Discovery** — Bring technical questions to the user:
   - Don't make difficult technical decisions alone.
   - Present trade-offs clearly (simpler vs. cleaner boundaries, reuse vs. new abstraction, etc.).
   - Ask about integration approaches in terms of this repo's real seams.
   - Update the task document with each decision.

- [ ] **Step 13: Edge Case & Integration Analysis** — Examine existing implementations for integration challenges:
   - Identify potential bugs under failure, partial progress, or unexpected input.
   - Present found edge cases to the user and ask for preferred handling.
   - Document edge cases and their resolutions in the task file.

- [ ] **Step 14: Test Design** — Design the tests **if the change merits tests**. Most do, but some don't: docs-only edits, simple lint/format changes, dependency bumps without behavioral impact, or pure UI tweaks where existing tests still apply. If tests are not warranted, note that explicitly in the task doc and move on.

   When tests are warranted, frame each one as an **assertion about a product decision this task makes**, not a code-coverage exercise. For each decision the task introduces or changes, ask three questions:
   - **"When X, then Y"** (core behavior) — What should this feature do? These are the happy-path product decisions.
   - **"When X but Z, then W"** (boundary behavior) — What should happen under stress, unexpected input, or edge conditions? Only include boundaries that represent a real product decision — not defensive null checks for impossible states.
   - **"X must never cause Q"** (safety invariants) — What properties must remain true regardless of what happens? These protect against silent regressions. A good heuristic: if someone changed one line and this invariant broke, would a test catch it?

   List the resulting tests in the "How to Test" section. Each test should trace back to a specific product decision. If you can't articulate which decision a test protects, it probably shouldn't exist. Pick frameworks and file layouts that already exist in the touched packages — do not invent a new test stack in the plan unless the task explicitly includes that setup.

- [ ] **Step 15: Finalize Task Document** — Ensure the spec is complete:
   - Ensure the `.md` file in the worktree's `docs/plans/` reflects all decisions made.
   - Include code patterns to follow based on codebase exploration.
   - List specific files to modify and the nature of changes.
   - Include an **Implementation Notes** section with any task-specific constraints the implementation agent needs (generators to run, deploy coordination, files that must not be hand-edited).

- [ ] **Step 16: Plan Review (Separate Agent)** — If a `plan-reviewer` (or equivalent) agent/subagent exists in this environment, launch it to review the task document with fresh eyes. If none exists, do a structured self-review using the same checklist, or ask the user whether to skip.
   - The reviewing agent has no context of the planning conversation — it evaluates the spec purely on its merits.
   - It returns a **PASS** or **FAIL** verdict along with detailed findings.
   - Prompt template (adapt paths and look-fors to this repo):
     ```text
     Agent(
       subagent_type: "plan-reviewer",
       description: "Review <feature name> spec",
       prompt: """
       Review the task specification at <absolute path to task spec — interpolate
       the resolved <repo_root> before invoking, e.g.
       /resolved/repo/.worktrees/<slug>/docs/plans/<slug>.md> for critical
       problems.

       Also read <repo_root>/CLAUDE.md and/or AGENTS.md (whichever exist) for
       architecture, package ownership, and guardrails. Read any code-style or
       architecture specs those files point to when the task touches those areas.

       **Look for:**
       - State transitions with missing/impossible branches
       - Race conditions, retries, partial failure
       - Missing entity references / lifecycle holes
       - Integration conflicts with systems described in orientation docs
       - Public contract or generated-type drift
       - Money / quota / billing hazards when those systems exist
       - Observability gaps relative to this repo's conventions
       - Trace through concrete multi-actor scenarios step by step
       - Ambiguous or undefined behavior
       - Missing edge cases
       - **Design & simplification**: sketch the strongest simpler alternative
         design and adopt-or-refute it. Flag invariants that N call sites must
         each remember to maintain (derive, don't synchronize) — a design that
         depends on such an unenforced cross-call-site invariant is a Critical
         Issue that gates FAIL, not a preference. Also flag fixes that close
         bug instances but leave the bug class open, accepted trade-offs a
         different design would dissolve, and hand-rolled versions of solved
         problems.
       - **Test cross-reference**: after your technical review, check the spec's
         "How to Test" section. For each Critical Issue or Warning you found,
         verify that at least one proposed test would catch it. Flag any gaps.

       **Do NOT review:** product decisions, scope, or priorities — only
       technical correctness and technical design.
       """
     )
     ```
   - **Handling the result:**
     1. Address all issues found (critical issues, warnings, design findings, and ambiguities) regardless of verdict. For each issue, either fix it or decide not to — but you must have a concrete reason grounded in context the reviewer lacked. "It's fine" is not a reason. For a design finding specifically, "the proposed design also works" is not a reason to keep the spec's design — prefer the alternative unless it costs something concrete the spec must then name.
     2. If the verdict is **FAIL**: update the spec, commit, and re-invoke the reviewer. On re-invocation, include context about what was fixed and what was intentionally kept (with reasoning), so the reviewer can focus on whether fixes are adequate rather than re-flagging resolved items. Repeat until the reviewer returns **PASS** or you hit **10 review cycles** — at that point, stop and escalate to the user.
     3. If the verdict is **PASS**, present the findings and fixes to the user and proceed.
   - This step catches bugs that are much cheaper to fix in a spec than in code.

### Planning Guardrails

Derive hard constraints from the repo's orientation docs. Always apply these meta-rules:

- **Design for the general case this product actually faces.** Don't hand-wave concurrency, retries, or multi-tenant collision as "rare" if the product routinely has those conditions. Conversely, don't invent distributed-systems complexity the repo's docs explicitly say doesn't apply yet.
- **Never break money, quotas, or public contracts silently.** If the product charges, meters, or exposes a stable API/CLI/schema, flag every semantic or contract change in the spec with a migration/rollout path.
- **Never drop the repo's observability hooks** (trace IDs, structured logs, error reporting) on new entry points if those conventions exist.
- **Present trade-offs without premature judgment.** When comparing approaches, present costs and edge cases factually. Don't minimize costs or dismiss alternatives without the user's input on what matters.

## Implementation Handoff

1. **Task Document Created**: Complete specification at `.worktrees/<slug>/docs/plans/<slug>.md`.
2. **ASK USER FOR NEXT STEPS**: NEVER automatically begin implementation.
3. **Pick the implementation mode.** The native worktree at `.worktrees/<slug>/` is usually fine for edits + unit tests. Shared local resources (databases, ports, containers) may still be shared with the main checkout — pick the right mode based on what the task needs at runtime and what *this* repo's tooling supports:

   **Mode 1 — Stay in the worktree** (lightweight tasks)
   - Use when: pure refactor, docs change, type fix, logic change validated by unit tests only.
   - In `.worktrees/<slug>/`, run the repo's lint / typecheck / unit-test commands for the touched packages.
   - If `.env` files are gitignored, they won't exist in a new worktree — copy from the main checkout (or follow the repo's documented bootstrap) before booting apps.
   - **Do NOT** run destructive migrations against a DB shared with main without the user's go-ahead.
   - Main checkout is untouched.

   **Mode 2 — Switch main to the feature branch for verification** (most runtime-touching tasks)
   - Use when: the change needs running services, a browser, or shared local infra, and you're only juggling one task at a time.
   - Stop anything running in main that would conflict.
   - In the main checkout root (`<repo_root>` — not inside `.worktrees/`), run `git checkout feature/<slug>`.
   - Run services, migrations, browser checks from main.
   - When done, optionally switch main back; the native worktree at `.worktrees/<slug>/` still tracks the same branch.
   - **Cost**: serial — only one task can be in verification mode at a time.

   **Mode 3 — Isolated checkout** (heavy / parallel tasks)
   - Use when: migrations that shouldn't touch main's DB, multi-day work alongside other tasks, or anything that needs a separate environment.
   - Prefer a repo-provided worktree/clone script if one exists; otherwise `git worktree add` / a separate clone as the user prefers.
   - Continue implementation where that checkout lives — the same spec is on `docs/plans/<slug>.md` via the shared feature branch.

4. **Implementation conventions** (apply in any mode):
   - **Comment discipline.** Default to writing no code comment. Add one only when a competent reader making a future change would otherwise make a wrong decision — one short line, no multi-paragraph API docs or block comments. Never cite the spec, decision letters, pitfall numbers, plan-reviewer findings, or rationale dates in code; the spec encodes *why*, and those references rot when it moves to `docs/plans/archive/`. When the spec writes "Rationale: …", that rationale lives in the spec — do not transcribe it.
   - Follow the repo's code style specs for the languages involved.
   - Update the task `.md` file as progress is made.
   - Use the repo's preferred commit / review / debug agents or skills when they exist; otherwise use normal git + review practices.
   - Run the relevant package's tests before declaring done. Don't assume pre-commit runs tests unless the repo says so.

5. **Open the PR and archive the spec inside it.** If an `open-pr` (or equivalent) skill exists, drive closing with it. Otherwise:
   - Confirm whatever release/version gates the repo documents (if any).
   - File any "Follow-ups" / "Out of scope" items as dated `docs/plans/backlog/YYYY-MM-DD-<slug>.md` entries when that backlog tree exists (or create it if the user wants the convention).
   - `git mv docs/plans/<slug>.md docs/plans/archive/YYYY-MM-DD-<slug>.md` (today's date) and commit `docs(plan): archive <slug> on completion`. Create `docs/plans/archive/` if needed. The archived spec must appear in **this PR's diff** — never leave it in active `docs/plans/` while the PR is open, and never defer the archive to after merge.
   - Open the PR (draft first if the team prefers), clear checks, then mark ready.

## Task Document Format

Each task should be a standalone document in the worktree's `docs/plans/` containing:

- **Branch**: `feature/<slug>` — the branch where this task is being developed. Worktree at `.worktrees/<slug>/`.
- **Areas Affected**: Packages, services, or modules touched (use concrete directory names from the repo).
- **Objective**: Clear, single-sentence goal.
- **Problem Statement**: What is missing, broken, or needs improvement.
- **Success Criteria**: How we know it's complete.
- **Implementation Notes**: A standard block telling the implementing agent that this spec is the source of *why* and the code should not restate it. A different agent may pick up implementation outside the plan-task flow — drop this block into every spec so that downstream implementer still sees the discipline. Suggested wording:
   > - Default to writing no code comments. Add one only when a future reader making a change would otherwise make a wrong decision — one short line max, no multi-paragraph API docs.
   > - Never cite this spec in code: no decision letters, pitfall numbers, plan-reviewer references, or rationale dates. Those references rot when this spec is archived.
   > - When this spec writes "Rationale: …", that rationale lives here — do not transcribe it into a code comment.
   > - Before opening the PR, follow any version/release gates documented in this repo.
   > - Before archiving, file each item in your "Follow-ups" / "Out of scope" sections as a dated `docs/plans/backlog/YYYY-MM-DD-<slug>.md` entry when that convention is in use.
   > - Archive this spec **as part of the PR**, not after merge: before opening the PR (or as the final commit before you mark it ready), `git mv` this file to `docs/plans/archive/YYYY-MM-DD-<slug>.md` (today's date) and commit as `docs(plan): archive <slug> on completion`. The archive must ship **inside the same PR** — never leave the spec in active `docs/plans/` while the PR is open.
   > - When implementation is complete and verified, open/shepherd the PR via the repo's preferred skill or process — don't open it ad hoc if a closing skill exists.
- **Technical Approach**: Specific changes per affected area.
- **Code Patterns to Follow**: Relevant patterns observed in the codebase that should be used (link to specific files when useful).
- **Edge Cases**: Known edge cases and how they should be handled.
- **Technical Decisions**: Key decisions made during planning and their rationale.
- **Implementation Considerations**: Performance, reliability, observability, billing/quotas (if any), and migration notes.
- **Files to Modify**: Explicit list of files and the nature of changes.
- **How to Test**: Acceptance criteria as plain language, plus instructions for automated and manual testing (see below).

### How to Test Section

Every task document should include a "How to Test" section unless tests are not warranted (see Step 14). Testing has up to four tiers:

1. **Acceptance Criteria** — Plain-language truths the feature must satisfy. Always present.
2. **Automated Tests** — Tests that assert the product decisions made by this task (only if tests are warranted; use frameworks already in the touched packages).
3. **Code Quality Review** — Run a code-quality reviewer agent if one exists; otherwise a careful self-review or human review.
4. **Manual / Visual Testing** — For UI or operator-facing CLI flows, exercise the feature as the orientation docs require.

Template:

```markdown
## How to Test

### Acceptance Criteria

1. [Plain-language truth about expected behavior]
2. [Another truth]
3. Type checks / static analysis pass: [repo command]
4. Linters pass: [repo command]
5. Hooks / CI checks that should pass locally: [repo command]

### Automated Tests

If tests are warranted, list each one grouped by file. Each test asserts a product decision from this task. Use the frameworks and paths already present in the touched packages — discover them in Phase 2; do not invent a new harness unless this task includes that setup.

List each test by name, what it verifies, and which category it falls into (core / boundary / invariant):

- [Test name] — [what it verifies] (core / boundary / invariant)
- [Test name] — [what it verifies] (core / boundary / invariant)

### Code Quality Review

\`\`\`
Agent(
  subagent_type: "code-quality-reviewer",
  description: "Review <feature name> code",
  prompt: """
  Review the code changes for <feature name>.

  **Working directory:** <worktree path — interpolate <repo_root> before invoking, e.g. /resolved/repo/.worktrees/<slug>>
  """
)
\`\`\`

(Omit or replace this block if no such agent exists in this environment.)

### Manual Testing (UI / operator flows only)

Exercise the golden path and the edge cases listed above. Monitor for regressions in adjacent features.

- What to run: [dev server, CLI, etc.]
- Golden path steps:
  1. [Action] → [Expected result]
  2. ...
- Edge cases to exercise:
  - [Edge case 1] → [Expected handling]
  - [Edge case 2] → [Expected handling]

Omit this section for pure library / schema / infra changes with no operator-visible surface.
```
