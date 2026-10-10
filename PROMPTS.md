# PROMPTS.md — AI Usage Log

This file is the record of AI use on this codebase. At the end of every
agent session, direct the agent to write the session log with this prompt:

> Append a session log to PROMPTS.md at the repo root, under today's date,
> newest entry at the top. Record every prompt I gave you this session, in
> order, including any corrections. End the entry with a short summary:
> the outcome, any places where I deviated from a recommended answer or
> asked follow-up questions, and anything that went sideways.

Two rules:

- Entries are added only by that prompt, never unprompted.
- New entries go at the top. Never rewrite or delete an old entry — the
  log is part of your work, and an honest log of a session that went
  sideways is worth more than a tidy one.

Each entry has this shape:

    ## YYYY-MM-DD — <one-line summary>

    ### Prompts
    1. ...

    ### Summary
    - **Outcome:** what was built and what was kept
    - **Deviations:** recommendations overridden, follow-up questions asked
    - **Sideways:** failures, wrong turns, and how they were caught

## 2026-10-10 — Account Security Center: Phase 1, email at signup

### Prompts
1. `@prd/account-security.md @plans/account-security.md` Do Phase 1
2. How can I manually verify this phase in the browser?
3. Append a session log to PROMPTS.md at the repo root, under today's
   date, newest entry at the top. Record every prompt I gave you this
   session, in order, including any corrections. End the entry with a
   short summary: the outcome, any places where I deviated from a
   recommended answer or asked follow-up questions, and anything that
   went sideways.

### Summary
- **Outcome:** Phase 1 is implemented; nothing is committed.
  - `User.email` is required and unique, with the error "That email
    address is already in use." `User.clean()` lowercases it. Because
    ModelForm validation runs `clean()` before the uniqueness check,
    duplicates are refused in any capitalization.
  - Migration `accounts/0003_user_email_unique.py` adds the constraint.
  - `SignupForm` asks for email, with a hint, and its docstring explains
    why email is now part of "the minimum."
  - Every test user got a distinct email: the `customer` and `employee`
    fixtures, the four ad-hoc `other` users, and the `root` superuser.
  - 8 new tests in `accounts/tests.py`. The suite went from 330 to 338
    passing, and Ruff is clean.
  - `docs/ARCHITECTURE.md` and `docs/TESTING.md` were updated as the plan
    asks.
  - The migration was checked against a copy of `db.sqlite3` in the
    scratchpad, so the tracked snapshot is unchanged.
  - Prompt 2 got a step-by-step browser checklist covering signup, the
    case-insensitive duplicate check, and the admin add-user form. It also
    explained how to restore the snapshot afterwards.
- **Deviations:**
  - The user asked one follow-up question (prompt 2). The agent asked no
    questions and made no recommendations for the user to accept or
    override.
  - The agent went beyond the plan in two places, both reported:
    - It added email to `UserAdmin.add_fieldsets`, because the stock
      add-user form has no email field. Admin-created users would all get
      a blank email, and the second would crash on the constraint. One
      test covers it.
    - The migration also carries an `AlterModelOptions` for `Address`. That
      mismatch was already there: the model orders by `-id` while
      migration 0002 recorded `-pk`. It changes nothing in practice.
  - The PRD says normalization happens at signup and change email. The
    agent put it in `User.clean()` instead of the form, so the admin's
    user forms get it too. Code that saves a `User` without a form must
    still lowercase the email itself; `ARCHITECTURE.md` says so.
- **Sideways:**
  - The PRD says the database had 12 users, all with unique emails. The
    committed snapshot actually has 13. `jeber`, created 2026-10-10, has a
    blank email. One blank is allowed under the unique constraint, so the
    migration applied cleanly. The agent left the data alone and gave the
    user three choices: set an email in the admin, re-seed, or leave it.
    This is still undecided.
  - Whether to migrate the committed `db.sqlite3` itself is also left to
    the user.
  - `uv run` again warned that `VIRTUAL_ENV` pointed at another project's
    `.venv`. The agent ignored it and used the project environment.
  - The session started with `/clear`.

