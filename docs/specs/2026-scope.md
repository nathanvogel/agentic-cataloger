

Goal: 
- LLM observability
    - Human feedback collection
    - LLM fine-tuning (later)
- Multi-step workflows
- Revised workflow for agentic capabilities
- Ability to ingest: 
  - Large batches of products for bulk import / bulk update
  - Single element for ingest / update
  - Specific subsets of the dataset (by imported category, by keyword, by embedding similarity, etc.)
- Python backend
- Domain Driven Design
- Revised data model
- Cache efficiency - don't repeat requests (middleware that caches every requests?) and avoid dev cost spikes

Current workflow: 
1. Data import
    1. Parse CSV, lightweight trait detection by name parsing and unit parsing. 
2. Category discovery — group products by consumer substitutability
    1. Select set of products by categories 
    2. LLM generates array of _new_ categories based on prompt rules and existing categories
    3. Insert DB categories
    4. Log agent execution
3. Schema generation — define per-category attribute schemas
4. Attribute extraction — fill structured traits on each produc

Current issues: 
- Token efficiency: 1 large LLM call vs many small LLM calls? (also ties into caching, as large calls have more variance) 
- Token efficiency: Entire category taxonomy dumped into model context
- Accurary and error rate? Large prompt does 1 LLM call to handle (1) check against existing categories (2) category creation and (3) product assignment. Harder to evaluate (designing an eval, measuring token usage per item, ...) and compare performance (e.g. across models).
- How to handle updates of a single modified source record?
- Traits and units extraction is split across the codebase (partially done deterministically at import time, useful for debug , but potentially not saving any tokens as verified by LLM anyway)
- Observability: custom built, not easily reviewable at scale, not fed back into the agent. 
- No eval set
- Potentially missing self-correcting behavior? (e.g. deleting and merging categories) 
- TypeScript is quite verbose for this workload compared to Python.
- data-importer and backend are split - unifying could increase reuse and correctness.
- Unit extraction fails often.
- No possibilty for the LLM to flag/defer a decision for human review
- Unclear policy regarding which traits go in which category
- "category" ambiguous term. Should be clarified that import category are used exclusively to filter imports (useful in development)
- Bug: Importer writes attributes with deterministic flags (bio, fairtrade, …) and on upsert replaces the whole column, so re-imports will wipe LLM extracted attributes
- Core specs are stored in .kiro instead of standardized cross-agent folder.  

New workflow: 
- Single Python backend for agent flow, REST API and data import
- devcontainers setup 
- 

Open questions: 
- Can products live in multiple places in the hierarchy? (many-to-many or many-to-one)
- Can categories live in multiple places in the hierarchy? (graph or tree)

References: 
- https://fermisense.com/when-machines-take-the-wheel/ 

