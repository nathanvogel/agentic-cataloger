"""System prompts for pipeline stages — rubric loaded from a packaged file.

The rubric lives at ``platform/pipeline/prompts/substitutability-rubric.md``
(not a Python package — just a data file loaded via ``importlib.resources``
relative to this package) so it ships with the wheel instead of being read
by a relative filesystem path that breaks in a container image.
"""

from __future__ import annotations

from importlib import resources

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

Always call `search_categories` with the product's name before deciding —
never guess a leaf without searching first. Use `get_category_children` to
look inside a branch when a search hit is a non-leaf, since assignment
always targets a leaf.

When an existing leaf fits the product per the rubric above, call
`assign_product_to_leaf` with that leaf's id, then respond with
`action="assign"` and the same `leaf_id`.

When nothing in the tree fits — including when the closest matches are
non-leaves or clearly the wrong substitutability class — respond with
`action="defer"` and a short `reason`. Do not force a near-miss into the
wrong leaf; the next stage grows the tree for you.
"""


__all__ = ["ASSIGN_SYSTEM_PROMPT"]
