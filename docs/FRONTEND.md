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
- Category placeholder images live in `assets/images/placeholders/`.
