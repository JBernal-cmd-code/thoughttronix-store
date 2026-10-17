# PRD: The ThoughtTronix Store — Product Reviews

*Commissioned by ThoughtTronix Product Management. "Your Thoughts, Our Business."*

---

## Problem Statement

A ThoughtTronix shopper deciding whether to buy a product has only the store's own word to go on: the tagline, the description, and the price. They can't see what other customers thought, and customers who bought something have nowhere to tell anyone how it went.

Reviews from just anyone wouldn't fix that. A review is only worth reading if the person writing it actually bought the product. Ownership matters at this store: a SoulSear's owner has an opinion worth hearing, but their next of kin, however strongly they feel, never bought one. Eligibility has to belong to the account that placed the order.

## Solution

**Product reviews** on every product detail page, written only by customers who bought the product.

- **Verified purchasers only.** A signed-in customer can review a product if their own account has an order for it that wasn't cancelled. Each customer can leave one review per product.
- **Stars and words.** A review is a whole-star rating from 1 to 5 plus a required written comment.
- **A reviews section on the product page.** It shows the average rating and the review count. Next comes the customer's own review, or the form for writing one, pinned in a fixed spot. Then everyone else's reviews follow, newest first.
- **Everything in place.** Writing, editing, and deleting a review update the reviews section without reloading the page, so the customer never loses their place.
- **Owners manage their own; staff manage any.** Customers can edit and delete only their own reviews. Staff can edit and delete any review, right on the product page. A review a staff member has changed is marked "Edited by staff," so shoppers know the words aren't entirely the customer's.
- **Friendly when you can't review.** Signed-out visitors are invited to sign in. Signed-in customers who haven't bought the product are told why there's no form.

## User Stories

**Shopper reading reviews**

1. As a shopper, I want a reviews section on each product's detail page, so that I can learn what buyers thought before I buy.
2. As a shopper, I want to see the product's average star rating and how many reviews it has, so that I can judge it at a glance.
3. As a shopper, I want reviews listed newest first, so that I read the most current opinions first.
4. As a shopper, I want each review to show its star rating, comment, author, and date, so that I can weigh each one.
5. As a shopper, I want reviewers shown by first name and last initial, so that reviews feel personal without exposing anyone's identity.
6. As a shopper, I want every review to come from someone who actually bought the product, so that I can trust what I read.
7. As a shopper, I want reviews a staff member changed to say "Edited by staff," so that I know when the words aren't entirely the customer's.
8. As a shopper, I want a friendly empty state on products nobody has reviewed yet, so that the section doesn't look broken.

**Visitor and ineligible customer**

9. As a visitor who isn't signed in, I want a "Sign in to write a review" link where the form would be, so that I learn I can review after signing in.
10. As a visitor, I want signing in to return me to the product I was on, so that I can write my review right away.
11. As a signed-in customer who hasn't bought a product, I want a short note explaining that only purchasers can review it, so that I understand why there's no form.

**Customer writing a review**

12. As a customer who bought a product, I want a review form on its page, so that I can share my experience.
13. As a customer, I want to pick a whole-star rating from 1 to 5, so that my overall opinion is clear.
14. As a customer, I want to write a comment of up to 2,000 characters, so that I can explain my rating.
15. As a customer, I want a review with no comment, or only spaces, to be refused with a clear error, so that every review says something.
16. As a customer, I want validation errors to appear in the form without losing what I typed, so that I can fix the problem and resubmit.
17. As a customer, I want my new review to appear in place, with the summary updated, without the page reloading, so that I don't lose my place.
18. As a customer, I want my own review pinned at the top of the reviews section, so that I can always find it.
19. As a customer, I want to be able to review a product I bought even if it's now unavailable, so that my experience still counts.
20. As a customer, I want my order counting as a purchase as soon as I place it, so that I don't have to wait for delivery to review.
21. As a customer, I want a cancelled order not to count as a purchase, so that eligibility reflects what I actually bought.
22. As a customer, I want only one review per product, so that my opinion is counted once.
23. As a customer who already reviewed a product, I want a second submission (from a stale tab or a double click) to show my existing review with a message saying I've already reviewed it, so that I'm not confused and nothing is duplicated.

**Customer managing their review**

