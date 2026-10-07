# Spec: Profile Backend Route

## Overview
This feature wires the `/profile` page to the database. Step 4 built the full profile UI using hardcoded Python dicts in `app.py`. Step 5 replaces that sample data with real data for the logged-in user: their name, email and join date from `users`, and their summary stats, recent transactions and category breakdown computed from `expenses`. All queries live in `database/db.py`; the route only fetches data, formats it, and renders the existing `profile.html`.

## Depends on
- Step 1: Database setup (`users` and `expenses` tables, `get_db()`, `seed_db()`)
- Step 2: Registration (users can be created)
- Step 3: Login + Logout (`session["user_id"]` is set)
- Step 4: Profile page (`profile.html` and `profile.css` exist and define the context shape)

## Routes
- `GET /profile` — render the profile page using real data for the session user — logged-in only (redirect to `/login` if not authenticated; `abort(404)` if the session user no longer exists)

No new routes.

## Database changes
No database changes. The existing `users` and `expenses` tables are sufficient.

New helper functions in `database/db.py` (all use `get_db()` inside `closing(...)` and parameterised queries):
- `get_user_by_id(user_id)` — return the user row or `None`
- `get_expense_summary(user_id)` — return total spent and transaction count for the user (total is 0 and count is 0 when there are no expenses)
- `get_recent_expenses(user_id, limit=10)` — return the user's expenses ordered by `date DESC, id DESC`
- `get_category_totals(user_id)` — return `(category, total)` rows ordered by total descending

## Templates
- **Create:** none
- **Modify:** `templates/profile.html` only if the context shape has to change (preferred: keep `user`, `stats`, `transactions`, `categories` exactly as Step 4 defined them, so no template changes are needed). Template changes are limited to handling empty states already present.

## Files to change
- `app.py` — replace the hardcoded sample data in `profile()` with calls to the new `db.py` helpers; add small formatting helpers (currency, date, initials, member-since); import `abort`
- `database/db.py` — add the four helper functions above

## Files to create
- `tests/test_profile.py` — pytest tests for the profile route and the new db helpers (uses a temporary database, not the real `expense_tracker.db`)

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never f-strings in SQL
- Passwords hashed with werkzeug (no auth changes in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- DB logic belongs in `database/db.py` only — the route must not open connections or contain SQL
- Route stays one responsibility: auth guard, fetch data, format, render
- Auth guard stays `session.get("user_id")`; redirect with `url_for("login")`
- Every query is scoped by `user_id` from the session — a user must never see another user's expenses
- Use `abort(404)` (not a raw string) if the session user id has no matching row; clear nothing silently
- Format currency with the `₹` symbol and thousands separators to match the Step 4 display (e.g. `₹3,240`); percentages are integers and category percents are calculated from the user's total (0 total → empty list, no division by zero)
- Top category stat: highest total category, with its share of spending in the note; show a sensible placeholder (e.g. `—`) when there are no expenses
- Do not implement `/expenses/add`, `/expenses/<id>/edit` or `/expenses/<id>/delete` — they stay stubs

## Definition of done
- [ ] Visiting `/profile` while logged out redirects to `/login`
- [ ] Logged in as the seeded demo user (`demo@spendly.com` / `demo123`), `/profile` returns 200 and shows "Demo User" and `demo@spendly.com` from the database, not hardcoded values
- [ ] Total Spent equals the sum of the demo user's expenses and Transactions equals 8 (the seeded count)
- [ ] The transaction table lists the user's expenses newest first with date, description, category badge and amount
- [ ] The category breakdown lists categories highest to lowest and the percentages add up to roughly 100
- [ ] Top Category shows the category with the largest total
- [ ] A newly registered user with no expenses sees 200 with zero stats, "No transactions yet." and no breakdown, with no errors
- [ ] A user only sees their own expenses (verified with two users)
- [ ] A session pointing at a deleted/nonexistent user id returns 404
- [ ] `grep` finds no SQL or `get_db()` calls in `profile()` in `app.py`
- [ ] `pytest` passes, including the new `tests/test_profile.py`
