# Plan: Product Reviews

> Source PRD: `prd/reviews.md`. The PRD owns the requirements;
> this plan owns the sequence. Where the two differ, the PRD's wording wins.

## Architectural decisions

Durable decisions that apply across all phases:

- **Owning app**: a new `reviews` app with its own URL namespace
  (`reviews:`) and its own template directory. `reviews` imports from
  `products` and `orders` (and may import from `accounts`). Nothing imports
  from `reviews` except the `seed` command, which already builds the whole
  demo world. The product detail view reads reviews through the reverse
  relation (`product.reviews`), never the `Review` model, the same way it
  reads the wishlist.
- **Models**:
  - `Review`: FK to the user (cascade), FK to the product (cascade), a
    `rating` (small positive integer, whole stars 1–5), a required `comment`
    (at most 2,000 characters; only spaces counts as empty), an
    `edited_by_staff` boolean (default false), and `created_at`.
  - `created_at` is a default, not `auto_now_add`, so `seed` can backdate it.
    There is no `updated_at`.
  - A unique constraint on (user, product) keeps it to one review per
    customer per product at the database level.
  - Ordered newest first.
  - Model methods hold the logic: eligibility (the user's own account has an
    order containing the product whose status isn't Cancelled, checked only
    at creation), `can_be_changed_by(user)` (author or any staff), an edit
    method that takes the editor and sets `edited_by_staff` when a staff
    member edits someone else's review (never cleared), and `author_name`
    ("Jordan P.", falling back to "Verified buyer"). Nothing here is a
    multi-model workflow, so there's no service module.
- **URLs** (all in the `reviews:` namespace):
  - `reviews:create`: `reviews/create/<product pk>/`, POST only. A missing
    product is a 404.
  - `reviews:edit`: `reviews/<review pk>/edit/`, GET. Returns the edit-form
    partial for one card.
  - `reviews:cancel`: `reviews/<review pk>/cancel/`, GET. Returns the card
    partial unchanged.
  - `reviews:update`: `reviews/<review pk>/update/`, POST only. Saves an edit.
  - `reviews:delete`: `reviews/<review pk>/delete/`, POST only.
  - No review URL takes a user id.
- **Access**:
  - Every review endpoint requires sign-in, enforced on the server, GETs
    included. A signed-out request goes to login. A signed-out HTMX request
    gets a response with `HX-Redirect` to login, so the whole browser
    navigates instead of the login page being swapped into the section.
  - Create refuses an ineligible user with 403.
  - Every endpoint that takes a review pk checks `can_be_changed_by` and
    answers anyone else with a 404.
  - Staff follow the same eligibility rule as customers.
- **HTMX**:
  - One reviews-section partial with a stable wrapper id, placed below the
    product details. It holds the summary, the pinned slot, and everyone
    else's reviews.
  - Separate partials for one review card and one edit form.
  - Create, save, and delete swap the whole section, so the summary stays
    correct. Edit and cancel swap only the card (`outerHTML`).
  - Partials live in the app's `partials/` directory, are underscore-
    prefixed, and never extend the base template.
- **Thin views**: views call the model methods and render.
- **Docs travel with the code**: there's no docs phase. Each phase updates the
  `docs/` files covering what it builds before the phase is called done.

---

## Phase 1: Writing and reading reviews on the product page

**User stories**: 1–6, 8–23, 30, 32–35

### What to build

This phase creates the `reviews` app, the `Review` model and its migration,
the rating and comment rules, the unique constraint, eligibility, and
`author_name`. The product detail view adds the section's context: the
average rating and count, the requester's own review (if any), whether the
requester may review, and everyone else's reviews.

The reviews section on the product detail page shows, in order:

1. **Summary:** average stars and review count, or a designed empty state
   when the product has no reviews.
2. **Pinned slot**, in one of four states:
   - **Signed out:** "Sign in to write a review," a plain link to login with
     `next` set to the product page. No HTMX.
   - **Signed in, not eligible:** a short note that only customers who've
     purchased the product can review it.
   - **Eligible, no review yet:** the create form. The rating is five DaisyUI
     `rating` radio inputs, and the comment is a textarea.
   - **Already reviewed:** the customer's own review card. Edit and Delete
     arrive in Phase 2.