## 2026-10-10 — Account Security Center: seven-phase plan via prd-to-plan (no code yet)

### Prompts
1. `/prd-to-plan @prd/account-security-center.md`
2. Keep phases 5 and 6 separate. Also do not split phase 7 but instead
   move the seed history into phase 6 so that it lands with failed
   sign-ins. Phase 7 should become the admin audit log and staff
   recovery. And yes, the sign up link can wait for phase 2. Each phase
   should update the relevant docs for what it builds since there's no
   separate docs phase.
3. Append a session log to PROMPTS.md at the repo root, under today's
   date, newest entry at the top. Record every prompt I gave you this
   session, in order, including any corrections. End the entry with a
   short summary: the outcome, any places where I deviated from a
   recommended answer or asked follow-up questions, and anything that
   went sideways.

### Summary
- **Outcome:** This was a planning-only session; no application code
  changed. Following the `prd-to-plan` skill, the agent read the PRD; the
  `accounts` views, forms, URLs, models, admin, and mixins; `config/urls.py`;
  the settings for auth and email; the seed's user creation; the nav in
  `base.html`; `conftest.py`; all four `docs/` files; and
  `plans/core-platform.md`. It proposed seven vertical slices and asked
  three questions, then wrote `plans/account-security-center.md` (new,
  uncommitted) with the user's changes. The plan header holds the durable
  decisions: `accounts` owns everything, the `User.email` constraint, the
  `SecurityEvent` model and its manager method, the `accounts:` URLs,
  access rules, and session behavior. The seven phases are:
  1. email at signup
  2. forgot password, end to end
  3. Security Center hub and change password
  4. change email
  5. security activity: sign-ins
  6. failed sign-ins, account-change events, and seed history
  7. admin audit log and staff recovery

  Every phase's acceptance criteria end with a "Docs:" item naming which
  `docs/` files it updates. As in the earlier draft, Phase 1 gives
  every test user a distinct email, since the fixtures and the ad-hoc
  `create_user`/`create_superuser` calls create users with a blank
  email, and a unique column would make them collide.
- **Deviations:**
  - The agent asked three questions: should phases 5 and 6 merge, should
    Phase 7 split, and could the signup link wait for Phase 2.
  - The user kept 5 and 6 separate and agreed the link could wait.
  - On Phase 7, the user picked neither option. Instead they moved the
    seed history into Phase 6 to land with failed sign-ins, leaving Phase 7
    as the admin log and staff recovery.
  - The user added a requirement the agent hadn't proposed: each phase
    updates its own docs, since there's no docs phase.
- **Sideways:**
  - Nothing failed. No tests or commands were run, since only a plan was
    written.
  - In the first written version, Phase 3 hedged about whether the hub's
    Change email link could point to a page that didn't exist yet. The
    agent removed the hedge before reporting: the link now arrives in
    Phase 4, with its page.
  - `plans/account-security-draft.md`, which the previous entry says it
    wrote, was not in `plans/` when this session looked. This plan was
    written fresh from the PRD rather than revised from that draft.
  - The first attempt to insert this entry targeted the wrong anchor text
    and failed without changing the file; the second attempt succeeded.
  - The session started with `/clear`.

## 2026-10-10 — Account Security Center: implementation plan drafted (no code yet)

### Prompts
1. `@prd/account-security-center.md` Turn this into a multi-phase plan and
   save it to plans/account-security-draft.md.
2. Append a session log to PROMPTS.md at the repo root, under today's
   date, newest entry at the top. Record every prompt I gave you this
   session, in order, including any corrections. End the entry with a
   short summary: the outcome, any places where I deviated from a
   recommended answer or asked follow-up questions, and anything that
   went sideways.

