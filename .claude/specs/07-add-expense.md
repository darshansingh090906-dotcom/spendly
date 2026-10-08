# Spec: Add Expense

## Overview
This feature lets a logged-in user record a new expense. Steps 5 and 6 made the profile page read real expense data (with a date filter), but the only way to create expenses is the seed script. Step 7 turns the `/expenses/add` stub into a real form: the user enters an amount, category, date and optional description, the expense is saved against their account, and they are sent back to the profile page where it appears in recent transactions and the totals.

## Depends on
- Step 1: Database setup (`expenses` table, `get_db()` with foreign keys on)
- Step 3: Login + Logout (`session["user_id"]`)
- Step 5: Profile backend route (profile shows the user's expenses)
- Step 6: Date filter on profile (the new expense must show up under "All time" and the matching range)

## Routes
- `GET /expenses/add` — render the add-expense form with today's date prefilled — logged-in only (redirect to `/login` if not authenticated)
- `POST /expenses/add` — validate the form, insert the expense for the session user, redirect to `/profile` — logged-in only. On validation error re-render the form with a message and the user's input preserved, status 400

The existing `add_expense` function is extended to accept `GET` and `POST`; no other routes change.

## Database changes
No schema changes. The existing `expenses` table (`user_id`, `amount`, `category`, `date`, `description`) is sufficient.

New helper in `database/db.py` (uses `closing(get_db())`, parameterised query):
- `create_expense(user_id, amount, category, date, description)` — insert one row and return the new expense id

## Templates
- **Create:** `templates/add_expense.html` — extends `base.html`; form with amount, category (select), date (`type="date"`), description (optional); shows the error message; cancel link back to the profile
- **Modify:** `templates/profile.html` — add an "Add expense" link using `url_for('add_expense')` (also in the empty "No transactions yet." state)

## Files to change
- `app.py` — implement `add_expense()` for GET/POST; add `EXPENSE_CATEGORIES` constant and a `validate_expense()` helper; import `create_expense`
- `database/db.py` — add `create_expense()`
- `templates/profile.html` — link to the add-expense page
- `static/css/profile.css` — styling for the new link, only if needed (CSS variables only)
- `CLAUDE.md` — mark `GET /expenses/add` as implemented in the routes table

## Files to create
- `templates/add_expense.html`
- `static/css/add_expense.css` — page-specific styles (no inline `<style>`)
- `tests/test_add_expense.py` — pytest tests using a temporary database

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never f-strings in SQL
- Passwords hashed with werkzeug (no auth changes in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- DB logic belongs in `database/db.py` only — the route must not open connections or contain SQL
- Auth guard is `session.get("user_id")`; redirect with `url_for("login")`. The expense is always saved with the session user's id — never a user id from the form
- Categories come from one fixed list matching the seeded ones: Food, Transport, Bills, Health, Entertainment, Shopping, Other. Reject anything else server-side
- Amount: must parse as a number, be greater than 0, be finite (reject `nan`/`inf`), and be rounded to 2 decimals before saving
- Date: strictly `YYYY-MM-DD` — reuse `parse_iso_date()`; a future date is allowed
- Description: optional, stripped, max 200 characters
- Validation errors re-render `add_expense.html` with status 400 and keep the user's input; use `abort()` for HTTP errors, never raw string returns
- Redirect with `url_for("profile")` after a successful save (POST/redirect/GET)
- Use `url_for()` for every link; never hardcode URLs
- Do not implement `/expenses/<id>/edit` or `/expenses/<id>/delete` — they stay stubs

## Definition of done
- [ ] Visiting `/expenses/add` while logged out redirects to `/login` (GET and POST)
- [ ] Logged in, `/expenses/add` returns 200 with amount, category, date and description fields, and the date defaults to today
- [ ] The profile page has an "Add expense" link that opens the form
- [ ] Submitting a valid expense redirects to `/profile`, and the new expense appears first in recent transactions with correct date, description, category and amount
- [ ] Total Spent and Transactions on `/profile` increase by the new amount and 1
- [ ] An empty, zero, negative or non-numeric amount shows an error, returns 400 and saves nothing
- [ ] An unknown category, an invalid date (e.g. `2026-13-45`) or a description over 200 characters shows an error, returns 400 and saves nothing
- [ ] After a validation error the form still shows what the user typed
- [ ] An expense is saved only for the logged-in user — a second user does not see it
- [ ] The description can be left blank and the expense still saves
- [ ] `grep` finds no SQL or `get_db()` calls in `add_expense()` in `app.py`
- [ ] `/expenses/<id>/edit` and `/expenses/<id>/delete` still return their stub responses
- [ ] `pytest` passes, including the new `tests/test_add_expense.py`
