import calendar
import os
import sqlite3
from datetime import date, timedelta

from flask import Flask, abort, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from database.db import (  # noqa: F401  (get_db used in later steps)
    create_user,
    get_category_totals,
    get_db,
    get_expense_summary,
    get_recent_expenses,
    get_user_by_email,
    get_user_by_id,
    init_db,
    seed_db,
)

app = Flask(__name__)
# The fallback is for local development only — set SPENDLY_SECRET_KEY in production.
app.secret_key = os.environ.get("SPENDLY_SECRET_KEY", "dev-only-insecure-key")


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


DUPLICATE_EMAIL_ERROR = "An account with this email already exists."


def validate_registration(name, email, password):
    """Return an error message for invalid registration input, else None."""
    if not name:
        return "Please enter your full name."
    local, sep, domain = email.partition("@")
    if not (local and sep and domain):
        return "Please enter a valid email address."
    if len(password) < 8:
        return "Password must be at least 8 characters."
    if get_user_by_email(email) is not None:
        return DUPLICATE_EMAIL_ERROR
    return None


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    error = validate_registration(name, email, password)
    if error is None:
        try:
            create_user(name, email, password)
        except sqlite3.IntegrityError:
            error = DUPLICATE_EMAIL_ERROR
    if error:
        return render_template("register.html", error=error, name=name, email=email), 400
    return redirect(url_for("login"))


INVALID_CREDENTIALS_ERROR = "Invalid email or password."


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if session.get("user_id"):
            return redirect(url_for("profile"))
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not email or not password:
        return render_template(
            "login.html", error="Please enter your email and password.", email=email
        ), 400

    user = get_user_by_email(email)
    if user is None or not check_password_hash(user["password_hash"], password):
        return render_template(
            "login.html", error=INVALID_CREDENTIALS_ERROR, email=email
        ), 401

    session.clear()
    session["user_id"] = user["id"]
    return redirect(url_for("profile"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


def format_currency(amount):
    """Format an amount as whole rupees with thousands separators."""
    return f"₹{round(amount):,}"


def format_short_date(iso_date):
    """Turn 2026-03-22 into 'Mar 22'."""
    return date.fromisoformat(iso_date).strftime("%b %d")


def format_member_since(created_at):
    """Turn a SQLite datetime string into 'January 2026'."""
    return date.fromisoformat(created_at[:10]).strftime("%B %Y")


def get_initials(name):
    """Return the first letters of the first and last words of a name."""
    words = name.split()
    if not words:
        return "?"
    if len(words) == 1:
        return words[0][0].upper()
    return (words[0][0] + words[-1][0]).upper()


INVALID_START_ERROR = "Start date is not a valid date. Use YYYY-MM-DD."
INVALID_END_ERROR = "End date is not a valid date. Use YYYY-MM-DD."
REVERSED_RANGE_ERROR = "Start date must be on or before the end date."


def parse_iso_date(raw):
    """Return raw as a date if it is strictly YYYY-MM-DD, else None."""
    try:
        parsed = date.fromisoformat(raw)
    except ValueError:
        return None
    # Python 3.11+ also accepts forms like 20260301; the DB needs padded ISO.
    return parsed if parsed.isoformat() == raw else None


def parse_date_filters(args):
    """Read the start/end query parameters into a validated filter dict.

    Never raises: bad input drops that bound and sets an error message.
    """
    bounds = {}
    errors = []
    for key, message in (("start", INVALID_START_ERROR), ("end", INVALID_END_ERROR)):
        raw = args.get(key, "").strip()
        bounds[key] = None
        if not raw:
            continue
        parsed = parse_iso_date(raw)
        if parsed is None:
            errors.append(message)
        else:
            bounds[key] = parsed.isoformat()

    if bounds["start"] and bounds["end"] and bounds["start"] > bounds["end"]:
        errors.append(REVERSED_RANGE_ERROR)
        bounds["start"] = bounds["end"] = None

    return {
        "start": bounds["start"],
        "end": bounds["end"],
        "error": " ".join(errors) or None,
        "active": bool(bounds["start"] or bounds["end"]),
    }


def format_range_date(iso_date):
    """Turn 2026-03-22 into 'Mar 22', adding the year if it is not this year."""
    parsed = date.fromisoformat(iso_date)
    pattern = "%b %d" if parsed.year == date.today().year else "%b %d, %Y"
    return parsed.strftime(pattern)


def build_range_note(start, end):
    """Describe an active date range, e.g. 'Mar 01 – Mar 31'."""
    if start and end:
        return f"{format_range_date(start)} – {format_range_date(end)}"
    if start:
        return f"From {format_range_date(start)}"
    return f"Up to {format_range_date(end)}"


def build_quick_ranges(filters, today=None):
    """Build the quick-range links (this month, last 30 days, all time)."""
    today = today or date.today()
    month_end = date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
    ranges = [
        ("This month", today.replace(day=1).isoformat(), month_end.isoformat()),
        ("Last 30 days", (today - timedelta(days=29)).isoformat(), today.isoformat()),
        ("All time", None, None),
    ]
    return [
        {
            "label": label,
            "start": start,
            "end": end,
            "active": (filters["start"], filters["end"]) == (start, end),
        }
        for label, start, end in ranges
    ]


def build_stats(summary, category_totals, filters=None):
    """Build the summary stat cards for the profile page."""
    total = summary["total_spent"]
    range_note = None
    if filters and filters["active"]:
        range_note = build_range_note(filters["start"], filters["end"])
    if category_totals and total > 0:
        top = category_totals[0]
        top_name = top["category"]
        top_note = f"{round(top['total'] / total * 100)}% of spending"
    else:
        top_name = "—"
        top_note = "No spending in this range" if range_note else "No spending yet"
    return [
        {
            "label": "Total Spent",
            "value": format_currency(total),
            "note": range_note or "Across all time",
        },
        {
            "label": "Transactions",
            "value": str(summary["transaction_count"]),
            "note": range_note or "Logged so far",
        },
        {"label": "Top Category", "value": top_name, "note": top_note},
    ]


def build_categories(category_totals, total):
    """Build the category breakdown rows with integer percentages."""
    if total <= 0:
        return []
    return [
        {
            "name": row["category"],
            "amount": format_currency(row["total"]),
            "percent": round(row["total"] / total * 100),
        }
        for row in category_totals
    ]


@app.route("/profile")
def profile():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    user_row = get_user_by_id(user_id)
    if user_row is None:
        abort(404)

    filters = parse_date_filters(request.args)
    start, end = filters["start"], filters["end"]
    summary = get_expense_summary(user_id, start, end)
    category_totals = get_category_totals(user_id, start, end)

    user = {
        "name": user_row["name"],
        "email": user_row["email"],
        "initials": get_initials(user_row["name"]),
        "member_since": format_member_since(user_row["created_at"]),
    }
    transactions = [
        {
            "date": format_short_date(row["date"]),
            "description": row["description"] or "",
            "category": row["category"],
            "amount": format_currency(row["amount"]),
        }
        for row in get_recent_expenses(user_id, start_date=start, end_date=end)
    ]
    return render_template(
        "profile.html",
        user=user,
        stats=build_stats(summary, category_totals, filters),
        transactions=transactions,
        categories=build_categories(category_totals, summary["total_spent"]),
        filters=filters,
        quick_ranges=build_quick_ranges(filters),
    )


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


with app.app_context():
    init_db()
    seed_db()


if __name__ == "__main__":
    app.run(debug=True, port=5001)