### Summary
- **Outcome:** This was a planning-only session; no application code
  changed. The agent read the PRD, `plans/core-platform.md` (for its
  layout), the `accounts` models, views, forms, URLs, and admin, plus
  `conftest.py`, the seed's user creation, settings, and
  `docs/ARCHITECTURE.md` and `docs/TESTING.md`. It wrote
  `plans/account-security-draft.md` (new, uncommitted) with five phases:
  1. email on every account (tracer bullet)
  2. the Security Center page, the `SecurityEvent` log, sign-in and
     failed sign-in signals, and the read-only admin
  3. change password and change email, with notice emails
  4. the forgot-password flow
  5. seeded events, docs, and the final sweep

  Each phase has goals, tasks, automated and manual verification, and an
  out-of-bounds list. The plan ends with three open questions.

  Reading the code found a problem the PRD didn't mention. The test
  fixtures and five ad-hoc `create_user`/`create_superuser` calls create
  users with no email, so a unique email column would break the suite.
  Phase 1 fixes those tests first. The agent also found that Django's
  stock add-user admin form has no email field.
- **Deviations:**
  - The user asked no follow-up questions, and the agent asked none.
  - The plan goes beyond the PRD in a few places, each chosen by the agent
    and listed in the plan where it matters:
    - `User.save()` lowercases email as well as the forms (this is an
      open question in the plan)
    - `UserAdmin` gets an `add_fieldsets` that includes email
    - `SecurityEvent.created_at` uses `default=timezone.now`, not
      `auto_now_add`, so the seed can backdate events
    - `record()` accepts `request=None`
    - the reset flow ends at the login page, not Django's complete view
- **Sideways:**
  - Nothing failed. No tests or commands were run, since only a plan was
    written.
  - The first draft put the signup page's "Forgot your password?" link in
    Phase 1, before its URL existed, with a workaround. The agent moved it
    to Phase 4 before reporting.
  - The plan was written by hand, without the `prd-to-plan` skill. That
    skill only appeared in the skill list after the plan was finished.
  - The session started with `/clear`.

## 2026-10-10 — Account Security Center: design interview and PRD (no code yet)

### Prompts
1. `/grill-me` I want to design an Account Security Center for the
   ThoughtTronix Store. Right now customers can only sign up, sign in, and
   sign out, and once they're in there's almost nothing they can do with
   their account. If someone forgets their password, they're locked out of
   their order history. Customers should be able to give an email address
   when they sign up, change their password, and reset a forgotten password
   through email. Before asking me things you could find yourself, explore
   the codebase to see how accounts work today. Please do not write a PRD,
   plan, or any other documentation yet, because I'll ask for that
   separately once we finish the interview.I'm also open to one or two
   other security features that would make the Security Center more
   useful, so please suggest some and explain the tradeoffs.
2. (Grill-me answer — email required and unique) Option A is good
3. (Grill-me answer — email capitalization) Option A is good
4. (Grill-me answer — sign-in identifier) Option A is good
5. (Grill-me answer — forgot-password response for unknown emails)
   Option C, but show the email unmasked so the customer can actually spot
   a typo.
6. (Grill-me answer — reset link lifetime) Option B is good
7. (Grill-me answer — after a successful reset) Option A is good
8. (Grill-me answer — changing the account email) Option B is good
9. (Grill-me answer — Security Center page shape) Option A is good
10. (Grill-me answer — staff and email reset) B. Staff get the Security
    Center but no email reset. Admin recovers them, and manage.py
    changepassword is the fallback for the admin.
11. (Grill-me answer — extra security features) Option 1 is good
12. (Grill-me answer — which events are logged) Option B is good
13. (Grill-me answer — what each event stores) Option B is good
14. (Grill-me answer — retention and list length) Option B is good
15. (Grill-me answer — duplicate email at signup) Option B is good
16. (Grill-me answer — staff visibility of the log) Option B is good
17. (Grill-me answer — seeded demo activity) Option B is good
18. `/to-prd`
19. Append a session log to PROMPTS.md at the repo root, under today's
    date, newest entry at the top. Record every prompt I gave you this
    session, in order, including any corrections. End the entry with a
    short summary: the outcome, any places where I deviated from a
    recommended answer or asked follow-up questions, and anything that
    went sideways.