24. As a customer, I want an Edit button on my review that turns it into a form in place, so that I can change my rating or comment without leaving the page.
25. As a customer, I want a Cancel button while editing that puts my review back unchanged, so that I can back out safely.
26. As a customer, I want saving an edit to update my review and the summary in place, so that the page stays where I was.
27. As a customer, I want a Delete button that asks me to confirm first, so that I don't delete my review by accident.
28. As a customer, I want deleting my review to remove it in place and show the form again, so that I can write a new one later if I want.
29. As a customer, I want to keep my review, and keep being able to edit or delete it, even if my order is cancelled later, so that my words aren't removed without warning.
30. As a customer, I want my reviews deleted along with my account, so that nothing I wrote remains after I leave.

**Security**

31. As a customer, I want no one but me and staff to be able to edit or delete my review, by any request, so that my words can't be tampered with.
32. As a customer, I want every review action to require me to be signed in, checked on the server, so that hand-crafted requests get nowhere.
33. As a customer whose session expired, I want clicking a review button to take me to the sign-in page, rather than showing the sign-in page squeezed inside a review card, so that the page doesn't break.
34. As the store, I want a create request from someone who hasn't bought the product refused, so that the purchase rule can't be bypassed.
35. As the store, I want the database itself to refuse a second review by the same customer on the same product, so that the one-review rule holds even in a race.

**Staff**

36. As a staff member, I want Edit and Delete on every review on the product page, so that I can moderate where reviews are shown.
37. As a staff member, I want editing someone else's review to mark it "Edited by staff," and the author's later edits not to remove that mark, so that moderation is always transparent.
38. As a staff member, I want to write reviews for products my own account has bought, under the same rule as everyone else, so that staff are treated like any customer when they shop.
39. As a staff member, I want deleting a review to be an ordinary delete, so that moderation stays simple.

**Admin**

40. As the admin, I want reviews listed in Django admin, filterable by rating and searchable by product or username, so that I can see every review across the store in one place.
41. As the admin, I want to be able to delete reviews from Django admin, so that I can remove problems from the overview.
42. As the admin, I want adding and changing reviews blocked in Django admin, superusers included, so that the admin can't become a way around the purchase rule or the "Edited by staff" mark.

**Demo and review**

43. As a developer or reviewer, I want the seed to include several realistic reviews written by background customers who really bought those products, so that the summary, the list, and the averages show right after seeding.
44. As a developer or reviewer, I want the demo `customer` to have one review already and some purchases not yet reviewed, so that I can try creating, editing, and deleting right away.
45. As a developer or reviewer, I want one seeded review to carry the "Edited by staff" mark and some products to have no reviews, so that the badge and the empty state are visible.
46. As a developer or reviewer, I want the seed to obey the purchase rule, proved by a test, so that the demo is never a quiet exception to it.

## Implementation Decisions

**A new `reviews` app**

- Reviews live in their own app with their own URL namespace (`reviews:`) and template directory.
- Dependency rule: `reviews` imports from `products` and `orders` (and may import from `accounts`, like every app). Nothing imports from `reviews`, except the `seed` command, which already builds the whole demo world. The product detail view reads reviews through the product's reverse relation, never the review model, the same way it reads the wishlist.

**Model: `Review`**

- Fields: the user (deleted with the user), the product (deleted with the product), a rating, a comment, an `edited_by_staff` boolean (default false), and `created_at`.
- `rating` is a small positive integer, validated to whole numbers from 1 to 5.
- `comment` is required, at most 2,000 characters. A comment that's only spaces is treated as empty and refused.
- `created_at` is a default rather than auto-set, so `seed` can backdate it. There is no `updated_at`, and no general "edited" note.
- A unique constraint on (user, product) guarantees one review per customer per product at the database level.
- Ordered newest first.
- Model methods hold the logic, so views stay thin:
  - **Eligibility:** whether a user may review a product. True when the user's own account has at least one order containing that product whose status isn't Cancelled (Placed, Shipped, and Delivered all count). The order's account (`Order.user`) decides it, not any name on the order. Eligibility is checked **only when a review is created**. Later cancellations don't remove or hide existing reviews, and authors keep edit and delete rights. Product availability doesn't matter.
  - **`can_be_changed_by(user)`:** true for the review's author and for any staff member. It's the single permission rule for editing and deleting.
  - **Editing:** an edit method that takes the editor along with the new rating and comment. When the editor is staff and isn't the author, it sets `edited_by_staff`. Nothing ever clears it, including the author's later edits.
  - **`author_name`:** the author's first name and last initial ("Jordan P."), falling back to "Verified buyer" when the first name is blank. It never shows the username or email. It belongs on `Review`, not `User`, so `accounts` stays unaware of reviews.
