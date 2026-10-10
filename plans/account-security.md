# Plan: Account Security Center

> Source PRD: `prd/account-security.md`. The PRD owns the requirements;
> this plan owns the sequence. Where the two differ, the PRD's wording wins.

## Architectural decisions

Durable decisions that apply across all phases:

- **Owning app**: `accounts`, and nothing else. `accounts` still imports from
  no other local app. No third-party auth packages: Django's built-in auth
  views, forms, and token generator are subclassed or configured, not rebuilt.
- **Models**:
  - `User.email` becomes required and unique (a unique constraint on the
    existing column, by migration, with no data cleanup needed). It's stored
    lowercase on every save path; lookups lowercase their input. Usernames
    stay the only sign-in identifier.
  - New `SecurityEvent`: FK to the user (cascade), `event_type`, timestamp,
    IP address, raw User-Agent, ordered newest first. There are five event
    types: signed in, failed sign-in, password changed, password reset, email
    changed. Sign-outs and reset requests are not recorded.
  - `SecurityEvent`'s manager has one recording method (user, event type,
    request). It takes the IP from the request's remote address and the
    User-Agent from its header, then deletes that user's events older than 90
    days. There's no scheduled job.
- **URLs** (all in the `accounts:` namespace under `/accounts/`):
  - Password reset: `password-reset/` (request), `password-reset/done/`,
    `reset/<uidb64>/<token>/` (confirm). Completion goes to the sign-in page
    with a success message, not a separate page.
  - Security Center: `security/` (hub), `security/password/`,
    `security/email/`.
  - No Security Center URL takes a user id. Every page acts on
    `request.user`.
- **Access**:
  - Security Center pages use `LoginRequiredMixin`: anonymous visitors go to
    login, and every signed-in user (staff included) gets in.
  - The reset request only matches users who are **active, not staff, and have
    a usable password**. Everyone sees the same response either way.
- **Sessions**: Django's session auth hash covers the password. A reset
  therefore signs out every device, and a signed-in change keeps the current
  session (`update_session_auth_hash`) and signs out the others.
- **Email**: all messages are plain-text templates sent through the existing
  console backend.
- **Settings**: `PASSWORD_RESET_TIMEOUT = 3600`, a fixed value. No new
  environment variables, so the app still runs with no `.env`.
- **Thin views**: form logic lives in forms; event recording and pruning live
  on the manager.
- **Docs travel with the code**: there's no docs phase. Each phase updates the
  `docs/` files covering what it builds before the phase is called done.

---

## Phase 1: Email at signup

**User stories**: 1, 3

### What to build

Signup asks for an email address, and each email belongs to exactly one
account. A migration adds the unique constraint to the user's email. The
signup form gets a required email field, saves it lowercase, and refuses an
address that's already registered, regardless of capitalization. The refusal
is a field error saying the email is already in use. The form's "ask for the
minimum" docstring now explains why email is part of that minimum.

Every user built in the test suite gets a distinct email, since a blank email
would collide once the column is unique. That covers the shared fixtures and
the ad-hoc `other` and superuser users in the app test files.

### Acceptance criteria

- [ ] Signing up without an email is refused.
- [ ] `Casey@Example.com` is saved as `casey@example.com`.
- [ ] Signing up with an email registered in any capitalization gets the
      "already in use" field error and creates no user.
- [ ] The migration applies cleanly to the seeded database.
- [ ] Every test user has a distinct email, and the full suite is green.
- [ ] Docs: `docs/ARCHITECTURE.md` (accounts rules) records that email is
      required, unique, and stored lowercase. `docs/TESTING.md` records that
      every test user needs a distinct email.

---

## Phase 2: Forgot password, end to end

**User stories**: 2, 4, 5, 6, 7, 8, 9, 10, 11, 27, and 19 (the reset half)

### What to build

A customer who forgot their password can get back in without help.

1. The sign-in page links to the forgot-password page. The duplicate-email
   error on signup now shows that link too.
2. The customer enters an email. The input is lowercased and matched against
   active, non-staff accounts with a usable password.
3. Every visitor then sees the same "If an account exists for that email…"
   page. It shows the submitted address unmasked and suggests checking the
   spelling. The address reaches that page through the session, never the URL.
4. A matching account gets a plain-text email with its username and a link
   that works once and expires after one hour.
5. Setting a new password signs out every existing session. The customer goes
   to the sign-in page with a success message and gets a "your password was
   changed" notice email.

### Acceptance criteria

- [ ] The sign-in page links to the forgot-password page. A duplicate email on
      signup shows the same link.
- [ ] A registered customer's email, in any capitalization, sends one email
      containing their username and a working reset link.
- [ ] An unregistered email, a staff account's email, an inactive account's
      email, and an account with an unusable password all send no email and
      show the same done page.
- [ ] The done page shows the typed address. The address never appears in a
      URL.
- [ ] A used link and a link older than one hour are both rejected.
- [ ] After a reset, the user isn't signed in, lands on sign-in with a success
      message, and gets a password-changed notice email. A session from before
      the reset is no longer authenticated.
- [ ] `PASSWORD_RESET_TIMEOUT` is one hour.
- [ ] Docs: `docs/VIEWS.md` lists the reset URLs and the staff exclusion.
      `docs/ARCHITECTURE.md` notes the reset timeout setting and the
      plain-text email templates.

---

## Phase 3: Security Center hub and change password

**User stories**: 12, 13, 14, 15, 19 (the signed-in half), 26

### What to build

Signed-in users get a "Security" link in the nav, next to "Addresses." It
leads to the Security Center hub at `/accounts/security/`, which shows the
username, the current email, and a link to Change password. The Change email
link is added in Phase 4, along with the page it points to.

