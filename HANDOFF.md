# Handoff — Product images

**Next session's job:** implement the product-image design agreed in the
previous session (a `/grill-me` interview). No code has been written yet. The
only change in the working tree is the untracked `product-images/` folder.
The design exists only in this document; no plan file was written.

Read `CLAUDE.md` first, then the docs it says to read before each kind of
change: `docs/ARCHITECTURE.md`, `docs/VIEWS.md`, `docs/FRONTEND.md`, and
`docs/TESTING.md`. The core platform's history is in `prd/core-platform.md`,
which says "no media handling in the core… this arrives later", and in
`plans/core-platform.md`.

## Goal (user's requirements)

- Every product shows its uploaded image or the existing category
  placeholder, with no broken images.
- Images look consistent across the catalog, and pages stay fast.
- Employees upload through the back office. An unusable file is rejected with
  a plain-language explanation, never accepted and lost.
- `product-images/` is a temporary holding spot, not Django's media dir.

## Starting state (verified)

- No `ImageField`, no `MEDIA_*` settings, and no Pillow in `pyproject.toml`.
- Placeholders are 400×300 (4:3) SVGs in `assets/images/placeholders/`,
  chosen by `Category.placeholder_image` (`products/models.py:32`). They're
  used only at `templates/products/catalog.html:64` and
  `templates/products/detail.html:17`.
- `ProductForm` is in `products/forms.py`. Its `StyledModelForm` loop assigns
  DaisyUI classes by widget type, so a file widget would currently get
  `input w-full`. DaisyUI has `file-input`.
- `Product` is registered in the Django admin (`products/admin.py:20`) with no
  `fields` list, so it would expose a new image field automatically.
- `seed` (`products/management/commands/seed.py`) is destructive. `_wipe()`
  bulk-deletes with `Product.objects.all().delete()`, which bypasses
  `Model.delete()`; `post_delete` signals still fire. `handle()` is
  `@transaction.atomic`.
- `OrderItem.product` uses `SET_NULL`, so products can be deleted.

## Agreed decisions

1. **Seed assets.** Marketing's images become committed seed assets. `seed`
   attaches them through the same processing function employees' uploads go
   through, so the full catalog with images comes back on every reseed.
2. **Frame.** 4:5 portrait everywhere. Odd shapes are center-cropped to fill
   the frame, never letterboxed. **Redraw all 7 placeholder SVGs at 4:5**,
   keeping their current look.
3. **Processing.** Each image is processed once, at upload: Pillow
   center-crops to 4:5, resizes to **800×1000**, and saves **WebP** (quality
   about 80). Only the processed file is stored.
4. **Rejection rules.** Each failure gets its own plain-language message.
   - The file must decode with Pillow. Checking the extension alone isn't
     enough.
   - Allowed formats are JPEG, PNG, and WebP. SVG, HEIC, and GIF are
     rejected; HEIC gets an "export as JPEG" hint.
   - The file must be 10 MB or smaller.
   - The image must be **at least 800×1000 after the 4:5 crop**. The message
     states the actual size and the minimum.
5. **No broken images.** A `Product.image_url` property returns the upload's
   URL only if the file **exists in storage**, and the category placeholder's
   static URL otherwise. Both templates call it. It replaces the direct
   `category.placeholder_image` usage.
6. **File lifecycle.** Delete the old file when the image is replaced,
   cleared, or its product is deleted, including during `seed`'s bulk wipe.
   Delete only **after commit** (`transaction.on_commit`). Every upload gets a
   unique filename (e.g. `products/<slug>-<random>.webp`) so browsers don't
   keep a cached old image. The form offers Replace plus a Clear checkbox,
   which reverts the product to its placeholder, and shows the current image.
7. **Text-baked images ship as-is for now**: Seraphine, Veil, MindSync Duo,
   and RecallPro. They'll be swapped when Marketing supplies no-text versions.
   The user said placeholders tested poorly and wants every Marketing image
   showing.
8. **SoulSear image goes on SoulSear Mark II.** Mark I and Tactical Core keep
   placeholders.
9. **Calm Collar uses its adult-model image** even though the copy says
   "children ages four and up". The mismatch is flagged to Marketing.
10. **Where images appear:** the catalog grid, the product detail page, the
    back-office product form, and a **new thumbnail column in the back-office
    product list**. Not the cart, order history, or receipts; those are
    deferred.
11. **Seed source files.** Convert the chosen originals to **quality-90 JPEG
    at full original resolution** (about 5 MB total instead of about 23 MB of
    PNG). Store them as `products/seed_images/<product-slug>.jpg`, then
    **delete `product-images/`**. Don't pre-shrink them; `seed` must still
    exercise cropping and resizing.
