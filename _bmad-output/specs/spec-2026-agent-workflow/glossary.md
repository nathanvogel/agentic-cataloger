# Glossary

| Term | Meaning |
| --- | --- |
| **Import / source category** | Retailer or CSV taxonomy label used **only to filter** ingest subsets. Not a comparison primitive. |
| **Substitutability category** | Our taxonomy node for **consumer substitutability** — products a shopper would treat as interchangeable for everyday purchase. The comparison primitive. |
| **Leaf** | Finest substitutability category used for default cross-retailer price compare. Product ↔ leaf is **many-to-one**. |
| **Facet** | Within-leaf preference filter (organic, fat%, brand tier, …). Does not create a new leaf. |
| **Parent** | Coarser tree ancestor used to **widen** compare scope (e.g. fresh vs UHT via parent `cow milk`). |
| **Comparison-ready row** | Product with: substitutability leaf + structured traits + shelf price + normalized comparable price (when convertible). |
| **Source identity** | Stable `(source_namespace, source_product_id, optional source_variant_id)` supplied by a versioned adapter. Product name and URL are mutable observations. |
| **evidence_span** | Verbatim substring of a specific immutable source observation that supports a non-null trait or quantity; field, offsets, text hash, and observation revision make it unambiguous. |
| **preferred_comparable_unit** | Unit the category declares as default for basket math on that leaf (required on compare leaves). |
| **Comparison price projection** | Rebuildable indexed read model containing normalized price plus the exact shelf-price/quantity revisions, currency, comparable unit, and formula version from which it was derived. |
| **DLQ** | Dead-letter / review queue for `unknown` / `defer` outcomes (H2). Non-blocking. |
| **Morph ID** | Stable option ID from the morphological matrix (e.g. C2, I9, D6). Used in constraints and bakeoff design. |
