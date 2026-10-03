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

## Styling

- Tailwind + DaisyUI classes only; no crispy-forms, no JavaScript beyond HTMX.
- DaisyUI theme: `night`, set in `assets/css/source.css` and `data-theme` on
  `<html>`.
- `assets/css/source.css` is the Tailwind input.

## Static assets

- HTMX is vendored at `assets/js/htmx.min.js`, not loaded from a CDN.
- Category placeholder images live in `assets/images/placeholders/`.
