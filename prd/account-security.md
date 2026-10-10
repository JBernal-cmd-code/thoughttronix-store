# PRD: The ThoughtTronix Store — Account Security Center

*Commissioned by ThoughtTronix Product Management. "Your Thoughts, Our Business."*

---

## Problem Statement

Today a ThoughtTronix customer can do three things with an account: sign up, sign in, and sign out. Signup asks only for a username and a password, so the store doesn't know how to reach anyone. Once signed in, the only account page is the address book.

So a customer who forgets their password is locked out for good. Their order history, saved addresses, and everything else on the account are gone, and nobody can help them get back in on their own. A customer who suspects someone else is using their password can't change it either, and can't see whether anyone else has signed in.

## Solution

An **Account Security Center**: one place where a signed-in customer manages how their account is protected. It comes with a self-service way back in for anyone who forgot their password.

- **Email at signup.** Every new account gives an email address, and each email belongs to exactly one account.
- **Forgot password.** From the sign-in page, a customer enters their email and gets a time-limited, single-use link to set a new password. The email also reminds them of their username.
- **Change password.** A signed-in customer changes their password by confirming the current one. Their other devices are signed out.
- **Change email.** A signed-in customer moves their account to a new email by confirming their password. The old address is notified.
- **Recent security activity.** The Security Center lists the account's recent sign-ins, failed sign-in attempts, and password and email changes, each with the time, IP address, and device, so a customer can spot activity that wasn't theirs.

Staff get the same Security Center, but no email reset. Their recovery stays with the admin.

## User Stories

**Visitor signing up**

1. As a visitor, I want to give my email address when I sign up, so that I can recover my account if I forget my password.
2. As a visitor, I want signup to refuse an email that's already registered and offer me a "Forgot your password?" link, so that I recover my existing account instead of creating a duplicate.
3. As a visitor, I want the store to treat `Casey@Example.com` and `casey@example.com` as the same address, so that capitalization can't create a duplicate account or make my email unrecognizable.

**Customer who forgot their password**

4. As a customer who forgot my password, I want a "Forgot your password?" link on the sign-in page, so that I can start recovery without contacting anyone.
5. As a customer, I want to request a reset link by entering my email, so that I don't need to remember my username to recover my account.
6. As a customer, I want the confirmation page to show the email I typed, with a hint to check the spelling, so that I can spot a typo if no email arrives.
7. As a customer, I want the confirmation page to say the same thing whether or not my email is registered, so that strangers can't use it to find out who shops at ThoughtTronix.
8. As a customer, I want the reset email to include my username, so that I can sign in even if I forgot my username too.
9. As a customer, I want the reset link to expire after one hour and stop working once used, so that an old or forwarded email can't be used to take over my account.
10. As a customer, I want to be sent to the sign-in page with a success message after setting a new password, so that I confirm the new password works by using it.
11. As a customer, I want resetting my password to sign out every device that was signed in to my account, so that anyone who had my old password loses access.

**Signed-in customer: Security Center**

12. As a signed-in customer, I want a "Security" link in the navigation, so that I can find my account security settings from any page.
13. As a signed-in customer, I want a Security Center page showing my username, my email, and links to change my password and email, so that I can see and manage my account protection in one place.
14. As a signed-in customer, I want to change my password by giving my current password and the new one twice, so that someone at my unlocked computer can't change it.
15. As a signed-in customer, I want to stay signed in on this device after changing my password, while my other devices are signed out, so that changing my password doesn't interrupt me but does lock out anyone else.
16. As a signed-in customer, I want to change my account email by entering my current password and the new email twice, so that I can move to a new inbox without contacting support and without a typo locking me out.
17. As a signed-in customer, I want a new email that's already used by another account to be refused, so that every email stays tied to one account.
18. As a customer, I want an email notice sent to my old address when my account email changes, so that I find out if someone else changed it.
19. As a customer, I want an email notice whenever my password is changed or reset, so that I find out right away if someone else did it.

**Signed-in customer: security activity**

