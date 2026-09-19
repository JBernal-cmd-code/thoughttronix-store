# PROMPTS.md — AI Usage Log

This file is the record of AI use on this codebase. At the end of every
agent session, direct the agent to write the session log with this prompt:

> Append a session log to PROMPTS.md at the repo root, under today's date,
> newest entry at the top. Record every prompt I gave you this session, in
> order, including any corrections. End the entry with a short summary:
> the outcome, any places where I deviated from a recommended answer or
> asked follow-up questions, and anything that went sideways.

Two rules:

- Entries are added only by that prompt, never unprompted.
- New entries go at the top. Never rewrite or delete an old entry — the
  log is part of your work, and an honest log of a session that went
  sideways is worth more than a tidy one.

Each entry has this shape:

    ## YYYY-MM-DD — <one-line summary>

    ### Prompts
    1. ...

    ### Summary
    - **Outcome:** what was built and what was kept
    - **Deviations:** recommendations overridden, follow-up questions asked
    - **Sideways:** failures, wrong turns, and how they were caught

## 2026-09-19 — Featured products: field, back-office toggle, and storefront badge

### Prompts
1. Please add an "is_featured" field to Product. It will be a boolean and
   defaults to not-featured, which means that existing products stay
   unfeatured.
2. Yes, please expose is_featured in the back-office product form so it
   can be edited from the UI
3. Please add a "Featured" badge for products where is_featured=True. The
   badge needs to appear wherever the store lists a product, especially on
   the catalog listing card and the product detail page. Please ensure
   both places are updated and display the featured badge.
4. Append a session log to PROMPTS.md at the repo root, under today's
   date, newest entry at the top. Record every prompt I gave you this
   session, in order, including any corrections. End the entry with a
   short summary: the outcome, any places where I deviated from a
   recommended answer or asked follow-up questions, and anything that went
   sideways.

### Summary
- **Outcome:** `Product.is_featured` (`BooleanField(default=False)`) with
  migration `products/0003_product_is_featured.py`; the field added to
  `ProductForm.Meta.fields`, where the existing `StyledModelForm` renders
  it as a DaisyUI toggle with no template change; a `badge-secondary`
  "Featured" badge on the catalog card (covering category pages and
  search, which share the template), the product detail page, and the
  back-office product table. Four new tests (feature via the form, badge
  on catalog and detail, badge in the back-office list). Suite went from
  164 to 168 passing; ruff clean throughout.
- **Deviations:** Prompt 2 was a follow-up taking up the agent's offer to
  expose the field in the form (the seed data half of that offer was not
  taken up, so no seeded product is featured). In prompt 3 the agent
  extended "wherever the store lists a product" to the back-office table
  as well as the two named storefront pages, since that table already
  carries a status-badge column.
- **Sideways:** Nothing. Each step was migrated, tested, and linted before
  reporting; no wrong turns.
