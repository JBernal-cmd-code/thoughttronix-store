# Architecture

Coupons, the address book, and the back-office order screens came after the
PRD and plan — the code, not those documents, is the reference for those
features.

## Conventions

Idiomatic Django throughout: class-based views, model methods, custom
managers/querysets, forms own their validation.

Exactly three deliberate deep modules, docstrings and type hints on every
public function:

- `orders/services.py` — `place_order`, which applies `coupon_code` and
  raises `CouponError` for a code that won't apply.
- `dashboard/queries.py` — the dashboard's aggregations.
- `products/images.py` — `prepare_product_image`, the one door every
  product image comes through: it validates an upload, center-crops it to
  4:5, resizes it to 800×1000, and encodes WebP, or raises
  `ValidationError` with a plain-language reason. Callers:
  `ProductForm.clean_image`, `ProductAdmin` (via `form = ProductForm`),
  and `seed`.

Settings read from `.env` via environs, every one with a working default.

Uploaded media lives in `MEDIA_ROOT` (`media/`, gitignored), served by
`config/urls.py` only when `DEBUG` is on. Known gap: with `DEBUG=False`
nothing serves media (or static files — there's no whitenoise yet).

## App dependencies

- `accounts` imports from no local app; everything else may import from it.
- `coupons` imports from `products`; `orders` imports from `coupons`, never
  the reverse.
- `wishlists` imports from `products`. Nothing imports from `wishlists`.
  The product detail view reads whether a product is saved through the
  reverse relation (`product.wishlist_items`), not the `Wishlist` model.
- `reviews` imports from `products` and `orders` (and `accounts`). Nothing
  imports from `reviews`. The product detail view builds the reviews
  section through the reverse relation
  (`product.reviews.section(product, user)`), not the `Review` model.
- Exception: the `seed` command (`products/management/commands/seed.py`)
  builds the whole demo world, so it imports from `coupons`, `orders`, and
  `wishlists`.

## Per-app rules

**accounts**

- `accounts.User` is `AbstractUser` + nullable `job_title`.
- `User.email` is required and unique, and stored lowercase.
  `User.clean()` lowercases it, and ModelForm validation runs `clean()`
  before the uniqueness check, so signup and the admin's user forms both
  refuse a registered email in any capitalization ("That email address is
  already in use."). Code that saves a `User` without a form must lowercase
  the email itself. Lookups by email lowercase their input; nothing needs
  a case-insensitive comparison. Usernames stay the only sign-in
  identifier.
- Forgot password reuses Django's reset views, forms, and token generator
  (routes and the staff exclusion are in `docs/VIEWS.md`).
  `PASSWORD_RESET_TIMEOUT` is a fixed one hour (`3600`) in settings, not
  an env setting. Links are single-use because the token covers the
  password hash. A reset invalidates every existing session, since the
  session auth hash covers the password too.
- Changing the account email takes effect immediately: the new address is
  **not** confirmed by a link. `ChangeEmailForm.save()` sets it (lowercase)
  and calls `User.send_email_changed_notice(old_email)`, which writes to
  the **old** address, where the real owner will still read it.
- Account emails are plain-text templates in `templates/accounts/emails/`
  (`password_reset.txt` + `_subject.txt`, `password_changed.txt`,
  `email_changed.txt`), sent through the console backend.
  `User.send_password_changed_notice()` sends the password-changed notice
  after a completed reset and after a signed-in password change.
- `SecurityEvent` is the account's security activity log: the user
  (cascade), an `event_type` (signed in, failed sign-in, password changed,
  password reset, email changed), `created_at`, `ip_address`, and the raw
  `user_agent`, newest first. Sign-outs and reset requests are not
  recorded. `created_at` is a default, not `auto_now_add`, so history can
  be backdated.
  - Write events only through `SecurityEvent.objects.record(user,
    event_type, request)`. It takes the IP from `REMOTE_ADDR` and the
    User-Agent from its header (a `None` request records neither). Then it
    deletes that user's events older than 90 days
    (`SECURITY_EVENT_RETENTION`). Retention needs no scheduled job, and
    other users' events are untouched. An inactive account keeps old
    events until its next one.
  - Known gap: behind a reverse proxy `REMOTE_ADDR` is the proxy's address.
    Forwarded-for headers are not handled.
  - `SecurityEvent.device` is the User-Agent as a "Browser on OS" label
    from `accounts/user_agents.py` (`describe_user_agent`, no
    dependencies), falling back to "Unknown device".
  - Event sources, one per event type:
    - **Signed in**: `accounts/signals.py` (connected in
      `AccountsConfig.ready()`), on Django's `user_logged_in` signal.
      That includes `Client.force_login` in tests.
    - **Failed sign-in**: `accounts/signals.py`, on `user_login_failed`.
      The signal carries only the typed credentials, so it's recorded only
      when the typed username belongs to an existing user. Attempts on
      unknown usernames are dropped. The password-change and change-email
      forms check the password directly, so a wrong password there is not
      a failed sign-in.
    - **Password changed**: `ChangePasswordView.form_valid`.
    - **Password reset**: `PasswordResetSetView.form_valid`, when the new
      password is set (not when the link is requested).
    - **Email changed**: `ChangeEmailView.form_valid`.
  - `seed` backdates a short history for `customer` with `create`, not
    `record`: sign-ins from a laptop and a phone, a password change, and
    one failed sign-in from an unfamiliar IP. IPs are from the
    documentation ranges (`203.0.113.0/24`, `198.51.100.0/24`) and times
    are relative to the run, so pruning never removes them.
  - The Security Center hub shows the signed-in user's 10 most recent
    events.
  - Django admin lists every user's events (user, type, time, IP, device),
    filtered by event type and searched by username. `SecurityEventAdmin`
    blocks add, change, and delete for everyone, superusers included, so
    the log is a trustworthy audit record: events come only from `record`
    (and `seed`) and go only by pruning or by deleting their user.
- Recovery without email: staff are excluded from the reset form, so a
  locked-out employee is recovered by the admin setting a new password
  from the user admin's "Reset password" form. A locked-out admin runs
  `uv run python manage.py changepassword <username>` on the server.
- Known, accepted enumeration leak: the forgot-password page reveals
  nothing about which emails are registered, but signup and change email
  do. Both must refuse a duplicate email, and the error says so. The only
  leak-free fix is email activation at signup, which is out of scope. The
  system is **not** enumeration-proof.
- `Address` is untyped — shipping vs billing is a fact about a checkout, not
  about an address.
- `accounts/constants.py` is the home of `US_STATES` and `zip_validator`,
  which `orders` imports.

**products**

- `Category`, `Product`, `Tag`.
- `Product.image` is optional and always a processed 800×1000 WebP; nothing
  is stored without going through `prepare_product_image`. Each upload gets
  a fresh name (`products/<slug>-<random>.webp`) so browsers never show a
  cached old image.
- Templates use `Product.image_url`, never the field: it returns the upload
  only if the file exists in storage, else the category placeholder
  (`Category.placeholder_image`), so no image is ever broken.
- A replaced, cleared, or deleted product's old file is deleted on commit
  (`transaction.on_commit`). Deletion uses `post_delete`, which also fires
  for queryset deletes such as `seed`'s wipe.
- `products/seed_images/<slug>.jpg` — Marketing's images at full
  resolution; `seed` processes them like any upload. Products without one
  keep their placeholder.

**coupons**

- `Coupon` is order-wide or product-scoped. Its status is read off
  `starts_at`/`expires_at`, never stored.
- Back office has CRUD plus "Expire now". `CouponError` lives here.

**orders**

- Checkout includes the HTMX coupon preview.
- Orders snapshot any coupon (code, percent, per-line `discount`);
  `Order.total` is what was paid, after discount.
- `orders/validators.py` — checkout's card-number (Luhn) and expiry
  validators.
- `orders/context_processors.py` — the `cart` context processor (registered
  in settings).
- `orders/templatetags/cart_extras.py` — cart template filters.

**wishlists**

- Built like the cart. `Wishlist` is one per user (one-to-one, cascade),
  created lazily by `Wishlist.for_user(user)` and nowhere else.
  `WishlistItem` is a wishlist, a product, and `added_at`, unique per
  (wishlist, product), newest first. Deleting a product deletes its items.
  `added_at` is a default, not `auto_now_add`, so it can be backdated.
- Model methods hold the logic: `add` (get-or-create, so saving twice does
  nothing), `remove` (removing an unsaved product does nothing), `has`, and
  `lines` (items with products loaded, for display).
  No service module: nothing spans several models.
- Unlike the cart, any product can be saved, available or not.
- Private: the models are not registered in Django admin, and there is no
  back-office page or dashboard figure. Every query goes through the
  requester's own wishlist.
- `seed` gives `customer` four saved products, one of them unavailable
  (EchoPatch), with `added_at` backdated relative to the run so the
  newest-first order shows. The wipe needs no extra step: the wishlist
  cascades with its user.

**reviews**

- `Review` is a user (cascade), a product (cascade), a whole-star `rating`
  (1–5), a required `comment` (at most 2,000 characters; only whitespace
  counts as empty and is refused), `edited_by_staff` (default false), and
  `created_at` (a default, not `auto_now_add`, so it can be backdated; no
  `updated_at`). Unique per (user, product) at the database level. Newest
  first.
- **Eligibility** is `Review.is_eligible(user, product)`: the user's own
  account (`Order.user`) has an order containing the product that isn't
  Cancelled. Placed, Shipped, and Delivered all count; the names typed on
  an order give no one eligibility; product availability doesn't matter.
  Staff follow the same rule.
- **Checked once**, at creation. A later cancellation never removes or
  hides a review, so order status changes never need to know about
  reviews. Authors keep their edit and delete rights after a cancellation.
- `Review.can_be_changed_by(user)` is the single permission rule for
  editing and deleting: the author, or any staff member.
- `Review.edit(editor, rating, comment)` saves an edit. **The staff flag**:
  when the editor is staff and isn't the author, it sets
  `edited_by_staff`, and the card shows "Edited by staff." Nothing ever
  clears it, the author's later edits included. A staff member editing
  their own review is just an author. A staff delete is an ordinary
  delete: no soft delete, no notice, and no block on re-reviewing.
- `Review.author_name` is the display name: first name and last initial
  ("Jordan P."), the first name alone without a last name, and "Verified
  buyer" without a first name. Never the username or email. It lives on
  `Review`, so `accounts` stays unaware of reviews.
- `ReviewQuerySet.section(product, user)` builds a `ReviewSection` for one
  requester: count, average, their own review, whether they may review,
  and everyone else's reviews (newest first, their own excluded). It works
  through the reverse relation, which is how the product page reaches it.
- No service module: eligibility reads orders, but it's a query, not a
  multi-model workflow.
- Django admin lists every review (product, author, rating, date, the
  staff flag), filtered by rating and searched by product name and
  username. `ReviewAdmin` blocks add and change for everyone, superusers
  included, the same way `SecurityEventAdmin` is locked down, so the admin
  can't bypass the purchase rule or the staff flag. Delete is allowed.
  Moderation itself happens on the product page; there is no back-office
  reviews tab.