20. As a signed-in customer, I want to see my 10 most recent security events on the Security Center, so that I can check for activity that wasn't mine.
21. As a signed-in customer, I want to see successful sign-ins in that list, so that I notice a sign-in I didn't make.
22. As a signed-in customer, I want to see failed sign-in attempts on my username, so that I know if someone is guessing my password.
23. As a signed-in customer, I want password changes, password resets, and email changes in that list, so that I have a record of every change to how my account is protected.
24. As a signed-in customer, I want each event to show when it happened, the IP address, and a readable device description such as "Firefox on Windows," so that I can tell my own activity from someone else's.
25. As a customer, I want security events older than 90 days to be deleted, so that the store doesn't keep my IP addresses forever.

**Staff and admin**

26. As an employee, I want the same Security Center as customers, including changing my password and email and seeing my activity, so that I can look after my own account.
27. As an employee, I want the forgot-password form to never send a reset link for my account, so that someone who gets into my inbox can't take over the back office.
28. As an employee who forgot my password, I want the admin to be able to reset it for me, so that I still have a way back in.
29. As the admin, I want to view every user's security events in Django admin, filtered by user and event type, so that I can investigate a customer's "someone got into my account" report.
30. As the admin, I want security events to be read-only in Django admin, so that the activity log can be trusted as an audit record.
31. As the admin who forgot my own password, I want to reset it from the command line on the server, so that the top-level account always has a way back in.

**Grader / reviewer**

32. As a reviewer, I want the seeded `customer` account to already have a short, realistic security history, including one suspicious failed sign-in from an unfamiliar IP, so that I can see the activity log working right after seeding.

## Implementation Decisions

**Scope and app boundaries**

- All of this feature lives in the `accounts` app. `accounts` still imports from no other local app.
- Django's built-in authentication views and forms are reused wherever possible: password reset (request, done, confirm, complete), password change, and their token generator. They're subclassed or configured for this project's templates, styling, and behavior instead of being rebuilt. No third-party auth packages are added.

**User email**

- The user's email becomes required and unique: a unique constraint on the existing email column, applied by migration. The existing database and the seed data were checked: every user has an email and none are duplicates, so the migration needs no data cleanup.
- Emails are normalized to lowercase whenever they're saved (signup, change email). Lookups such as the reset request lowercase the input before matching. Because everything is stored lowercase, a plain unique constraint is enough and no case-insensitive comparison is needed anywhere else.
- Usernames stay the sign-in identifier. Login doesn't change.

**Signup**

- The signup form adds a required email field. Its existing "ask for the minimum" docstring is updated to explain why email is now part of that minimum.
- A duplicate email gets a field error that the email is already in use, and the template shows a link to the forgot-password page next to it.

**Password reset**

- The sign-in page links to a forgot-password page.
- The reset request form only matches accounts that are **active, not staff, and have a usable password**, extending Django's own active and usable-password filter. Staff accounts never get a reset email, and the page still shows the same response, so nothing reveals that the account is staff.
- After the request, every user sees the same "If an account exists for that email…" page. It shows the submitted address unmasked and suggests checking the spelling. The address goes from the request view to the done page through the session, not the URL, so it doesn't end up in browser history or server logs.
- The reset email is plain text and includes the username.
- `PASSWORD_RESET_TIMEOUT` is set to one hour. Links are single-use by Django's design, since the token covers the password hash and last-login time.
- After a reset the user is **not** signed in automatically. They go to the sign-in page with a success message, which matches how signup works today.
- Because the session auth hash is built on the password, a reset invalidates every existing session for that user.

**Change password**

- Uses Django's password change form: current password, new password twice, the project's password validators.
- The current session is kept (its auth hash is updated). All other sessions become invalid.
- On success: a "password changed" event is recorded, a notice email goes to the account email, and the user returns to the Security Center with a success message.

**Change email**

- A new form asks for the new email, the new email again, and the current password. It checks that the two emails match, that the password is right, that the email is unique (lowercased), and that it's different from the current email.
- The change takes effect immediately. The new address is **not** confirmed by a link.
- On success: an "email changed" event is recorded, a notice goes to the **old** address saying the email changed and to contact the store if it wasn't them, and the user returns to the Security Center with a success message.
- The duplicate-email error uses the same "already in use" wording as signup, without the forgot-password link.

**Notification emails**

