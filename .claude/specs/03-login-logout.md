# Spec: Login and Logout

## Overview
Turn the static `/login` page into a working sign-in flow and implement `/logout`. A visitor submits email and password; the app verifies them against the werkzeug hash stored in `users`, starts a Flask session, and redirects to the dashboard. Logout clears the session and returns the visitor to the landing page. This is Step 3 of the Spendly roadmap and introduces the app's first session handling, which every later logged-in feature (profile, expenses) depends on.

## Depends on
- Step 1 — Database setup (`get_db()`, `users` table).
- Step 2 — Registration (`get_user_by_email()`, users with hashed passwords, redirect to `/login`).

## Routes
- `GET /login` — render the sign-in form; if already logged in, redirect to `dashboard` — public
- `POST /login` — validate credentials, set `session["user_id"]`, redirect to `dashboard` on success or re-render the form with an error (HTTP 400 for missing fields, 401 for bad credentials) — public
- `GET /logout` — clear the session and redirect to `landing` — logged-in (harmless if called while logged out; still redirects to `landing`)

`/dashboard` is not protected in this step (it still shows sample data); protecting routes and per-user data belongs to later steps.

## Database changes
No database changes. Existing `users` table is sufficient, and `get_user_by_email(email)` from Step 2 is reused. No new db helpers are required.

## Templates
- **Create:** none
- **Modify:**
  - `templates/login.html` — replace hardcoded `action="/login"` with `action="{{ url_for('login') }}"`; re-populate the `email` input from the submitted value on error (never re-populate the password).
  - `templates/base.html` — navbar shows "Sign out" (`url_for('logout')`) instead of "Sign in" / "Get started" when a user is logged in; otherwise unchanged. Use a template-visible flag (e.g. `session.get("user_id")` or a context processor value) rather than DB logic in the template.

## Files to change
- `app.py` — set `app.secret_key`; change `login` to accept `GET` and `POST`; implement `logout`; import `abort`/`session` as needed.
- `templates/login.html` — `url_for` action and email re-population.
- `templates/base.html` — conditional navbar links.
- `CLAUDE.md` — update route table: `/login` implemented (POST), `/logout` implemented.

## Files to create
- None (spec only: `.claude/specs/03-login-logout.md`).

## New dependencies
No new dependencies. Uses Flask's built-in `session` and `werkzeug.security.check_password_hash` (already installed).

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug — verify with `check_password_hash`; never compare or log plaintext
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- DB logic lives in `database/db.py`, not in `app.py`; reuse `get_user_by_email()`
- Use `url_for()` for every internal link and redirect — no hardcoded URLs
- Route functions do one thing: read form, call helpers, render or redirect
- Email is trimmed and lowercased before lookup (matches registration)
- Use one generic error for unknown email and wrong password (e.g. "Invalid email or password.") so account existence is not leaked
- The secret key must come from an environment variable (e.g. `SPENDLY_SECRET_KEY`) with a clearly dev-only fallback; do not commit a real secret
- Store only `user_id` in the session; on login, call `session.clear()` first
- Do not implement any other stub route (`/profile`, `/expenses/*`)
- No flash messages, no "remember me", no password reset
- Do not add new page-specific inline `<style>` tags
- Keep the app on port 5001

## Definition of done
- [ ] `GET /login` renders the form and its action uses `url_for('login')`.
- [ ] Logging in with `demo@spendly.com` / `demo123` redirects (302) to `/dashboard` and sets a session cookie.
- [ ] Email matching is case-insensitive: `Demo@Spendly.com` with the correct password logs in.
- [ ] A wrong password shows "Invalid email or password." with status 401, and no session is set.
- [ ] An unknown email shows the same message as a wrong password.
- [ ] Empty email or password shows an error and no session is set.
- [ ] On error, the email is pre-filled and the password field is empty.
- [ ] A user registered via `/register` can log in with the same credentials.
- [ ] While logged in, the navbar shows "Sign out" and hides "Sign in" / "Get started"; while logged out it shows the original links.
- [ ] Visiting `/login` while logged in redirects to `/dashboard`.
- [ ] `GET /logout` clears the session, redirects (302) to `/`, and the navbar shows "Sign in" again.
- [ ] `/logout` while logged out redirects to `/` without error.
- [ ] No plaintext password appears in the DB, logs, or session.
- [ ] The app starts on port 5001 with no errors and `/`, `/register`, `/dashboard` still load.
