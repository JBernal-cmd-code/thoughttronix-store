# Views and URLs

Views are class-based and stay thin. Access rules (`StaffRequiredMixin`, the
`Own…Mixin` classes) are in the root `CLAUDE.md`.

## URLs

- Every URL is named; every app has a namespace (`products:catalog`,
  `orders:checkout`).
- Public catalog URLs use slugs (`/products/seraphine-home-hub/`);
  back-office URLs use pks.
- `Product` defines `get_absolute_url`.

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
