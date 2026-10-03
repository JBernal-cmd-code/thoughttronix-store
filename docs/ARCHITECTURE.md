# Architecture

Coupons, the address book, and the back-office order screens came after the
PRD and plan — the code, not those documents, is the reference for those
features.

## Conventions

Idiomatic Django throughout: class-based views, model methods, custom
managers/querysets, forms own their validation.

Exactly two deliberate deep modules, docstrings and type hints on every
public function:

- `orders/services.py` — `place_order`, which applies `coupon_code` and
  raises `CouponError` for a code that won't apply.
- `dashboard/queries.py` — the dashboard's aggregations.

Settings read from `.env` via environs, every one with a working default.

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