3. **Everyone else's reviews**, newest first, excluding the requester's own.
   Each card shows the stars, comment, `author_name`, date, and an "Edited
   by staff" badge when the flag is set. (Phase 1 can't set the flag through
   the UI, but the card renders it.)

`reviews:create` HTMX-POSTs and handles four cases:

- **Not eligible:** 403.
- **Invalid:** the form re-renders in place with errors, keeping what the
  customer typed.
- **Already reviewed:** the section re-renders with the existing review
  pinned and an alert saying the customer has already reviewed the product
  and can edit it below. This covers both a stale tab and a simultaneous
  duplicate, where the view catches the `IntegrityError` from the unique
  constraint and answers the same way.
- **Valid:** the review is saved, and the whole section re-renders with the
  summary updated.

The sign-in requirement and the HTMX `HX-Redirect` behavior are built here,
in a form the review-pk endpoints in Phase 2 can reuse.

### Acceptance criteria

- [ ] In the browser, an eligible customer can write a review on a product
      page and see it appear pinned in place, with the summary updated and
      no page reload.
- [ ] Eligibility: Placed, Shipped, and Delivered orders qualify, and
      Cancelled doesn't. Another account's order for the same product
      doesn't qualify. An unavailable product qualifies.
- [ ] Model:
  - [ ] Ratings of 1 and 5 are accepted, and 0 and 6 are refused.
  - [ ] The comment is required, a comment of only spaces is refused, and
        the 2,000-character limit holds.
  - [ ] The unique constraint refuses a duplicate.
  - [ ] `author_name` gives "First L." and falls back to "Verified buyer."
- [ ] Access:
  - [ ] A signed-out POST to create goes to login.
  - [ ] A signed-out HTMX POST to create gets `HX-Redirect` to login.
  - [ ] An ineligible create returns 403 and creates nothing.
- [ ] Responses:
  - [ ] A valid create returns the section partial (not the full page) with
        an updated summary.
  - [ ] An invalid create re-renders the form with errors and the typed
        values.
  - [ ] A second create re-renders with the existing review and the alert,
        and creates nothing.
- [ ] Page:
  - [ ] Each of the four pinned-slot states renders for the right requester.
  - [ ] The signed-out link carries `next`, and signing in returns to the
        product.
  - [ ] Reviews list newest first, and the requester's own review is
        excluded from the list.
  - [ ] The empty state shows on an unreviewed product.
  - [ ] The "Edited by staff" badge shows when the flag is set.
- [ ] Deleting a product or a user deletes their reviews.
- [ ] Tests live in `reviews` and use the plain `conftest.py` fixtures, never
      seed data. Every test user has a distinct email.
- [ ] The style guard covers the new templates and passes.
- [ ] Docs:
  - [ ] `docs/ARCHITECTURE.md` gets the new app, its dependency rule, and
        its per-app rules: eligibility, check-once, and the display name.
  - [ ] `docs/VIEWS.md` gets the create route, the access rules (sign-in on
        every endpoint, `HX-Redirect`, 403 for an ineligible create), and
        the section-swap rule.
  - [ ] `docs/FRONTEND.md` gets the reviews section, its pinned-slot states,
        and the partials.
  - [ ] The root `CLAUDE.md` project layout gains `reviews/`.

---

## Phase 2: Editing and deleting your own review

**User stories**: 24–29, 31, 33

### What to build

This phase adds `can_be_changed_by` and the edit method. Edit and Delete
buttons render on a review card only for users `can_be_changed_by` allows.
For now that means the author on their own pinned review.

- **Edit:** HTMX-GETs `reviews:edit` and swaps the card for the edit-form
  partial (`outerHTML`).
- **Cancel:** HTMX-GETs `reviews:cancel` and swaps the original card back,
  unchanged.
- **Save:** HTMX-POSTs `reviews:update`. Invalid input re-renders the edit
  form in place with errors. Valid input saves through the edit method and
  re-renders the whole section.
