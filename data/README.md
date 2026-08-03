# Source data (`data/`)

Swiss grocery product CSVs from the [Yelinz HuggingFace datasets](https://huggingface.co/Yelinz). Each retailer has its own folder:

- `coop-ch-products/`
- `denner-ch-products/`
- `lidl-ch-products/`
- `migros-ch-products/`

Files are stored in Git LFS (see repo-root `.gitattributes`).

## File layout

Each CSV is one **point-in-time scrape**, not a delta:

```text
{retailer}-ch-products/YYYY/MM/DD-HH:MM.csv
```

The same product appears in many files across dates with updated prices.

### Latest file per retailer only

Pulled from HuggingFace on 2026-08-02:

| Retailer | File | Products |
| --- | --- | --- |
| Coop | `coop-ch-products/2026/02/25-21:46.csv` | 8,308 |
| Denner | `denner-ch-products/2025/12/30-14:48.csv` | 1,092 |
| Lidl | `lidl-ch-products/2025/12/31-11:35.csv` | 2,905 |
| Migros | `migros-ch-products/2025/12/30-15:22.csv` | 20,790 |

Latest HF dumps add new fields: `name_de`, `unified_category`, `unified_subcategory`, `original_price`, `original_unit`, `original_unit_price`.

### Dataset snapshot regression

Coop scrapes regressed in late 2025 (Sep files dropped to ~5k food-only rows; Aug had ~23k across wine, household, cosmetics, etc.). Feb 2026 is better (~8.3k) but still narrow. Lidl, Migros, and Denner latest files look like stable full-catalog snapshots (~3–7% product churn between months).

## CSV schema

Core columns (all retailers):

- `name`, `url`, `price`, `price_text`, `unit`, `unit_price`
- `has_discount`, `discount_info`, `image_url`, `category`

Newer dumps also include:

- `name_de` — German display name where different from `name`
- `unified_category`, `unified_subcategory` — publisher-normalized labels (see below)
- `original_price`, `original_unit`, `original_unit_price` — pre-discount / list values

Coop is the only retailer whose latest file includes a `store` column in older 2025 dumps; newer files follow the shared schema above.

## `unified_category` and `unified_subcategory`

These are **import/source labels** from the dataset publisher — useful for filtering ingest subsets, **not** the substitutability taxonomy the app builds in M1.

### `unified_category` — shared vocabulary, uneven product coverage

All four retailers use the same 12 English top-level labels (`bakery`, `beverages`, `dairy`, `meat`, `pantry`, `snacks`, `vegetables`, `fruits`, `fish`, `household`, `personal_care`, `other`). No retailer-specific category names.

Eight categories appear in all four latest files: `bakery`, `beverages`, `dairy`, `meat`, `other`, `pantry`, `snacks`, `vegetables`.

Gaps reflect scrape scope, not different taxonomies:

| Gap | Cause |
| --- | --- |
| Coop has no `household` / `personal_care` | Latest scrape is ~99% `/lebensmittel/` (food) |
| Migros has no `fruits` / `fish` at this level | Those products are classified under other labels (e.g. `other`, `vegetables`) |

Category fill rate in latest files:

| Retailer | Rows with `unified_category` set |
| --- | --- |
| Coop | ~100% |
| Lidl | ~99% |
| Migros | ~94% |
| Denner | ~66% |

### `unified_subcategory` — same namespace, sparse and inconsistent

59 distinct `snake_case` values across all files (`bread`, `cheese`, `wine`, `frozen_meals`, …). Only **two** appear in all four retailers: `frozen_meals` and `misc`.

Subcategory fill rate in latest files:

| Retailer | Rows with subcategory set |
| --- | --- |
| Lidl | ~87% |
| Denner | ~42% |
| Migros | ~20% |
| Coop | ~6.5% |


## Ingest into the Python catalog

The active importer is `pricecomp ingest` (see [`backend/README.md`](../backend/README.md)). It registers an immutable snapshot per latest file and upserts products on `(source_namespace, source_product_id, source_variant_id?)` parsed from the product URL. New HF fields (`name_de`, `unified_*`, `original_*`) are stored as observations; `unified_*` remain import/source labels only.

## Per-retailer notes

### Coop

- README on HuggingFace claims the full online catalogue; latest local scrape does not reflect that.
- Aug 2025 files (~23k rows) include wine (`/weine/`), household, cosmetics, baby, etc.
- Sep 2025 scrapes broke down to ~5k food-only; Feb 2026 recovered to ~8.3k but is still ~99% food.

### Migros

- HuggingFace README: **Zurich region only**, not all of Switzerland.
- Latest file ~20.8k products; stable size across 2025 snapshots.

### Denner / Lidl

- Latest files match expected catalogue size; normal product churn between monthly snapshots.

