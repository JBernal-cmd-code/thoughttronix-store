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