The change-password page uses Django's password change form: the current
password plus the new one twice, checked by the project's validators. On
success, this session stays signed in and every other session is signed out.
A notice email goes to the account email, and the user returns to the hub
with a success message. Staff use the same pages.

### Acceptance criteria

- [ ] The nav shows "Security" to signed-in users only.
- [ ] Anonymous visitors to any Security Center page are sent to login.
      Customers and staff both get in.
- [ ] The hub shows the signed-in user's username and email.
- [ ] A wrong current password is refused. A new password the validators
      reject is refused.
- [ ] A successful change keeps the current session signed in, signs out
      another session for the same user, sends the notice email, and returns
      to the hub with a success message.
- [ ] Docs: `docs/VIEWS.md` lists the Security Center URLs and their access
      rule. `docs/FRONTEND.md` notes the nav link.

---

## Phase 4: Change email

**User stories**: 16, 17, 18

### What to build

On the change-email page, a signed-in user enters the new email twice and
their current password. The form checks four things:

- the two emails match;
- the password is correct;
- the lowercased email isn't used by another account;
- it differs from the current email.

The duplicate error uses signup's "already in use" wording, without the
forgot-password link. The change takes effect immediately, with no
confirmation link. A notice goes to the **old** address saying the email
changed and to contact the store if it wasn't them. The user returns to the
hub, which links here, with a success message.

### Acceptance criteria

- [ ] Mismatched emails, a wrong password, an email used by another account
      (in any capitalization), and the user's own current email are each
      refused with a clear field error.
- [ ] A valid change saves the new email lowercase and sends the notice to the
      old address, not the new one.
- [ ] Success returns to the hub with a success message, and the hub shows the
      new email.
- [ ] The hub links to the change-email page.
- [ ] Docs: `docs/VIEWS.md` adds the change-email URL. `docs/ARCHITECTURE.md`
      notes that a change takes effect without confirmation.

---

## Phase 5: Security activity, sign-ins

**User stories**: 20, 21, 24, 25

### What to build

This phase adds the `SecurityEvent` model with its recording-and-pruning
manager method, and connects the first event source: Django's
`user_logged_in` signal records a "signed in" event on every successful
sign-in.

A small helper with no external dependency turns a User-Agent into a short
"Browser on OS" label, such as "Firefox on Windows." It recognizes common
browsers and operating systems and falls back to a generic label otherwise.

The hub shows the user's 10 most recent events, each with when it happened,
the IP address, and the device label. When there are no events yet, the list
shows a designed empty state.

### Acceptance criteria

- [ ] Signing in records a "signed in" event with the request's IP and
      User-Agent.
- [ ] Recording an event deletes that user's events older than 90 days and
      leaves other users' events alone.
- [ ] The device label reads correctly for common browser/OS pairs and falls
      back to a generic label for an unknown or empty User-Agent.
- [ ] The hub shows at most 10 events, newest first, only the signed-in
      user's, each with time, IP, and device. With no events, it shows the
      empty state.
- [ ] Docs: `docs/ARCHITECTURE.md` describes `SecurityEvent`, its manager
      method, 90-day retention, the remote-address IP caveat behind a proxy,
      and the signal receiver.

---

## Phase 6: Security activity, failed sign-ins, account changes, and seed history

**User stories**: 22, 23, 32

### What to build

Phase 6 connects the remaining four event sources:

- **Failed sign-ins** come from Django's `user_login_failed` signal. The event
  is recorded only when the typed username belongs to an existing user.
  Attempts against unknown usernames are dropped.
- **Password changes, password resets, and email changes** are recorded by
  the Phase 2–4 views when they succeed.

The `seed` command gives the `customer` demo user a short, realistic history
of 5–6 events over the past few weeks: several sign-ins from different
devices, a password change, and one failed sign-in from an unfamiliar IP. The
timestamps are relative to when the seed runs, so pruning never removes them.
The IPs come from the documentation ranges `203.0.113.0/24` and
`198.51.100.0/24`.

### Acceptance criteria

- [ ] A wrong password on an existing username records a "failed sign-in"
      event for that user. A wrong unknown username records nothing.
- [ ] A successful signed-in password change, a completed reset, and a
      successful email change each record their own event type.
- [ ] All five event types appear on the hub with readable labels.
- [ ] After seeding, `customer` has 5–6 events within the last 90 days. One is
      a failed sign-in from an IP different from the others, and every seeded
      IP is in a documentation range.
- [ ] Seeding twice still yields the same history (idempotent).
- [ ] Docs: `docs/ARCHITECTURE.md` lists every event source. The `seed`
      docstring and its summary output mention the security history.

---

## Phase 7: Admin audit log and staff recovery

**User stories**: 28, 29, 30, 31

### What to build

`SecurityEvent` is registered in Django admin. The list shows user, event
type, time, IP address, and device label. It filters by event type and
searches by username. Add, change, and delete are blocked for everyone,
superusers included, so the log can be trusted as an audit record.

Staff recovery needs no new feature. Tests confirm that the admin can still
set an employee's password from the user admin. The admin's own recovery
through Django's `changepassword` command is recorded in the docs.

### Acceptance criteria

- [ ] A superuser can view the `SecurityEvent` changelist, filter it by event
      type, and search it by username.
- [ ] Add, change, and delete are all refused for a superuser.
- [ ] A superuser can change a staff user's password through the user admin.
- [ ] The full suite is green, and Ruff is clean.
- [ ] Docs: `docs/ARCHITECTURE.md` records the read-only admin and the staff
      and admin recovery paths. It also records the PRD's accepted
      enumeration leak at signup and change email, so nobody assumes the
      system is enumeration-proof.
