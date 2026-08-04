# Substitutability rubric

Prose definition and few-shot pairs for the M2 discover/assign agent. Membership
means: would a typical Swiss grocery shopper treat these products as
**interchangeable substitutes** when comparing price for the same use?

## Definition

Two products belong in the **same leaf** when a shopper would freely swap one
for the other for the same everyday use, without changing the meal plan or
recipe in a meaningful way. Same leaf implies same preferred comparable unit
once units are validated (later work); for assignment, focus on shopper
substitutability, not on price being numerically close.

Ask: "Would a regular shopper switch from product A to product B for their
everyday needs?" If yes → same leaf. If no → different leaves.

Put products in **different leaves** when form, use, or shopper expectation
differs enough that comparing them as "the same thing" would be misleading
(e.g. fresh vs UHT milk, whole vs skim if the leaf is fat-specific, brand-tier
only when the tree already encodes that facet as separate leaves).

**Facets, not new leaves.** Preference filters within the same product class
stay as facets (organic/Bio, variety, fat%, brand tier) unless the tree
already encodes that split as separate leaves. Do not invent a leaf just to
hold an organic or variety distinction.

**Not** criteria for membership:

- Same retailer `source_category` or import label
- Similar price or pack size alone
- Embedding / name similarity alone
- Brand match alone
- Whether prices can be compared by weight/quantity (that is later unit work,
  not a reason to split or merge leaves)

Parents widen compare scope later (e.g. all cow milk under a parent); leaves
stay at consumer-fine granularity.

## Same leaf (few-shot)

1. **Migros M-Budget Vollmilch 1L** and **Denner Vollmilch 1L** — both plain
   whole cow milk, UHT or fresh as already scoped by the leaf; shopper swaps
   on price.
2. **Coop Qualité & Prix Emmentaler gerieben 200g** and **Migros Emmentaler
   gerieben 200g** — same grated Emmental style cheese for cooking/topping.
3. **Lidl Freeway Cola 1.5L** and **Denner Cola 1.5L** — standard cola soft
   drinks in large PET; interchangeable for a fridge stock-up.
4. **Migros Zitronen Bio** and **Denner Zitronen** — organic vs conventional
   lemons; Bio is a facet, not a separate leaf.
5. **Coop Gala Äpfel** and **Migros Braeburn Äpfel** — apple varieties stay in
   one leaf; variety is a facet (or downstream attribute), not a leaf split.
6. **Lidl Cherry Tomaten** and **Migros Tomaten** — mild form variants most
   recipes can use interchangeably; stay in the same tomato leaf.

## Not the same leaf (few-shot)

1. **Migros Vollmilch 1L** vs **Migros Haferdrink 1L** — dairy milk vs oat
   drink; different use for many shoppers and different comparable units.
2. **Denner Rapsöl 1L** vs **Denner Olivenöl Extra Vergine 0.5L** — different
   oil types and typical culinary roles; do not force into one "cooking oil"
   leaf when the tree already distinguishes them.
3. **Coop Banane lose** vs **Coop Apfel Golden Delicious** — both fresh fruit,
   but shoppers do not treat banana and apple as substitutes for the same
   basket line item.
4. **Migros Zitronen** vs **Lidl Limetten** — lemon and lime are related citrus
   but not everyday substitutes; keep separate leaves.