### Summary
- **Outcome:** This was a design-only session; no application code
  changed. The agent first read the `accounts` app, settings, templates,
  docs, and seed data. It found:
  - `User` is `AbstractUser`, with an email column that is optional, not
    unique, and never filled in by signup
  - only stock login and logout views, and no reset or change-password
    views
  - the console email backend already configured
  - the address book as the only signed-in account page

  It also queried the database: all 12 users have unique emails, so no
  question about migrating existing data was needed.

  Sixteen questions settled the design:
  - email required, unique, and lowercased when saved; username stays the
    sign-in identifier
  - Django's built-in reset with a 1-hour single-use link, a response that
    doesn't reveal whether the email exists, the username in the email,
    and no auto-login after a reset
  - change password and change email both behind the current password,
    with notice emails
  - a hub-plus-form-pages Security Center at `/accounts/security/`
  - staff get the center but no email reset
  - a `SecurityEvent` activity log: five event types, IP and device,
    90-day prune-on-write, latest 10 shown, read-only in Django admin,
    and seeded history for `customer`

  `/to-prd` wrote `prd/account-security-center.md` (new, uncommitted). No
  plan was written, and nothing is committed.
- **Deviations:**
  - Q4 (the forgot-password page): the user took Option C but overrode the
    masked display the option showed, choosing to show the email unmasked.
    The agent had said either was fine.
  - Q10 (extra features): the user chose only the activity log, against
    the recommended pairing of the activity log with sign-in throttling.
    Throttling is listed as out of scope.
  - Q9 the user restated Option B in their own words, adding the admin
    recovery path, which matched the recommendation's caveat.
  - Every other answer took the recommendation.
  - The user asked no follow-up questions.
  - The agent set several defaults without a question, flagging each in
    the interview: Django's stock change-password behavior, a
    "password changed" notice email, typing the new email twice, and the
    code placement, email, and test conventions. The PRD also added one
    rule that was never discussed: change email rejects the current
    address.
- **Sideways:**
  - Nothing failed.
  - Q14 caught a conflict between two earlier answers. The leak-free reset
    page (Q4) and unique emails (Q1) together mean signup reveals which
    emails are registered. The user accepted this as a documented leak.
  - `uv run` printed a warning that `VIRTUAL_ENV` pointed at another
    project's `.venv`; it was ignored and the project environment was
    used.
  - `/login` was run once at the start of the session; it's a CLI
    command, not a prompt to the agent.

## 2026-10-03 — Product images: implemented from HANDOFF.md

### Prompts
1. `@HANDOFF.md` Implement this feature
2. How can I manually verify this works in the browser?
3. Append a session log to PROMPTS.md at the repo root, under today's
   date, newest entry at the top. Record every prompt I gave you this
   session, in order, including any corrections. End the entry with a
   short summary: the outcome, any places where I deviated from a
   recommended answer or asked follow-up questions, and anything that
   went sideways.

### Summary
- **Outcome:** The design in `HANDOFF.md` was implemented in full;
  nothing is committed.
  - `products/images.py` holds `prepare_product_image`. It enforces
    10 MB, real decoding, JPEG/PNG/WebP only (with a HEIC export hint),
    and at least 800×1000 after the crop. It applies EXIF orientation,
    keeps transparency, center-crops to 4:5, and outputs an 800×1000 WebP.
  - `Product.image` (migration `0004`) has unique
    `products/<slug>-<random>.webp` names. `Product.image_url` checks the
    file exists before using it. Old files are deleted on commit when an
    image is replaced, cleared, or deleted, including `seed`'s bulk wipe.
  - The form gets the image through a plain `FileField` (so Django's
    generic image error never pre-empts ours), a picker-only widget, and
    `_image_field.html` with a preview and a Remove checkbox.
    `ProductAdmin` uses `ProductForm` and keeps the admin's own widget.
  - `MEDIA_*` settings, serving only when `DEBUG` is on, `media/`
    gitignored, and Pillow added.
  - Catalog, detail, back-office list thumbnails, and the form use 4:5
    images. All 7 placeholder SVGs were redrawn at 400×500.
  - 12 seed JPEGs (3.4 MB total) are in `products/seed_images/`; `seed`
    attaches them. `product-images/` was deleted as agreed, after checking
    all 12 JPEGs decode.
  - New `products/test_images.py`, a seed assertion for 12 images, and an
    autouse `media_root` fixture. Updated `docs/ARCHITECTURE.md`,
    `FRONTEND.md`, `TESTING.md`, and `CLAUDE.md`.
  - The suite is green (330 passed), ruff is clean, and every flow was
    checked with `curl` against the running dev server.
