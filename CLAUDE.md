# CLAUDE.md — The ThoughtTronix Store

A server-rendered Django 6 storefront and back office. The PRD (`prd/core-platform.md`) and the plan (`plans/core-platform.md`) record how the core platform was designed and built.

## Commands

- `uv sync` — install dependencies (Python 3.13, managed by uv)
- `uv run python manage.py migrate` — apply migrations
- `uv run python manage.py seed` — reset the database to the demo world
  (destructive, idempotent)
- `uv run python manage.py tailwind runserver` — dev server + Tailwind watch
- `uv run python manage.py tailwind build` — compile production CSS
- `uv run pytest` — run the test suite
- `uv run ruff check .` and `uv run ruff format .` — lint and format

## Project layout

- `config/` — the project package (settings, root urls)
- `accounts/` — custom user model, the customer address book, access mixins
- `products/` — catalog, its back-office CRUD, product images
  (`images.py`), and the `seed` command with its `seed_images/`
- `coupons/` — percent-off coupons and their back-office CRUD
- `orders/` — cart, checkout, orders, and back-office order management
- `dashboard/` — the staff analytics dashboard
- `PROMPTS.md` — the AI-usage log
- `templates/` — all templates, project-level and per app
- `assets/` — static sources (Tailwind input, vendored HTMX, images)

## Always

- Logic lives in models and managers; cross-model workflows get a service
  module; views stay thin.
- `PROMPTS.md`: append entries, never rewrite history.
- Never edit `assets/css/tailwind.css` — it's compiled output (gitignored).
- The app must run with no `.env` present.
- The suite must be green at every phase boundary.

## Access

- Roles are Django's own vocabulary: customers are plain users, employees are
  `is_staff`, the admin is `is_superuser`. No role field, no Groups.
- Back-office views are gated by `StaffRequiredMixin` (`accounts/mixins.py`):
  anonymous users go to login, non-staff get 403.
- Customer-owned data (orders, addresses) is scoped to the signed-in user
  through the `Own…Mixin` views.

## Docs

- Before changing models, services, settings, or which app imports which, read
  `docs/ARCHITECTURE.md`.
- Before adding or changing views, URLs, or back-office pages, read
  `docs/VIEWS.md`.
- Before touching templates, HTMX, or styling, read `docs/FRONTEND.md`.
- Before writing or changing tests, read `docs/TESTING.md`.