- **Delete:** asks for confirmation with `hx-confirm`, then HTMX-POSTs
  `reviews:delete`. The review is deleted, and the section re-renders with
  the create form back in the pinned slot.

All four endpoints require sign-in, including the GETs, and get the
`HX-Redirect` behavior from Phase 1. Each checks `can_be_changed_by` on the
server and gives anyone else a 404.

### Acceptance criteria

- [ ] In the browser, the author can edit their review in place, cancel an
      edit, save one, and delete their review after confirming.
- [ ] Edit and cancel return the form or card partial. Save and delete
      return the section partial with an updated summary.
- [ ] An invalid save re-renders the edit form with errors and the typed
      values.
- [ ] After a delete, the create form shows again, and the customer can
      write a new review.
- [ ] `can_be_changed_by` is true for the author and false for other
      customers.
- [ ] Another customer's edit, cancel, update, and delete requests return 404
      and change nothing.
- [ ] Signed-out requests to all four endpoints, the GETs included, go to
      login. HTMX requests get `HX-Redirect`.
- [ ] After the author's order is cancelled, the review stays, and the author
      can still edit and delete it.
- [ ] Docs: `docs/VIEWS.md` gets the four routes, the 404 rule, and the card
      versus section swap rules. `docs/FRONTEND.md` gets the edit-form
      partial and the `hx-confirm` delete.

---

## Phase 3: Staff moderation and the admin overview

**User stories**: 7, 36–42

### What to build

`can_be_changed_by` grants staff access to every review, so Edit and Delete
show on every card for staff. The server allows the staff member's requests
on every review endpoint. A staff edit to someone else's review sets
`edited_by_staff`, and the card shows the badge. The author's later edits
never clear it. A staff delete is an ordinary delete. Staff writing their
own reviews follow the same eligibility rule as everyone else.

A `ReviewAdmin` lists reviews with their author, product, rating, date, and
staff-edited flag. It filters by rating and searches by product name and
username. Add and change are blocked for everyone, superusers included, the
same way `SecurityEventAdmin` is locked down. Delete is allowed.

### Acceptance criteria

- [ ] In the browser, a staff member sees Edit and Delete on every review and
      can moderate in place. An edited review shows "Edited by staff."
- [ ] `can_be_changed_by` is true for staff on any review.
- [ ] A staff edit of another user's review sets the flag. A staff edit of
      their own review doesn't set it. The author's later edit doesn't clear
      it.
- [ ] Staff can delete any review.
- [ ] A staff member without a qualifying order gets the not-eligible note
      and a 403 on create. With one, they can review.
- [ ] Admin: the changelist renders with the filter and search, add and change
      are refused for a superuser, and delete works.
- [ ] Docs: `docs/ARCHITECTURE.md` gets the staff flag rule and the admin
      lockdown. `docs/VIEWS.md` notes that staff can moderate on the product
      page.

---

## Phase 4: Seeded demo reviews

**User stories**: 43–46

### What to build

`seed` adds a handwritten list of reviews in the store's voice: several
reviews each for a handful of products. Each one is assigned
deterministically to a background customer who has a non-cancelled order for
that product. The demo `customer` gets exactly one review on a product they
bought and keeps other purchases unreviewed, so the create form shows. One
background review has `edited_by_staff` set. Some products get no reviews, so
the empty state shows. `created_at` values are backdated relative to the
run. The wipe needs no extra step, because reviews cascade with their
products and users. The seed summary line reports the review count.

### Acceptance criteria

- [ ] Every seeded review passes the eligibility rule (tested).
- [ ] `customer` has exactly one review and at least one unreviewed eligible
      purchase.
- [ ] Exactly one seeded review is staff-edited, and at least one product has
      no reviews.
- [ ] Seeding twice gives the same reviews (idempotent).
- [ ] The full suite is green, and Ruff is clean.
- [ ] Docs: `docs/ARCHITECTURE.md`'s seed exception names `reviews`. The
      `seed` docstring and summary mention reviews. `PROMPTS.md` gets an
      appended entry.