- **Deviations:**
  - No recommendation was overridden.
  - The user asked one follow-up (prompt 2): how to verify by hand in the
    browser. The agent gave a step-by-step checklist.
  - The agent's own departures from `HANDOFF.md`:
    - The temporary `MEDIA_ROOT` fixture is autouse for every test, not
      just uploading ones.
    - The admin keeps its own Clear widget.
    - The suggested `code-review` and `simplify` passes were not run.
  - The previous entry said 36 products; the seeded catalog has 34
    (12 with images, 22 on placeholders).
- **Sideways:**
  - The first image-conversion command hung on a stray `cat >` waiting for
    stdin. It was stopped and rerun as a script.
  - Regenerating the SVGs crashed on Windows' cp1252 console after
    writing one file. It was rerun with UTF-8 output and a pattern that
    also matched the already-converted file.
  - Ruff's DJ012 flagged the method order in `Product`; it was fixed.
  - `tailwind build` reported "up to date" and skipped the new
    `aspect-[4/5]` class. A `--force` rebuild fixed it.
  - To time the seed tests before the change, the agent ran
    `git stash` / `stash pop` on the working tree. The comparison was
    invalid (the untracked migration stayed behind and every test
    errored), but the tree was restored intact. That was a riskier move
    than the question deserved.
  - The `curl` smoke script needed several fixes: wrong back-office path,
    the `manage.py shell` banner, a `sed` edit that split a line, and
    `sh`'s `echo` mangling large HTML. One false "0 thumbnails" came from
    the agent's own over-broad `sed`; a direct fetch showed 34.
  - Adding images made the suite slower: the seed tests take about 12 s
    of a roughly 72 s run.

## 2026-10-03 — Product images: design interview and handoff (no code yet)

### Prompts
1. `/grill-me` I want to add product images to the ThoughtTronix catalog.
   Right now every product shows a placeholder. Marketing gave us a set of
   product images, which are in the product-images folder at the root of
   this repo. That folder is just a temporary holding spot, not Django's
   media directory. Every product has to show either its uploaded image or
   the existing placeholder, with no broken images. Images should look
   consistent across the catalog and pages need to stay fast. Employees
   will upload images through the back office, and if they upload a file
   the site can't use, it should be rejected with a plain-language
   explanation instead of being accepted and lost.
2. (Grill-me answer — how images reach products) Option 1. I want seed to
   always produce the full catalog with images, and running them through
   the same upload path tests the employee code too. Use the No Text
   version of SyncRest so it matches the other images.
3. (Grill-me answer — frame shape) Option 2 is fine.
4. (Grill-me answer — when to process) Option 2 is fine.
5. (Grill-me answer — images that are too small) Option 1 is good.
6. (Grill-me answer — missing files) Option 2 is good.
7. (Grill-me answer — old files) Option 2 is good.
8. (Grill-me answer — text-baked images) Option 3. I want all of
   Marketing's images showing, since placeholders tested poorly.
