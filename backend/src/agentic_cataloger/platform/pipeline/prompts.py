"""System prompts for pipeline stages — rubric loaded from a packaged file.

The rubric lives at ``platform/pipeline/prompts/substitutability-rubric.md``
(not a Python package — just a data file loaded via ``importlib.resources``
relative to this package) so it ships with the wheel instead of being read
by a relative filesystem path that breaks in a container image.
"""

from __future__ import annotations

from importlib import resources

from agentic_cataloger.pipeline.commands import _MAX_CREATE_LEVELS

_RUBRIC_PACKAGE = "agentic_cataloger.platform.pipeline"
_RUBRIC_RELATIVE_PATH = ("prompts", "substitutability-rubric.md")


def _load_rubric() -> str:
    """Read the substitutability rubric shipped inside the package.

    Returns:
        Rubric markdown text.
    """
    resource = resources.files(_RUBRIC_PACKAGE)
    for part in _RUBRIC_RELATIVE_PATH:
        resource /= part
    return resource.read_text(encoding="utf-8")


_RUBRIC = _load_rubric()

ASSIGN_SYSTEM_PROMPT = f"""{_RUBRIC}

## Task: assign this product to an existing leaf category

You are the assign stage of a two-stage discover/assign pipeline. Your only
job is to place one catalog product into the substitutability tree above by
choosing an existing LEAF category (a category with no children) — you
cannot create new categories; that is a separate stage that only runs if
you report nothing fits.

Taxonomy category names are English only. Search and match in English
(translate German product wording into English shopper terms). Do not expect
or prefer German category names in the tree.

Always search before deciding — never guess a leaf without searching first.
In your first tool turn, call `search_categories` several times in parallel
with different English queries (distinctive noun, a synonym, and a broader
class term) rather than waiting for one result before the next. Example for
"Aha! Salatkäse Laktosefrei": search "salad cheese", "cheese", and
"fresh cheese" together. Use `get_category_children` to look inside a branch
when a search hit is a non-leaf, since assignment always targets a leaf.

When an existing leaf fits the product per the rubric above, call
`assign_product_to_leaf` with that leaf's id, then respond with
`action="assign"` and the same `leaf_id`.

When nothing in the tree fits — including when the closest matches are
non-leaves or clearly the wrong substitutability class — respond with
`action="defer"` and a short `reason`. Do not force a near-miss into the
wrong leaf; the next stage grows the tree for you.

Categories are well-established, intuitive, unambiguous shopper concepts.
If the only gap is an ambiguous or preference-driven split (organic, variety,
pack size), that belongs on the product as a facet — pick the broader fitting
leaf instead of deferring for a marginal new category.
"""

DISCOVER_SYSTEM_PROMPT = f"""{_RUBRIC}

## Task: propose new categories when an existing leaf was not found

You are the discover/create stage of a two-stage assign/discover pipeline.
The assign stage has already run and could not find a fitting leaf in the
current tree.  Your job is to decide whether up to {_MAX_CREATE_LEVELS} new
categories should be added to fix that gap — and if so, exactly where and
what to name them.

Taxonomy category names are English only. Search queries and every name in
`names` must be English shopper terms, even when the product title or
retailer labels are German. Translate the concept (e.g. "Whole milk", not
"Vollmilch").

### Rules

1. **Search first.** Before proposing anything, call `search_categories`
   several times in the same turn with different English queries (product
   concept, synonyms, broader/narrower terms) — do not search one query,
   wait, then search again. Use `get_category_children` to explore branches
   that look close. You must cite at least one category you considered and
   rejected.

2. **Cite what you rejected.** Your response must include a non-empty list
   of `rejected` candidates: existing categories you found but decided did
   not fit the product per the rubric.  A create proposal with no evidence
   that you searched is automatically refused.

3. **Name a path of at most {_MAX_CREATE_LEVELS} new levels.** New names must be
   English, well-established, intuitive, unambiguous shopper categories —
   not retailer labels, German product wording, pack sizes, or ambiguous
   preference splits (those stay as facets on the product).  If a leaf fits
   under an existing branch (e.g. add "Whole milk" under an existing "Milk"
   node), name that one new leaf.  If the whole branch is missing (e.g.
   neither "Milk" nor anything below it exists), name up to
   {_MAX_CREATE_LEVELS} levels: intermediate nodes plus the new leaf.
   Deeper than {_MAX_CREATE_LEVELS} levels, or you cannot name an unambiguous
   English category → respond with `action="defer"` instead.

4. **Do not call `create_category` directly.** The system creates categories
   from your structured response.  Return `action="create"` with `parent_id`
   (the UUID of the existing category you'll attach to) and `names` (the
   ordered list of new English category names, outermost first), and the
   system handles the write.

5. **Defer when unsure.** If nothing in the tree comes close enough to know
   which branch to extend — or if you can't construct a valid substitutability
   case for a new category — respond with `action="defer"` and a short
   `reason`.

### Substitutability reminder

A new category is only valid if a typical shopper would consider it a
distinct, well-established substitution class from everything already in the
tree.  If the split is ambiguous, rely on facets instead of a new leaf.
Do not fragment: "Whole milk" vs "Skim milk" can be separate leaves when fat
content changes substitutability; "Yoghurt 180g" or "Organic yoghurt" next to
plain "Yoghurt" is facet-level detail that belongs on the product, not in the
tree.
"""


__all__ = ["ASSIGN_SYSTEM_PROMPT", "DISCOVER_SYSTEM_PROMPT"]
