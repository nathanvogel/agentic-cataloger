### General rules

- This is a prototype, don't overdo it. YAGNI. 

### Communication rules

- **Do not use overly corporate tech speak.** Prefer simpler (but precise) startup builder vocabulary and tone (in chats, documents, etc.)
- **Name concrete things.** Prefer file paths, CLI commands, table names, and field names over abstract labels ("envelope", "primitive", "load-bearing"). If a technical term is the right name in code, gloss it in plain English on first use.
- **Keep precision; drop ceremony.** "Fail closed on missing unit" is fine; "leverage synergistic orchestration primitives" is not.
- When referring to stories, requirements, etc. by IDs (e.g. AC-03, TECH-002, etc.), don't assume the reader is familiar with them, reiterate their title / summary if the surrounding context doesn't already make them clear.

### Code rules

- When writing Python, always read and follow the [code_style_python.md](docs/specs/code_style_python.md).
- When writing Typescript, always read and follow the [code_style_typescript.md](docs/specs/code_style_typescript.md).
- CI/CD stays thin: GitHub Actions should mostly invoke portable shell scripts
- Architectural decisions that outlive a PR go in [`docs/decision_records/`](docs/decision_records/) (template: [`docs/templates/decision_record.md`](docs/templates/decision_record.md)).
- Implementation plans go in `docs/plans/YYYYMMDD-<main-component>-<slug>.md` (`<main-component>` = primary package/module/service from the repo).
- When committing, use conventional commit messages.
- **Comments and docstrings describe current code, not history.** No roadmap/story IDs, phase labels, or "design discussion" asides in code. Skip "X, and not Z" when Z was never a real option. 
- **Code comments (if any) explain the why.** Do not reformulate the code in prose.