- Staff follow the same eligibility rule as everyone else: checkout is open to any signed-in user, so a staff member can review what their own account bought.
- No service module is planned. Eligibility reads orders, but the logic is a query, not a multi-model workflow.

**Views and URLs**

Every review endpoint requires sign-in, enforced on the server, and that includes the GET endpoints for the edit form and cancel. Signed-out requests go to login. For HTMX requests from a signed-out user, the response carries an `HX-Redirect` to login, so the whole browser navigates there instead of swapping the login page into the reviews section.

- **Create**: POST, takes a product pk (a missing product is a 404).
  - Not eligible: 403.
  - Already reviewed: the reviews section re-renders showing the existing review, with an alert telling the customer they've already reviewed the product and can edit it below. This also covers a simultaneous duplicate, where the unique constraint raises an integrity error that the view catches and answers the same way.
  - Invalid: the form re-renders in place with errors and the typed input kept.
  - Valid: the review is saved and the whole reviews section re-renders.
- **Edit form**: GET, takes a review pk. It returns the edit-form partial for that one review card.
- **Cancel edit**: GET, takes a review pk. It returns the review card partial unchanged.
- **Save edit**: POST, takes a review pk. Invalid input re-renders the edit form in place with errors. Valid input saves through the edit method (which handles the staff flag) and re-renders the whole reviews section.
- **Delete**: POST, takes a review pk. It deletes the review and re-renders the whole reviews section.
- Every endpoint that takes a review pk (edit form, cancel, save, delete) checks `can_be_changed_by` on the server. Any other user gets a **404**, so the response doesn't reveal that the review exists.
- The product detail view adds the reviews section's context: the average rating and count, the requester's own review (if any), whether the requester may review, and everyone else's reviews.
- No pagination: all reviews render.

**HTMX and templates**

- The reviews section is one partial with a stable wrapper id, placed on the product detail page below the product details. In order, it contains:
  1. **Summary:** the average stars and the review count, or the designed empty state when there are no reviews.
  2. **Pinned slot:** one of four states.
     - **Signed out:** a "Sign in to write a review" link to login with `next` set to the product page. No HTMX.
     - **Signed in, not eligible:** a short note that only customers who've purchased the product can review it.
     - **Eligible, no review yet:** the create form.
     - **Already reviewed:** the customer's own review card, with Edit and Delete.
  3. **Everyone else's reviews**, newest first, excluding the requester's own.
- Separate partials for a single **review card** and a single **edit form**. Edit and Cancel swap only that card (`outerHTML`). Create, save, and delete swap the whole section, so the summary always stays correct.
- Edit and Delete buttons render only for users `can_be_changed_by` allows: the author on their own review, and staff on every review. The server checks again regardless.
- Delete asks for confirmation with `hx-confirm`, the browser's built-in confirm, so it needs no custom JavaScript.
- A review card shows the stars, the comment, `author_name`, the date, and an "Edited by staff" badge when `edited_by_staff` is set.
- The star input is five DaisyUI `rating` radio inputs, with no JavaScript beyond HTMX.
- Partials follow the frontend conventions: in the app's `partials/` directory, underscore-prefixed, never extending the base template. They use DaisyUI classes, existing badge and alert patterns, `{% url %}` links, and no inline styles.
- Ratings appear only on the product detail page.

**Admin**

- A `ReviewAdmin` lists reviews with author, product, rating, date, and the staff-edited flag. It filters by rating and searches by product name and username.
- Add and change are blocked for everyone, superusers included, the same way the security event admin is locked down. Delete is allowed.

**Seed**

