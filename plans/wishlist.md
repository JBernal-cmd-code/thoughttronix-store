# Plan: Customer Wishlist

> Source PRD: `prd/wishlist.md`. The PRD owns the requirements;
> this plan owns the sequence. Where the two differ, the PRD's wording wins.

## Architectural decisions

Durable decisions that apply across all phases:

- **Owning app**: a new `wishlists` app with its own URL namespace
  (`wishlists:`) and its own template directory. `wishlists` imports from
  `products` (and may import from `accounts`). Nothing imports from
  `wishlists` except the `seed` command, which already builds the whole demo
  world.
- **Models**:
  - `Wishlist`: a one-to-one link to the user (cascade). It's created lazily
    through `Wishlist.for_user(user)`, the same way the cart works, and
    nothing else creates wishlists.
  - `WishlistItem`: FK to the wishlist and FK to the product (both cascade),
    plus `added_at`. A unique constraint on (wishlist, product) keeps each
    product to one row per wishlist. Items are ordered newest first.
    `added_at` is a default, not `auto_now_add`, so `seed` can backdate it.
  - Model methods hold the logic: add a product (get-or-create, so adding
    twice does nothing), remove a product (removing an unsaved product does
    nothing), and report whether a product is saved. Nothing here spans
    several models, so there's no service module.
- **URLs** (all in the `wishlists:` namespace):
  - `wishlists:detail`: `/wishlist/`, the "My wishlist" page.
  - `wishlists:add` and `wishlists:remove`: POST only, take a product pk.
    They're separate endpoints, not a toggle, so a repeated request or a
    stale tab can't flip the state. A nonexistent product pk returns 404.
  - `wishlists:remove_item`: POST only, takes a wishlist item pk, which is
    always looked up through the requester's wishlist.
  - No wishlist URL takes a user id or a wishlist id.
- **Access**: every wishlist view uses `LoginRequiredMixin`. Signed-out
  visitors go to login. Every signed-in user, staff included, gets in, and
  acts only on their own wishlist. The models aren't registered in Django
  admin, and there's no back-office page or dashboard figure.
- **HTMX**: the endpoints re-render partials (the button partial, or the
  wishlist contents partial) the way the cart does. There's no navbar count
  badge, so no out-of-band swap.
- **Thin views**: views call the model methods and render.
- **Docs travel with the code**: there's no docs phase. Each phase updates the
  `docs/` files covering what it builds before the phase is called done.

---

## Phase 1: The wishlist button on the product page

**User stories**: 1, 2, 3, 4, 5, 6, 7, 19, 20, and 16–18 for the add and
remove routes

### What to build

This phase creates the `wishlists` app and its two models, along with
`Wishlist.for_user` and the add, remove, and is-saved methods. The product
detail view adds one fact to its context: whether the product is on the
requester's wishlist (always false for signed-out visitors).

Next to Add to cart, the detail page includes a wishlist button partial with
three states:

- **Signed out:** a plain "Save to wishlist" link to the login page, with
  `next` set to the current product page. No HTMX.
- **Signed in, not saved:** an outline small "Save to wishlist" button that
  HTMX-POSTs to `wishlists:add` and swaps itself (`outerHTML`).
- **Signed in, saved:** a secondary small "Saved ✓ — Remove" button that
  HTMX-POSTs to `wishlists:remove` and swaps itself.

`wishlists:add` saves any product, available or not, and returns the partial
in its saved state. `wishlists:remove` removes the product if it's saved and
returns the partial in its not-saved state.

### Acceptance criteria

- [ ] The detail page shows the right button state for a signed-out visitor,
      a signed-in user who hasn't saved the product, and one who has.
- [ ] The signed-out link goes to login with `next` set to the product page,
      and signing in returns there.
- [ ] Add and remove respond with the partial alone (not the full page), in
      the new state.
- [ ] Adding the same product twice leaves one item. Removing a product that
      isn't saved succeeds and changes nothing.
- [ ] An unavailable product can be added. A nonexistent product pk returns
      404 from both add and remove.
- [ ] Signed-out POSTs to add and remove go to login.
- [ ] Deleting a product deletes its wishlist items.
- [ ] Tests live in `wishlists` and use the plain `conftest.py` fixtures,
      never seed data. Every test user has a distinct email.
- [ ] Docs: `docs/ARCHITECTURE.md` gets the new app, its dependency rule,
      and its per-app rules. `docs/VIEWS.md` gets the add and remove routes,
      the access rule (sign-in required, staff included, own wishlist only),
      and the fact that no URL takes a user id. `docs/FRONTEND.md` gets the
      button partial. The root `CLAUDE.md` project layout gains
      `wishlists/`.

---

## Phase 2: The My wishlist page

**User stories**: 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 21

### What to build

Signed-in users get a "Wishlist" link in the navbar alongside Orders,
Addresses, and Security. It leads to `/wishlist/`, which extends the base
template and follows the new-page checklist. The page's list is a contents
partial: one row per saved product, newest first, each with the product
image (`loading="lazy"`), name, price, a link to its product page, the
existing warning badge reading "Unavailable" where it applies, and a Remove
button. With no items, the partial shows a designed empty state that tells
the customer how to start saving products.

Each Remove button HTMX-POSTs to `wishlists:remove_item` and swaps the whole
contents partial, as the cart page does. The item is looked up through the
requester's wishlist, so another user's item pk returns 404. Removing the
last item shows the empty state in place.

### Acceptance criteria

- [ ] The navbar shows "Wishlist" to signed-in users only.
- [ ] Signed-out requests to the page and to `remove_item` go to login.
- [ ] The page lists items newest first, with image, name, price, and a
      product link. An unavailable product shows the Unavailable badge.
- [ ] An empty wishlist shows the empty state.
- [ ] `remove_item` deletes the item and returns the contents partial alone.
      After the last item is removed, the partial shows the empty state.
- [ ] `remove_item` on another user's item returns 404 and leaves that item
      untouched.
- [ ] Each user's page, staff included, shows only their own items.
- [ ] A product deleted by the store no longer appears on the page.
- [ ] The style guard covers the new page and passes.
- [ ] Docs: `docs/VIEWS.md` gets the detail and `remove_item` routes.
      `docs/FRONTEND.md` gets the navbar entry and the contents partial.

---

## Phase 3: Seeded demo wishlist

**User stories**: 22

### What to build

`seed` gives the demo `customer` a wishlist of three or four products, at
least one of them unavailable. Their `added_at` values are backdated relative
to the run, so the newest-first order shows right after seeding. The
architecture doc's seed exception is extended to cover `wishlists`.

### Acceptance criteria

- [ ] After seeding, `customer` has 3–4 wishlist items, including at least
      one unavailable product, with distinct `added_at` values in the past.
- [ ] Seeding twice still gives the same wishlist (idempotent).
- [ ] The full suite is green, and Ruff is clean.
- [ ] Docs: `docs/ARCHITECTURE.md`'s seed exception names `wishlists`. The
      `seed` docstring and its summary output mention the wishlist.
