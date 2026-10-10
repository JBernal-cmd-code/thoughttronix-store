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
- Account emails are plain-text templates in `templates/accounts/emails/`
  (`password_reset.txt` + `_subject.txt`, `password_changed.txt`), sent
  through the console backend. `User.send_password_changed_notice()` sends
  the password-changed notice after a completed reset.
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
