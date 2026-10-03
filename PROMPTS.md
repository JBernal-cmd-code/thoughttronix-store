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

