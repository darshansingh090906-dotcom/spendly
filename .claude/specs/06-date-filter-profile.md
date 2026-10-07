# Spec: Date Filter Profile

## Overview
This feature lets a logged-in user narrow the profile page to a date range. Step 5 wired `/profile` to real data, but every figure covers all time. Step 6 adds optional `start` and `end` query parameters to `GET /profile` and a filter bar on the page. The date range scopes the summary stats, the transaction history and the category breakdown together, so the page always tells one consistent story. With no parameters the page behaves exactly as it does today.

## Depends on
- Step 1: Database setup (`expenses.date` stored as ISO `YYYY-MM-DD` text)
- Step 3: Login + Logout (`session["user_id"]`)
- Step 4: Profile page (`profile.html`, `profile.css`)
- Step 5: Profile backend route (`get_expense_summary`, `get_recent_expenses`, `get_category_totals`, and the formatting helpers in `app.py`)

## Routes
- `GET /profile` — now accepts optional `start` and `end` query parameters (`YYYY-MM-DD`, both inclusive) — logged-in only (unchanged: redirect to `/login` if not authenticated, `abort(404)` if the session user no longer exists)

No new routes.

## Database changes
No database changes. `expenses.date` is already ISO text, so range comparison with `date >= ?` and `date <= ?` sorts correctly.

Modify the existing helpers in `database/db.py` to take optional `start_date=None, end_date=None` arguments (ISO strings or `None`):
- `get_expense_summary(user_id, start_date=None, end_date=None)`
- `get_recent_expenses(user_id, limit=10, start_date=None, end_date=None)`
- `get_category_totals(user_id, start_date=None, end_date=None)`

Rules for these changes:
- A `None` bound adds no condition, so existing callers and tests keep working unchanged
- Build the `WHERE` clause only from fixed SQL fragments (`AND date >= ?`, `AND date <= ?`) and pass the values as parameters. Never put a value into the SQL string
- Every query stays scoped by `user_id`

## Templates
- **Create:** none
- **Modify:** `templates/profile.html`
  - Add a filter bar above the stat row: two `<input type="date">` fields (From, To) inside a `<form method="get" action="{{ url_for('profile') }}">`, an "Apply" button and a "Clear" link to `url_for('profile')`
  - Pre-fill the inputs with the active `filters.start` / `filters.end`
  - Add quick-range links built with `url_for('profile', start=..., end=...)`: "This month", "Last 30 days", "All time"
  - Show `filters.error` (if set) in an alert element above the stat row
  - Show the active range in the stat card notes (e.g. "Mar 01 – Mar 31") instead of "Across all time" when a filter is active
  - Use "No transactions in this range." / "No spending in this range." for the empty states when a filter is active, and the existing wording otherwise

## Files to change
- `app.py` — parse and validate `start` / `end` in `profile()` (or a small helper it calls), pass them to the db helpers, add `filters` to the template context, adapt `build_stats` notes for an active range
- `database/db.py` — add the optional date-range arguments to the three helpers above
- `templates/profile.html` — filter bar, error message, range-aware notes and empty states
- `static/css/profile.css` — styles for the filter bar and error message (use existing CSS variables)
- `tests/test_profile.py` — add filter tests (see Definition of done)

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never f-strings in SQL, including the date conditions
- Passwords hashed with werkzeug (no auth changes in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- DB logic belongs in `database/db.py` only — the route must not open connections or contain SQL
- Route stays one responsibility: auth guard, parse filters, fetch, format, render
- Validate dates with `date.fromisoformat()`. Reject anything else (wrong format, impossible dates like `2026-02-30`)
- Invalid input must never cause a 500. On a malformed date, fall back to no bound for that field and show a clear error message; on `start` later than `end`, show an error and fall back to all time. Return 200 in both cases
- A single bound is valid: only `start` means "from that date onwards", only `end` means "up to and including that date"
- Both bounds are inclusive
- Filter state lives in the URL (GET), so a filtered page can be bookmarked or refreshed. Use no session storage and no JavaScript requirement; the form must work with JS disabled
- Use `url_for()` for every link, including the quick-range links. Compute their dates in Python, never hardcode them
- Percentages in the category breakdown are calculated from the filtered total (0 total → empty list, no division by zero)
- Top Category and the other stats reflect the filtered range only
- Every query stays scoped by `user_id` from the session — a filter must never expose another user's expenses
- Do not implement `/expenses/add`, `/expenses/<id>/edit` or `/expenses/<id>/delete` — they stay stubs

## Definition of done
- [ ] `/profile` with no parameters looks and behaves exactly as before
- [ ] `/profile?start=YYYY-MM-DD&end=YYYY-MM-DD` as the demo user shows only expenses inside that range, with both end dates included
- [ ] Total Spent, Transactions, Top Category, the transaction table and the category breakdown all reflect the filtered range
- [ ] Using only `start` or only `end` filters on that single bound
- [ ] The filter inputs are pre-filled with the active range after submitting
- [ ] "Clear" and "All time" return to the unfiltered view
- [ ] "This month" and "Last 30 days" show the correct ranges
- [ ] A range with no expenses returns 200 with zero stats, "No transactions in this range.", no breakdown and no errors
- [ ] `?start=banana`, `?end=2026-02-30` and `?start=2026-05-01&end=2026-04-01` return 200 with a visible error message, not a 500
- [ ] A filter never shows another user's expenses (verified with two users)
- [ ] The filter form works with JavaScript disabled
- [ ] `grep` finds no SQL or `get_db()` calls in `profile()` in `app.py`, and no f-strings in SQL in `db.py`
- [ ] Logged out, `/profile?start=...` still redirects to `/login`
- [ ] `pytest` passes, including the new filter tests in `tests/test_profile.py`
