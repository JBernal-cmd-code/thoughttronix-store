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

## 2026-09-24 — Coupon form: products as category-grouped checkboxes; accounts import cleanup

### Prompts
1. `/grill-me` I worked with you to add a new coupon feature. Everything
   looks to be working, but when I log in as admin or employee, and then go
   to back office and then coupons, when I edit or go to add a new coupon,
   everything looks correct except for the "Products" section. All
   products look jumbled together and are not organized. I want these
   organized and not jumbled together. When on applies to, I would like
   all products listed but neatly. When on applies to and I select
   product, I would like to be able to see all products neatly, but have
   the optioon to choose a product that the coupon applies to.
2. (Grill-me answer — picker style) Checkboxes by category (Recommended)
3. (Grill-me answer — "Whole order" behavior) Visible, dimmed (Recommended)
4. (Grill-me answer — unavailable products) Show, with a badge
   (Recommended)
5. (Grill-me answer — scope) Coupons only (Recommended)
6. yes, go ahead and build it
7. yes, clean up the duplicate imports too
8. Please write our entire  session log from today  with the standard
   prompt in the PROMPTS.md.

### Summary
- **Outcome:** The agent read the code first and found the cause:
  `products` was a `<select multiple>` that `StyledModelForm` styled with
  DaisyUI's single-dropdown `select` class, which crammed every product
  into one box. `CouponForm` now shows `products` as a
  `CheckboxSelectMultiple`. Its queryset is `select_related("category")`,
  sorted by category name and then product name, and a new
  `product_checkboxes_by_category()` method groups the checkboxes. A new
  partial, `templates/coupons/partials/_product_picker.html`, lays out a
  heading per category, one column on phones and two on wider screens, an
  "Unavailable" badge, and a "No products yet" empty state. While "Applies
  to" is Whole order, the list fades and a note appears. That uses
  Tailwind `group-has-[…]` CSS only, with no JavaScript. Save and validate
  rules are unchanged. There are five new tests in
  `coupons/test_backoffice.py`, and the suite went from 238 to 243
  passing. As a follow-up, merge leftovers in `accounts/` were removed: the
  duplicate imports in `models.py` plus stray blank or whitespace-only
  lines in `models.py` and `views.py`. `ruff check .` and
  `ruff format --check .` now pass project-wide. The work is not
  committed yet. The agent asked whether to make one commit or two, and
  that is still unanswered.
- **Deviations:** None. All four grill-me recommendations were taken as
  offered. The agent chose some layout details itself without asking:
  A–Z ordering, responsive columns, and leaving the dimmed checkboxes
  clickable. Prompt 7 accepted the agent's offer to fix the lint errors it
  found. While doing that, the agent also fixed two whitespace-only format
  problems in `accounts/` that the prompt didn't mention, and it reported
  them.
- **Sideways:** `ruff check .` failed on duplicate imports in
  `accounts/models.py`, which were already there before this session. The
  agent reported them rather than fixing them unasked, and they were
  cleaned up in prompt 7. `tailwind build` said "up to date", so the agent
  ran `--force` and checked the compiled CSS for the `group-has` dimming
  rules. The first draft of the "checked when editing" test matched on
  exact HTML attribute order, which breaks easily. The agent rewrote it to
  check the bound checkbox's `tag()` before running it. The agent has not
  looked at the page in a browser. The work was verified only by tests
  and by inspecting the compiled CSS.

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

Note from me. I didn't realize I had to add the whole log list, and by the time I was working on the review, I cleared since Claude was in the dumb zone after my initial grill me section.