# Frontend

## Templates

- Project-level templates (`base.html`) live in `templates/`; app templates
  live in `templates/<app>/`.
- Every page extends `templates/base.html` (DaisyUI navbar, footer motto).
  Back-office pages extend `templates/backoffice/base.html` instead — see
  `docs/VIEWS.md`.
- HTMX endpoints render partials from `templates/<app>/partials/_<name>.html` —
  prefixed with an underscore, never extending `base.html`.
- Every list view gets a designed empty state, not a blank page.

## Wishlist button

`wishlists/partials/_wishlist_button.html` sits next to Add to cart on the
product detail page, driven by `on_wishlist`. Three states:

- Signed out: a plain "Save to wishlist" link (outline small button) to
  login, with `next` set to the product page. No HTMX.
- Signed in, not saved: an outline small "Save to wishlist" button that
  HTMX-POSTs to `wishlists:add` and swaps itself (`outerHTML`).
- Signed in, saved: a secondary small "Saved ✓ — Remove" button that
  HTMX-POSTs to `wishlists:remove` and swaps itself.

## Wishlist contents

`wishlists/partials/_wishlist_contents.html` is the My wishlist page's list,
inside `#wishlist-contents`: a table row per item (lazy thumbnail, name
linking to the product, price, the warning "Unavailable" badge where it
applies, a Remove button), or the empty state. Remove HTMX-POSTs to
`wishlists:remove_item` and swaps the whole partial, as the cart does. No
navbar count badge, so no out-of-band swap.

## Navigation

- Signed-in users see Orders, Addresses, Security (the Security Center,
  `accounts:security`), and Wishlist (`wishlists:detail`) in the navbar;
  staff also see Back office.
  Anonymous visitors see only Sign in and Sign up.

## New pages: checklist

`config/test_style_guard.py` enforces the first three points.

- Starts with `{% extends "base.html" %}` (or `backoffice/base.html`) and fills
  `{% block title %}` and `{% block content %}`.
- No `<html>`, `<head>`, or `<body>` — `base.html` owns those.
- No `<style>`, no `<link rel="stylesheet">`, no new files in `assets/css/`,
  and no fixed `style="..."`. An inline style is allowed only when its value
  is computed in the template (e.g. a chart bar's width).
- Reuse the existing patterns:
  - page heading: `<h1 class="text-3xl font-bold">`
  - tables: `overflow-x-auto rounded-box bg-base-100 shadow-md` wrapping a
    `table` with `thead`/`tbody`
  - status: `badge` (`badge-error`, `badge-warning`, `badge-success`, …)
  - notices: `alert alert-<kind>` with `role="alert"`
  - actions: `btn btn-primary`; inline links: `link link-primary`
  - links use `{% url %}`, never hard-coded paths

## Styling

- Tailwind + DaisyUI classes only; no crispy-forms, no JavaScript beyond HTMX.
- DaisyUI theme: `night`, set in `assets/css/source.css` and `data-theme` on
  `<html>`.
- `assets/css/source.css` is the Tailwind input.

## Static assets

- HTMX is vendored at `assets/js/htmx.min.js`, not loaded from a CDN.
- Category placeholder images live in `assets/images/placeholders/` —
  400×500 SVGs, the same 4:5 frame as product images.

## Product images

- Every product image is 4:5 portrait. Render it with
  `src="{{ product.image_url }}"` (upload or placeholder, never broken),
  `alt="{{ product.name }}"`, `width="800" height="1000"`, and
  `class="aspect-[4/5] … object-cover"` plus a width class.
- Add `loading="lazy"` wherever many appear at once (the catalog grid, the
  back-office list, the wishlist); not on the detail page.
- Shown on the catalog, the detail page, the wishlist, and the back-office
  product list and form. Not yet in the cart, order history, or receipts.
- Forms that upload need `enctype="multipart/form-data"`. The product
  form's image field renders through `products/partials/_image_field.html`.
