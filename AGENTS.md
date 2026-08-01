### General rules

- This is a prototype, don't overdo it. YAGNI. 

### Communication rules

- Do not use overly corporate tech speak. Prefer simpler (but precise) startup builder vocabulary and tone (chats, BMAD documents, etc.)
- When referring to stories, requirements, etc. by IDs (e.g. AC-03, TECH-002, etc.), don't assume the reader is familiar with them, reiterate their title / summary if the surrounding context doesn't already make them clear.

### Code rules

- When writing Python, always read and follow the [code_style_python.md](docs/specs/code_style_python.md).
- When writing Typescript, always read and follow the [code_style_typescript.md](docs/specs/code_style_typescript.md).
- CI/CD stays thin: GitHub Actions should mostly invoke portable shell scripts
