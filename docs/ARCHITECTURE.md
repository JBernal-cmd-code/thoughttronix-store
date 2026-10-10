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
- Exception: the `seed` command (`products/management/commands/seed.py`)
  builds the whole demo world, so it imports from `coupons` and `orders`.

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