- A handwritten list of reviews, in the store's voice, for a handful of products, several reviews each.
- Each seeded review is assigned deterministically to a background customer who has a non-cancelled order for that product, so every seeded review satisfies the purchase rule.
- The demo `customer` gets exactly one review on a product they bought, and keeps other purchases unreviewed so the create form shows.
- One background review has `edited_by_staff` set. Some products have no reviews, so the empty state shows.
- `created_at` values are backdated relative to the run.
- The wipe needs no extra step: reviews cascade with their products and users. The seed summary line reports the review count.

**Docs**

- `docs/ARCHITECTURE.md`: the new app, its dependency rule, the per-app rules (eligibility, check-once, the staff flag, the display name, the admin lockdown), and the extended seed exception.
- `docs/VIEWS.md`: the review routes, the access rules (sign-in on every endpoint, 404 for others' reviews, 403 for ineligible creates), and the swap rules.
- `docs/FRONTEND.md`: the reviews section, its pinned-slot states, and the partials.
- The root `CLAUDE.md` project layout gains the `reviews/` app. `PROMPTS.md` gets an appended entry.

**Testing**

- Tests live in the `reviews` app and use plain fixtures from the project `conftest.py`, never seed data. Every test user has a distinct email.
- Eligibility:
  - Placed, Shipped, and Delivered orders qualify, and Cancelled doesn't.
  - Another account's order for the same product doesn't qualify.
  - Unavailable products qualify.
  - A later cancellation leaves the review and its edit and delete rights intact.
- Model:
  - The rating bounds of 1 and 5 are enforced.
  - The comment is required, a comment of only spaces is refused, and the 2,000-character limit holds.
  - The unique constraint refuses a duplicate.
  - `author_name` and its fallback.
  - `can_be_changed_by` for the author, staff, and other customers.
  - The staff edit sets the flag, and the author's later edit doesn't clear it.
- Access:
  - A signed-out request to every endpoint, including the GETs, goes to login, and an HTMX signed-out request gets `HX-Redirect`.
  - Another customer's edit form, cancel, save, and delete return 404 and change nothing.
  - An ineligible create returns 403.
  - Staff can edit and delete any review.
- Duplicates: a second create re-renders with the existing review and the alert, and creates nothing.
- Responses:
  - Create, save, and delete return the section partial (not the full page) with an updated summary.
  - Edit and cancel return the card or form partial.
  - Invalid input re-renders the form with errors and keeps the typed values.
- Page: each pinned-slot state, newest-first order, the requester's own review excluded from the list, the empty state, and the "Edited by staff" badge.
- Cascade: deleting a product or user deletes their reviews.
- Admin: add and change are refused, the list renders, and delete works.
- Seed: every seeded review is eligible, `customer` has exactly one review and at least one unreviewed purchase, one review is staff-edited, and at least one product has no reviews.
- The style guard covers the new templates automatically.

## Out of Scope

- Ratings, averages, or review counts anywhere but the product detail page (catalog cards, category pages, the back office, the dashboard).
- A back-office reviews tab. Moderation happens on the product page, and the overview is Django admin.
- Pagination, sorting, or filtering reviews on the product page.
- Half-star ratings, or ratings without a comment.
- A general "edited" note or edit timestamps, and edit history.
- A "Verified purchase" badge (every review is from a purchaser by definition).
- Blocking a customer from re-reviewing after staff delete their review, soft deletes, or "removed by staff" notices.
- Hiding or removing reviews when their order is later cancelled.
- Review voting ("helpful"), replies, photos, or reporting/flagging reviews.
- Notifications to customers about their reviews being edited or deleted.
- Creating or changing reviews in Django admin.

## Further Notes

- The "already purchased" rule reads the account that owns the order, matching how orders are already scoped to the signed-in user. Shipping and billing names on an order are just text, and give no one eligibility.
- Eligibility is a gate passed once, at creation, on purpose. It keeps the rule in one place and means order status changes in the back office never need to know about reviews.
- The design reuses existing patterns: a unique constraint paired with graceful handling of repeats (cart, wishlist), owner-scoped lookups that 404 for others (wishlist), a locked-down admin (security events), and HTMX partials that swap in place (cart, wishlist, coupon preview).
- Natural follow-ups if ThoughtTronix asks: catalog-card stars (via a reverse-relation annotation, so `products` still never imports `reviews`), a back-office reviews list, and soft-delete moderation with re-review blocking. Each needs its own scope decision.