12. **Architecture.** A new module, `products/images.py`, holds one function,
    `prepare_product_image(uploaded_file)`. It validates, crops, resizes, and
    encodes, then returns the processed file or raises `ValidationError`.
    These call it:
    - `ProductForm.clean_image`
    - `ProductAdmin`, which is set to `form = ProductForm`
    - `seed`, which calls it directly

    Add it to `docs/ARCHITECTURE.md` as a third deliberate deep module, with a
    docstring and type hints.

### Seed image mapping (source file → product slug)

| `product-images/` file | slug |
|---|---|
| `Seraphine GPT Text.png` | `seraphine` |
| `Hush GPT No Text.png` | `hush` |
| `MindSync GPT 2.png` | `mindsync` |
| `MindSync Duo.png` | `mindsync-duo` |
| `RecallPro.png` | `recallpro` |
| `MoodSet GPT No Text.png` | `moodset` |
| `DreamWeaver Matrix GPT 3.png` | `dreamweaver` |
| `Veil GPT Text.png` | `veil` |
| `Calm Collar GPT Man.png` | `calm-collar` |
| `SyncRest GPT No Text.png` | `syncrest` |
| `SoulSear No Text.png` | `soulsear-mark-ii` |
| `CrowdCalm Array No Text.png` | `crowdcalm-array` |

`SyncRest GPT Text.png` is **not used**; the user chose the No Text version.
Every mapped image passes the 800×1000-after-crop rule. The tightest is
MindSync Duo (1536×1024), which crops to 819×1024. The other 24 products keep
placeholders.

## Implementation defaults (agreed; no further questions needed)

- **Settings and dependency.** `MEDIA_ROOT = BASE_DIR / "media"` and
  `MEDIA_URL = "media/"`, with no `.env` dependency. Add `media/` to
  `.gitignore`. Serve media through `config/urls.py` only when `DEBUG`
  (`django.conf.urls.static.static`). Add Pillow with `uv add pillow`.
- **Processing details.** Apply `ImageOps.exif_transpose` so phone photos
  aren't sideways. Treat Pillow's `DecompressionBombError`/`Warning` as the
  "can't read this image" rejection. Keep transparency.
- **Templates.**
  - Put `aspect-[4/5] object-cover` on the images.
  - Set `width="800" height="1000"`.
  - Add `loading="lazy"` on the catalog grid and the back-office list.
  - Use the product name as alt text.
  - Give the product form `enctype="multipart/form-data"`, and make the views
    pass `request.FILES`. Generic `CreateView`/`UpdateView` already do this.
  - Follow `docs/FRONTEND.md`'s checklist, which
    `config/test_style_guard.py` enforces.
- **Tests.** Point `MEDIA_ROOT` at a temporary directory for every test that
  uploads (e.g. a fixture using `settings` and `tmp_path`). Cover:
  - each rejection rule and its message
  - crop and resize output (800×1000 WebP)
  - the `image_url` fallback when the field is empty and when the file is
    missing
  - file deletion on replace, clear, and delete, which needs
    `django_capture_on_commit_callbacks` or `transaction=True`
  - the staff upload flow
  - seed attaching 12 images
- **Docs.**
  - Update `docs/ARCHITECTURE.md` (the new module, the products rules).
  - Update `docs/FRONTEND.md` (4:5 placeholders, media, image classes).
  - Update the `CLAUDE.md` layout if `products/seed_images/` warrants it.
- **Known gap, out of scope.** With `DEBUG=False`, nothing serves media (or
  static files; the project has no whitenoise). Note it in docs and don't fix
  it.

## Constraints to remember

- Keep the suite green at every phase boundary (`uv run pytest`). Run
  `uv run ruff check .` and `uv run ruff format .`.
- Never edit `assets/css/tailwind.css`. New Tailwind classes such as
  `aspect-[4/5]` are picked up by `uv run python manage.py tailwind build`.
- After implementing, run `uv run python manage.py seed` and check that the 12
  products show their images and every other product shows a 4:5 placeholder.
- Commit only when the user asks.

## Follow-ups for Marketing (record in the final summary, don't implement)

- No-text versions of Seraphine, Veil, MindSync Duo, and RecallPro.
- Confirm or replace the Calm Collar image (the copy targets children; the
  image shows an adult).
- A second SoulSear image for Mark I.
- Later: cart and order-history thumbnails, if wanted.

## Suggested skills

- **`run`**: launch the dev server after seeding and confirm the catalog,
  detail page, back-office list thumbnails, and upload form in the real app,
  including a rejected upload's error message.
- **`code-review`**: review the diff for correctness before handing back,
  especially the after-commit deletion and the bulk-delete path in `seed`.
- **`simplify`**: a final quality pass on the new `products/images.py` and
  its form and admin wiring.
- **`grill-me`**: only if a new design question comes up that this document
  doesn't settle. Ask the user; don't guess.