9. (Grill-me answer — SoulSear mapping) Option 1 is good.
10. (Grill-me answer — Calm Collar mismatch) Option 1 is good.
11. (Grill-me answer — where images appear) Options 2 is good.
12. (Grill-me answer — seed source format) Option 2 is good.
13. (Grill-me answer — where the processing code lives) Option 1 is good.
14. `/handoff` the next session implements the design we just agreed.
15. Append a session log to PROMPTS.md at the repo root, under today's
    date, newest entry at the top. Record every prompt I gave you this
    session, in order, including any corrections. End the entry with a
    short summary: the outcome, any places where I deviated from a
    recommended answer or asked follow-up questions, and anything that
    went sideways.

### Summary
- **Outcome:** This was a design-only session; no application code
  changed. The agent first explored the code and the image folder. It
  found:
  - no media setup, no `ImageField`, and no Pillow
  - 4:3 placeholder SVGs
  - 13 roughly 2 MB PNGs, mostly 4:5 portrait, covering 12 of the 36
    products
  - a destructive `seed`

  Thirteen questions settled the design:
  - images are seed assets processed through the employee upload path
  - a 4:5 frame
  - a single 800×1000 WebP made once at upload
  - JPEG/PNG/WebP only, at most 10 MB, and at least 800×1000 after
    cropping
  - an existence-checked `Product.image_url` with a placeholder fallback
  - files deleted after commit
  - thumbnails in the back-office product list
  - quality-90 JPEG seed sources in `products/seed_images/`
  - one `prepare_product_image` function in a new `products/images.py`,
    shared by the back-office form, the Django admin, and `seed`

  The full design and the image-to-product mapping are in `HANDOFF.md`
  (new, uncommitted). No `plans/` file was written. `product-images/` is
  still untracked; the design deletes it once the seed sources are
  converted.
- **Deviations:**
  - Q7 (the four images with marketing text baked in): the user chose
    Option 3, ship now and swap later, over the recommended Option 2,
    placeholders until Marketing sends no-text versions. Their reason was
    that placeholders tested poorly.
  - Every other answer took the recommendation.
  - In prompt 2 the user said the No Text SyncRest "matches the other
    images." The agent pointed out that several other images also have
    baked-in text, which led to Q7.
  - Prompt 3 ("Option 2 is fine") was taken as also accepting
    center-cropping, which Q2 had asked about separately.
  - The user asked no follow-up questions.
  - The agent's closing question, write `plans/product-images.md` or start
    implementing, went unanswered; the user ran `/handoff` instead.
- **Sideways:**
  - Nothing failed, but the interview grew three questions the original
    brief didn't anticipate, each found by inspecting files mid-interview.
    The SoulSear image fit three products. The Calm Collar image shows an
    adult while the copy says "children ages four and up". `Product` is
    registered in the Django admin, which would have let uploads skip
    validation.
  - Marketing follow-ups are listed in `HANDOFF.md`.
  - The session started with `/clear`.

## 2026-09-24 — Coupon form: products as category-grouped checkboxes; accounts import cleanup

### Prompts
1. `/grill-me` I worked with you to add a new coupon feature. Everything
   looks to be working, but when I log in as admin or employee, and then go
   to back office and then coupons, when I edit or go to add a new coupon,
   everything looks correct except for the "Products" section. All
   products look jumbled together and are not organized. I want these
   organized and not jumbled together. When on applies to, I would like
   all products listed but neatly. When on applies to and I select
   product, I would like to be able to see all products neatly, but have
   the optioon to choose a product that the coupon applies to.
2. (Grill-me answer — picker style) Checkboxes by category (Recommended)
3. (Grill-me answer — "Whole order" behavior) Visible, dimmed (Recommended)
4. (Grill-me answer — unavailable products) Show, with a badge
   (Recommended)
5. (Grill-me answer — scope) Coupons only (Recommended)
6. yes, go ahead and build it
7. yes, clean up the duplicate imports too
8. Please write our entire  session log from today  with the standard
   prompt in the PROMPTS.md.