- All emails (reset link, password changed, email changed) are plain-text templates sent through the existing console email backend. No real mail is sent.
- A password-changed notice is sent for both a signed-in change and a completed reset.

**Security Center pages and URLs**

- A hub page under the accounts URL namespace shows the username, the current email, links to Change password and Change email, and the recent activity list.
- Change password and Change email each have their own form page that returns to the hub on success. This follows the same list-page-plus-form-pages pattern as the address book.
- All Security Center pages require sign-in (anonymous visitors go to login). They're for any signed-in user, staff included, and always act on the signed-in user, never on an id from the URL.
- The signed-in nav gets a "Security" link next to "Addresses."
- Views stay thin: form logic lives in the forms, and event recording and pruning live on the model's manager.

**Security events model**

- A new `SecurityEvent` model: the user it belongs to, an event type, a timestamp, the IP address, and the raw User-Agent string. It's ordered newest first.
- The event types are: signed in, failed sign-in, password changed, password reset, email changed. Signed out and reset requested are left out on purpose.
- One manager method records an event from a user, an event type, and the request (pulling the IP and User-Agent from the request). After writing, it deletes that user's events older than 90 days, so retention takes care of itself with no scheduled job.
- The IP comes from the request's remote address. Behind a reverse proxy that would be the proxy's address, which is noted as a deployment concern and not handled now.
- A small helper with no external dependency turns the User-Agent into a short "Browser on OS" label for display. It only needs to recognize common browsers and operating systems and falls back to a generic label otherwise.

**Event sources**

- Signed in: Django's `user_logged_in` signal.
- Failed sign-in: Django's `user_login_failed` signal. That signal carries only the typed credentials, so the event is recorded only when the typed username belongs to an existing user. Attempts against usernames that don't exist are not recorded.
- Password changed, password reset, email changed: recorded by the corresponding views on success.
- The hub shows the user's 10 most recent events.

**Django admin**

- `SecurityEvent` is registered in admin with a list showing user, event type, time, IP address, and device, with filters by event type and searching by username.
- Add, change, and delete permissions are all blocked, so the log is read-only for everyone.

**Seed data**

- The `seed` command gives the `customer` demo user about 5–6 security events spread over the past few weeks: several sign-ins on different devices, a password change, and one failed sign-in from an unfamiliar IP.
- Timestamps are computed relative to the moment of seeding, so the 90-day pruning never removes them.
- Seeded IP addresses come from the reserved documentation ranges (`203.0.113.0/24`, `198.51.100.0/24`), so they're clearly fake.

## Out of Scope

- Signing in with an email address. Username stays the only sign-in identifier.
- Confirming a new email by a link before an email change takes effect.
- Confirming the email address at signup, and "pending" or unactivated accounts.
- Removing the email-enumeration leak at signup and change email (see Further Notes).
- Sign-in throttling or lockout after repeated failed attempts.
- A "sign out of all other devices" button, and any list of active sessions. Changing or resetting the password signs out other devices as a side effect.
- Two-factor authentication of any kind.
- A "forgot username" flow separate from the password reset email.
- Email reset for staff or admin accounts.
- A back-office (non-admin) page for staff to view customers' security activity.
- Logging sign-outs or reset requests.
- A full or paginated activity history beyond the 10 most recent events.
- Real email delivery (SMTP or a provider). The console backend stays.
- Handling forwarded-for headers to find a client IP behind a proxy.
- Changing usernames, deleting accounts, or editing other profile fields.

## Further Notes

- **Known, accepted enumeration leak.** The forgot-password page reveals nothing about which emails are registered, but signup and change email do: they have to refuse a duplicate email, and the error says so. The leak was accepted on purpose. The only leak-free alternative is email activation at signup, which is a much bigger change. This PRD records it so nobody assumes the whole system is enumeration-proof.
- **Staff recovery path.** A locked-out employee is recovered by the admin through Django admin's password change. A locked-out admin recovers with the `changepassword` management command on the server.
- **Personal data.** Security events store IP addresses and User-Agent strings. They're shown only to the account owner and to admin users, and kept for at most 90 days, pruned whenever a newer event is written for that user. An inactive account may keep older events until its next recorded event.
- **The app must still run with no `.env`.** The reset timeout is a fixed setting with a default, and no new environment variables are required.
