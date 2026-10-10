# Views and URLs

Views are class-based and stay thin. Access rules (`StaffRequiredMixin`, the
`Own…Mixin` classes) are in the root `CLAUDE.md`.

## URLs

- Every URL is named; every app has a namespace (`products:catalog`,
  `orders:checkout`).
- Public catalog URLs use slugs (`/products/seraphine-home-hub/`);
  back-office URLs use pks.
- `Product` defines `get_absolute_url`.

## Forgot password

Django's own reset views, subclassed in `accounts/views.py` for this
project's templates. All are public, under `/accounts/`:

- `accounts:password_reset` — `password-reset/`, the email form. The login
  page links here, and so does signup's "already in use" email error.
- `accounts:password_reset_done` — `password-reset/done/`, the same "If an
  account exists for that email…" page for everyone. It shows the typed
  address, which arrives through the session (`password_reset_email`),
  never the URL.
- `accounts:password_reset_confirm` — `reset/<uidb64>/<token>/`, the
  new-password form. Success goes to `accounts:login` with a message; there
  is no "complete" page, and the user isn't signed in automatically.

**Staff exclusion:** `PasswordResetRequestForm` only matches users who are
active, **not staff**, and have a usable password. Staff (and the admin)
never get a reset email, and see the same done page, so nothing reveals the
account is staff. Their recovery goes through the admin.

## Security Center

How the signed-in user's account is protected, under `/accounts/security/`.
Access is `LoginRequiredMixin`: anonymous visitors go to login, and every
signed-in user, **staff included**, gets in. No URL takes a user id; every
page acts on `request.user`. Same list-page-plus-form-pages shape as the
address book.

- `accounts:security` — `security/`, the hub: username, email, links to
  change the password and the email, and the user's 10 most recent
  security events (with an empty state).
- `accounts:password_change` — `security/password/`, Django's
  `PasswordChangeView` (current password, new one twice). It keeps this
  session signed in and signs out every other one, sends the
  password-changed notice, and returns to the hub with a message.
- `accounts:email_change` — `security/email/`, a `FormView` around
  `ChangeEmailForm` (new email twice, current password). The form refuses
  a mismatch, a wrong password, the user's own email, and an email used by
  another account (signup's "already in use" wording, without the
  forgot-password link). On success the form saves the email lowercase and
  notifies the old address; the view returns to the hub with a message.

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
