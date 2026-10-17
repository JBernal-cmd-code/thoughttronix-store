# PRD: The ThoughtTronix Store — Customer Wishlist

*Commissioned by ThoughtTronix Product Management. "Your Thoughts, Our Business."*

---

## Problem Statement

Today a ThoughtTronix customer who finds a product they want, but aren't ready to buy, has nowhere to keep it. The only list on the account is the cart. The cart means "I'm buying this," it won't take a product that is unavailable, and it fills checkout with things the customer didn't mean to buy yet.

So customers lose track of products they were interested in. To find one again they have to remember its name and search the catalog. And a product they wanted but found unavailable is easy to forget about completely.

## Solution

A **wishlist**: one private list per customer of products they want to keep an eye on.

- **Save from the product page.** Every product detail page has a "Save to wishlist" button. Clicking it saves the product and the button changes to show that it's saved, without reloading the page. Clicking again removes it, also without reloading.
- **My wishlist page.** A "Wishlist" link in the navbar opens the customer's saved products, newest first, each with a link to its product page and a Remove button. Removing an item updates the list in place. An empty wishlist shows a designed empty state.
- **Unavailable products welcome.** A customer can save a product even when it's unavailable. The wishlist shows it with an "Unavailable" badge, so they know to check back.
- **Private.** Only the owner ever sees a wishlist. There's no sharing, no staff view, and no admin view.

Visitors who aren't signed in see a "Save to wishlist" link that takes them to sign-in and brings them back to the product. Staff who shop have their own wishlist like any other user.

## User Stories

**Customer on a product page**

1. As a customer, I want a "Save to wishlist" button on each product's detail page, so that I can keep track of products I'm interested in.
2. As a customer, I want saving a product to happen without reloading the page, so that I don't lose my place.
3. As a customer, I want the button to show when a product is already on my wishlist, so that I know its status at a glance.
4. As a customer, I want to remove a saved product from its detail page with the same button, without reloading the page, so that I can change my mind just as easily.
5. As a customer, I want saving the same product twice (a double click, or two open tabs) to leave it on my wishlist only once, so that my list never has duplicates.
6. As a customer, I want removing a product that's already gone from my wishlist to do nothing, so that a stale tab can't put my list in a confusing state.
7. As a customer, I want to save a product that's currently unavailable, so that I can come back to it when it returns.

**Customer viewing their wishlist**

8. As a customer, I want a "Wishlist" link in the navbar, so that I can find my saved products from anywhere in the store.
9. As a customer, I want my wishlist page to show each saved product's image, name, and price, so that I can recognize what I saved.
10. As a customer, I want my saved products listed newest first, so that what I saved most recently is at the top.
11. As a customer, I want each item to link to its product page, so that I can read more or add it to my cart.
12. As a customer, I want saved products that are now unavailable to show an "Unavailable" badge, so that I know why I can't buy them right now.
13. As a customer, I want a Remove button on each item that updates the list without reloading the page, so that pruning my wishlist is quick.
14. As a customer, I want a friendly empty state when my wishlist has nothing in it, so that the page tells me how to start saving products rather than looking broken.
15. As a customer, I want a product to drop off my wishlist if the store deletes it, so that my list never shows something that no longer exists.

**Privacy**

16. As a customer, I want my wishlist visible only to me, so that what I'm interested in stays my business.
17. As a customer, I want no URL or request to let anyone else view or change my wishlist, so that guessing or tampering with links gets nowhere.
18. As a customer, I want ThoughtTronix staff unable to browse my wishlist, so that "private" means private from the store too.

**Visitor**

19. As a visitor who isn't signed in, I want the product page to offer "Save to wishlist" as a link to sign in, so that I learn the feature exists and can use it after signing in.
20. As a visitor, I want sign-in to return me to the product I was looking at, so that I can save it right away.

**Staff**

21. As a staff member, I want my own wishlist like any customer, so that I can save products when I shop too, and see only my own.

**Demo and review**

22. As a developer or reviewer, I want the seeded demo customer to already have a few wishlist items, one of them unavailable, so that I can see the wishlist page, its ordering, and the Unavailable badge right after seeding.

## Implementation Decisions

**A new `wishlists` app**

- The wishlist lives in its own app with its own URL namespace (`wishlists:`) and its own template directory.
- Dependency rule: `wishlists` imports from `products` (and may import from `accounts`, like every app). Nothing imports from `wishlists`, except the `seed` command, which already builds the whole demo world. The architecture doc's app-dependency rules and its seed exception are updated to say so.

**Models**