### Summary
- **Outcome:** The agent read the code first and found the cause:
  `products` was a `<select multiple>` that `StyledModelForm` styled with
  DaisyUI's single-dropdown `select` class, which crammed every product
  into one box. `CouponForm` now shows `products` as a
  `CheckboxSelectMultiple`. Its queryset is `select_related("category")`,
  sorted by category name and then product name, and a new
  `product_checkboxes_by_category()` method groups the checkboxes. A new
  partial, `templates/coupons/partials/_product_picker.html`, lays out a
  heading per category, one column on phones and two on wider screens, an
  "Unavailable" badge, and a "No products yet" empty state. While "Applies
  to" is Whole order, the list fades and a note appears. That uses
  Tailwind `group-has-[…]` CSS only, with no JavaScript. Save and validate
  rules are unchanged. There are five new tests in
  `coupons/test_backoffice.py`, and the suite went from 238 to 243
  passing. As a follow-up, merge leftovers in `accounts/` were removed: the
  duplicate imports in `models.py` plus stray blank or whitespace-only
  lines in `models.py` and `views.py`. `ruff check .` and
  `ruff format --check .` now pass project-wide. The work is not
  committed yet. The agent asked whether to make one commit or two, and
  that is still unanswered.
- **Deviations:** None. All four grill-me recommendations were taken as
  offered. The agent chose some layout details itself without asking:
  A–Z ordering, responsive columns, and leaving the dimmed checkboxes
  clickable. Prompt 7 accepted the agent's offer to fix the lint errors it
  found. While doing that, the agent also fixed two whitespace-only format
  problems in `accounts/` that the prompt didn't mention, and it reported
  them.
- **Sideways:** `ruff check .` failed on duplicate imports in
  `accounts/models.py`, which were already there before this session. The
  agent reported them rather than fixing them unasked, and they were
  cleaned up in prompt 7. `tailwind build` said "up to date", so the agent
  ran `--force` and checked the compiled CSS for the `group-has` dimming
  rules. The first draft of the "checked when editing" test matched on
  exact HTML attribute order, which breaks easily. The agent rewrote it to
  check the bound checkbox's `tag()` before running it. The agent has not
  looked at the page in a browser. The work was verified only by tests
  and by inspecting the compiled CSS.

## 2026-09-19 — Featured products: field, back-office toggle, and storefront badge

### Prompts
1. Please add an "is_featured" field to Product. It will be a boolean and
   defaults to not-featured, which means that existing products stay
   unfeatured.
2. Yes, please expose is_featured in the back-office product form so it
   can be edited from the UI
3. Please add a "Featured" badge for products where is_featured=True. The
   badge needs to appear wherever the store lists a product, especially on
   the catalog listing card and the product detail page. Please ensure
   both places are updated and display the featured badge.
4. Append a session log to PROMPTS.md at the repo root, under today's
   date, newest entry at the top. Record every prompt I gave you this
   session, in order, including any corrections. End the entry with a
   short summary: the outcome, any places where I deviated from a
   recommended answer or asked follow-up questions, and anything that went
   sideways.

### Summary
- **Outcome:** `Product.is_featured` (`BooleanField(default=False)`) with
  migration `products/0003_product_is_featured.py`; the field added to
  `ProductForm.Meta.fields`, where the existing `StyledModelForm` renders
  it as a DaisyUI toggle with no template change; a `badge-secondary`
  "Featured" badge on the catalog card (covering category pages and
  search, which share the template), the product detail page, and the
  back-office product table. Four new tests (feature via the form, badge
  on catalog and detail, badge in the back-office list). Suite went from
  164 to 168 passing; ruff clean throughout.
- **Deviations:** Prompt 2 was a follow-up taking up the agent's offer to
  expose the field in the form (the seed data half of that offer was not
  taken up, so no seeded product is featured). In prompt 3 the agent
  extended "wherever the store lists a product" to the back-office table
  as well as the two named storefront pages, since that table already
  carries a status-badge column.
- **Sideways:** Nothing. Each step was migrated, tested, and linted before
  reporting; no wrong turns.

