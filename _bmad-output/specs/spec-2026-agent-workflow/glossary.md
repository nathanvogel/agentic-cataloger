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
| **evidence_span** | Verbatim substring of a source observation that supports a non-null trait or quantity; source field, the substring, and a SHA-256 hash of that field's text make it checkable. |
| **preferred_comparable_unit** | Unit the category declares as default for basket math on that leaf (required on compare leaves). |
| **Normalized comparable price** | Shelf price divided by the selected quantity expressed in the leaf's preferred comparable unit. **Derived on read** in MVP; always reported with its currency and comparable unit. |
| **DLQ** | Dead-letter / review queue for `unknown` / `defer` outcomes (H2). Non-blocking. |
| **Morph ID** | Stable option ID from the morphological matrix (e.g. C2, I9, D6). Used in constraints and bakeoff design. |
