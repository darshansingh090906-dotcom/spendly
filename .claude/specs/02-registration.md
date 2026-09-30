# Spec: Registration

## Overview
Turn the static `/register` page into a working sign-up flow. A visitor submits their name, email and password; the app validates the input, stores a new user with a werkzeug-hashed password in the `users` table, and redirects them to the login page. This is Step 2 of the Spendly roadmap and is the first feature that writes user data; login (Step 3) and everything behind it depend on accounts existing.

## Depends on
- Step 1 — Database setup (`get_db()`, `init_db()`, `users` table with `UNIQUE` email).

## Routes
- `GET /register` — render the registration form — public (already exists, unchanged)
- `POST /register` — validate form, create the user, redirect to `login` on success or re-render the form with an error — public

`GET /login` already exists and is the redirect target. No session or auto-login is added in this step (that belongs to Step 3).

## Database changes
No database changes. The existing `users` table (`id`, `name`, `email UNIQUE NOT NULL`, `password_hash`, `created_at`) is sufficient.

New helper functions in `database/db.py` (DB logic must not live in the route):
- `get_user_by_email(email)` — returns a `sqlite3.Row` or `None`.
- `create_user(name, email, password)` — hashes the password with `generate_password_hash`, inserts the row with a parameterised query, returns the new user id. Raises `sqlite3.IntegrityError` if the email is already taken (the `UNIQUE` constraint is the source of truth; the route catches it to avoid a check-then-insert race).

## Templates
- **Create:** none
- **Modify:** `templates/register.html`
  - Replace the hardcoded `action="/register"` with `action="{{ url_for('register') }}"`.
  - Re-populate `name` and `email` inputs from submitted values on error (never re-populate the password).
  - Keep the existing `{% if error %}` block, which already uses `.auth-error`.

## Files to change
- `app.py` — change `register` to accept `GET` and `POST`; add the POST handler; import `request`, `redirect`, `url_for` and the new db helpers.
- `database/db.py` — add `get_user_by_email()` and `create_user()`.
- `templates/register.html` — `url_for` action and value re-population.

## Files to create
- None (spec only: `.claude/specs/02-registration.md`).

## New dependencies
No new dependencies. Uses `werkzeug.security` (already installed) and `sqlite3`.

## Validation rules
Applied server-side in the route (HTML `required` is not sufficient):
- `name`: trimmed, non-empty.
- `email`: trimmed, lowercased, non-empty, contains `@` with text on both sides; must not already exist.
- `password`: at least 8 characters (matches the form placeholder "Min. 8 characters").
- On any failure: re-render `register.html` with `error` set and HTTP 200 (or 400), never a raw string return.
- Duplicate email error message must be generic enough to show plainly, e.g. "An account with this email already exists."

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (`generate_password_hash`); never store or log plaintext
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- DB logic lives in `database/db.py`, not in `app.py`
- Use `url_for()` for every internal link and redirect — no hardcoded URLs
- Route function does one thing: read form, call helpers, render or redirect
- Do not implement any stub route (`/logout`, `/profile`, `/expenses/*`)
- Do not add sessions, `secret_key` or flash messages in this step
- Keep the app on port 5001

## Definition of done
- [ ] `GET /register` still renders the form.
- [ ] Submitting valid name, email and an 8+ character password creates a row in `users` and redirects (302) to `/login`.
- [ ] The stored `password_hash` is a werkzeug hash, not the plaintext password.
- [ ] Submitting an email that already exists (e.g. `demo@spendly.com`) re-renders the form with an error and creates no new row.
- [ ] Email matching is case-insensitive: `Demo@Spendly.com` is rejected as a duplicate.
- [ ] A password shorter than 8 characters shows an error and creates no row.
- [ ] Empty or whitespace-only name/email shows an error and creates no row.
- [ ] On error, name and email are pre-filled and the password field is empty.
- [ ] The form action uses `url_for('register')`; no hardcoded URLs were added.
- [ ] The app starts on port 5001 with no errors and existing pages (`/`, `/login`, `/dashboard`) still load.