- `Wishlist`: one per user (a one-to-one link to the user, deleted with the user). It is created lazily the first time it's needed, through a `Wishlist.for_user(user)` class method, the same way the cart works. Nothing else creates wishlists.
- `WishlistItem`: a wishlist, a product, and an `added_at` timestamp. A unique constraint on (wishlist, product) means a product appears at most once. Deleting a product deletes its wishlist items (cascade). Items are ordered newest first. `added_at` is a default rather than auto-set, so `seed` can backdate it.
- Model methods hold the logic: the wishlist adds a product (with get-or-create, so adding twice does nothing), removes a product (removing a product that isn't saved does nothing), and reports whether a product is saved. Views stay thin and call these methods. No service module is needed, since nothing here spans several models.

**Views and URLs**

All wishlist views require sign-in (`LoginRequiredMixin`): signed-out visitors go to login. Every signed-in user, staff included, gets in, and every view acts only on the requester's own wishlist. No URL takes a user id or a wishlist id.

- `wishlists:detail` — `/wishlist/`, the "My wishlist" page: the requester's items, newest first, with product image, name, price, link, an Unavailable badge where it applies, and a Remove button. It has a designed empty state.
- `wishlists:add` — POST only, takes a product pk. It adds the product to the requester's wishlist (any product, available or not; a pk that doesn't exist is a 404) and re-renders the wishlist button partial in its "saved" state.
- `wishlists:remove` — POST only, takes a product pk. It removes the product from the requester's wishlist, if it's there, and re-renders the wishlist button partial in its "not saved" state.
- `wishlists:remove_item` — POST only, takes a wishlist item pk. The item is always looked up through its owner (filtered by the requester's wishlist), never by bare pk, so another user's item returns a 404. It deletes the item and re-renders the wishlist contents partial, which shows the empty state once the last item is gone.
- Add and remove are separate endpoints, not a single toggle, so each request states what the customer meant. Repeating a request, or sending it from a stale tab, can't flip the state by mistake.
- The product detail view adds one fact to its context: whether the product is on the requester's wishlist (false for signed-out visitors).

**HTMX and templates**

- The detail-page control is a wishlist button partial, included next to Add to cart. It has three states:
  - **Signed out:** a plain "Save to wishlist" link to the login page with `next` set to the current product page. No HTMX.
  - **Signed in, not saved:** a "Save to wishlist" button that HTMX-POSTs to `wishlists:add` and swaps itself out (`outerHTML`).
  - **Signed in, saved:** a "Saved ✓ — Remove" button that HTMX-POSTs to `wishlists:remove` and swaps itself out.
- The wishlist page's list is a contents partial: the item rows or the empty state. Remove buttons HTMX-POST to `wishlists:remove_item` and swap the whole contents partial, as the cart page does.
- Partials follow the frontend conventions: in the app's `partials/` directory, underscore-prefixed, never extending the base template.
- The wishlist page extends the base template and follows the new-page checklist (the heading pattern, `{% url %}` links, product images per the image conventions with `loading="lazy"`, no inline styles).
- Styling: "Save to wishlist" is an outline small button, "Saved" is a secondary small button. Unavailable items use the existing warning badge.
- Navigation: signed-in users get a "Wishlist" link in the navbar alongside Orders, Addresses, and Security. It has no count badge, so the responses don't need an out-of-band swap.

**Privacy**

- The wishlist models are not registered in Django admin. There is no back-office page and no dashboard figure for wishlists.
- Privacy is enforced by scoping: every query goes through the requester's own wishlist. A request can't name another user's wishlist, and a guessed item pk that isn't the requester's returns a 404.

**Seed**

- `seed` gives the demo `customer` a wishlist of three or four products, at least one of them unavailable, with `added_at` values backdated relative to the run so the newest-first order is visible.

**Docs**

- `docs/ARCHITECTURE.md`: the new app, its dependency rule, its per-app rules, and the extended seed exception.
- `docs/VIEWS.md`: the wishlist routes, the access rule (sign-in, staff included, own wishlist only), and that no URL takes a user id.
- `docs/FRONTEND.md`: the navbar entry and the wishlist partials.
- The root `CLAUDE.md` project layout gains the `wishlists/` app.

**Testing**

- Tests live in the `wishlists` app and use plain fixtures from the project `conftest.py`, never seed data. Every test user has a distinct email.
- Privacy:
  - signed-out requests to every wishlist route go to login;
  - `remove_item` on another user's item returns 404 and leaves it untouched;
  - each user's wishlist page shows only their own items, staff included.
- Repeats: adding twice leaves one item, and removing an unsaved product succeeds and changes nothing.
- Button states: the detail page renders the right state for signed-out, not-saved, and saved; add and remove responses render the partial (not the full page) in the new state.
- Wishlist page: newest-first order, the Unavailable badge, the empty state, and the empty state appearing after the last `remove_item`.
- Unavailable products can be added. A nonexistent product pk returns 404.
- Cascade: deleting a product removes it from wishlists.
- Seed: the demo customer has the seeded items, including an unavailable one.
- The style guard covers the new page automatically.

## Out of Scope

- More than one wishlist per customer, named wishlists, or wishlist folders.
- Sharing a wishlist, public wishlist links, or gift registries.
- Any staff, back-office, Django admin, or dashboard view of wishlists, including anonymous totals such as "most-wishlisted products."
- Wishlist buttons on the catalog grid or category pages.
- A wishlist count badge in the navbar.
- Saving a product automatically after sign-in for visitors who clicked "Save to wishlist" while signed out.
- Notifications when a wishlisted product becomes available again or changes price.
- "Move to cart" or other actions that combine the wishlist and cart.
- Guest (session-based) wishlists for signed-out visitors.

## Further Notes

- The design deliberately copies the cart: a one-per-user parent created lazily through `for_user`, unique child rows, HTMX endpoints that re-render a partial, and items always fetched through their owner. Anyone who knows the cart code should find the wishlist code familiar.
- Unlike the cart, the wishlist accepts unavailable products. That's on purpose: keeping track of something you can't buy yet is a main reason to have a wishlist. A product can also become unavailable after it's saved, so the wishlist page has to handle unavailable items whatever the add rule is.
- Natural follow-ups if ThoughtTronix asks: catalog-grid buttons (loading saved state for the page in one query), a "back in stock" notice, and anonymous "most-wishlisted" totals on the dashboard. Each needs its own decision on privacy and scope.
