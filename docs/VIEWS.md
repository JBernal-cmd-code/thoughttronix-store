# Views and URLs

Views are class-based and stay thin. Access rules (`StaffRequiredMixin`, the
`Own…Mixin` classes) are in the root `CLAUDE.md`.

## URLs

- Every URL is named; every app has a namespace (`products:catalog`,
  `orders:checkout`).
- Public catalog URLs use slugs (`/products/seraphine-home-hub/`);
  back-office URLs use pks.
- `Product` defines `get_absolute_url`.

## Forgot password

Django's own reset views, subclassed in `accounts/views.py` for this
project's templates. All are public, under `/accounts/`:

- `accounts:password_reset` — `password-reset/`, the email form. The login
  page links here, and so does signup's "already in use" email error.
- `accounts:password_reset_done` — `password-reset/done/`, the same "If an
  account exists for that email…" page for everyone. It shows the typed
  address, which arrives through the session (`password_reset_email`),
  never the URL.
- `accounts:password_reset_confirm` — `reset/<uidb64>/<token>/`, the
  new-password form. Success goes to `accounts:login` with a message; there
  is no "complete" page, and the user isn't signed in automatically.

**Staff exclusion:** `PasswordResetRequestForm` only matches users who are
active, **not staff**, and have a usable password. Staff (and the admin)
never get a reset email, and see the same done page, so nothing reveals the
account is staff. Their recovery goes through the admin.

## Security Center

How the signed-in user's account is protected, under `/accounts/security/`.
Access is `LoginRequiredMixin`: anonymous visitors go to login, and every
signed-in user, **staff included**, gets in. No URL takes a user id; every
page acts on `request.user`. Same list-page-plus-form-pages shape as the
address book.

- `accounts:security` — `security/`, the hub: username, email, links to
  change the password and the email, and the user's 10 most recent
  security events (with an empty state).
- `accounts:password_change` — `security/password/`, Django's
  `PasswordChangeView` (current password, new one twice). It keeps this
  session signed in and signs out every other one, sends the
  password-changed notice, and returns to the hub with a message.
- `accounts:email_change` — `security/email/`, a `FormView` around
  `ChangeEmailForm` (new email twice, current password). The form refuses
  a mismatch, a wrong password, the user's own email, and an email used by
  another account (signup's "already in use" wording, without the
  forgot-password link). On success the form saves the email lowercase and
  notifies the old address; the view returns to the hub with a message.

## Wishlist

The customer's private wishlist, in the `wishlists:` namespace. Access is
`LoginRequiredMixin`: anonymous visitors go to login, and every signed-in
user, **staff included**, gets in. Every view acts only on the requester's
own wishlist; no URL takes a user id or a wishlist id.

- `wishlists:detail` — `wishlist/`, the "My wishlist" page: the
  requester's items, newest first, with an empty state. Linked from the
  navbar.
- `wishlists:remove_item` — `wishlist/items/<item pk>/remove/`, POST only.
  The item is looked up through the requester's wishlist, never by bare
  pk, so another user's item is a 404 (staff included). Deletes it and
  re-renders the wishlist contents, which show the empty state once the
  last item is gone.
- `wishlists:add` — `wishlist/add/<product pk>/`, POST only. Saves the
  product (available or not; a missing pk is a 404) and re-renders the
  wishlist button in its saved state.
- `wishlists:remove` — `wishlist/remove/<product pk>/`, POST only. Removes
  the product if it's saved (otherwise does nothing) and re-renders the
  button in its not-saved state.

Add and remove are separate endpoints, not a toggle, so a repeated request
or a stale tab can't flip the state. The product detail view puts
`on_wishlist` in its context (false for signed-out visitors).

## Reviews

Product reviews, in the `reviews:` namespace. Every endpoint requires
sign-in, enforced on the server, through `HtmxLoginRequiredMixin`
(`accounts/mixins.py`): a signed-out request goes to login, and a
signed-out **HTMX** request gets an empty 200 with `HX-Redirect` to login
instead, so the whole browser navigates rather than the login page being
swapped into the section. Its `next` is the page the request came from
(the path and query of `HX-Current-URL`). No review URL takes a user id.

- `reviews:create` — `reviews/create/<product pk>/`, POST only. A missing
  product is a 404. In order:
  - Already reviewed (a stale tab or a double click): the section, with the
    existing review pinned and an "already reviewed" alert. Checked before
    eligibility, so a review outlives a later cancellation. A simultaneous
    duplicate, refused by the unique constraint (`IntegrityError`), is
    answered the same way.
  - Not eligible: 403, nothing created.
  - Invalid: the section, with the form's errors and the typed input.
  - Valid: saved, and the section re-renders.
- `reviews:edit` — `reviews/<review pk>/edit/`, GET. Returns the edit-form
  partial for that one card.
- `reviews:cancel` — `reviews/<review pk>/cancel/`, GET. Returns the card
  partial, unchanged.
- `reviews:update` — `reviews/<review pk>/update/`, POST only. Invalid: the
  edit-form partial with errors and the typed input, sent back into the
  card with `HX-Retarget: #review-<pk>` and `HX-Reswap: outerHTML` (the
  form itself targets the section). Valid: saved through `Review.edit`,
  and the section re-renders.
- `reviews:delete` — `reviews/<review pk>/delete/`, POST only. Deletes the
  review and re-renders the section, where the create form shows again if
  the customer is still eligible.

The four review-pk endpoints share `ChangeableReviewMixin`: the review is
looked up by pk and checked with `Review.can_be_changed_by`, and anyone
it doesn't allow gets a **404**, so the response doesn't reveal that the
review exists. A missing review is the same 404.

Swap rules: create, update, and delete return the whole section partial
(`reviews/partials/_reviews_section.html`), never the full page, so the
summary always matches the list. Edit and cancel swap only the one card
(`outerHTML` on `#review-<pk>`). The product detail view puts
`reviews_section` in its context, built through `product.reviews`.

## Back-office pages

- Back-office templates extend `templates/backoffice/base.html` — the staff
  shell with the tab rail.
- The active tab comes from the view's `section` context entry, set with
  `extra_context = {"section": ...}`. Values:
  - `products` — Products
  - `catalog` — Categories & tags (not the public catalog)
  - `orders` — Orders
  - `coupons` — Coupons
  - `dashboard` — Dashboard
