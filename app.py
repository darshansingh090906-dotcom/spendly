import os
import sqlite3

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from database.db import (  # noqa: F401  (get_db used in later steps)
    create_user,
    get_db,
    get_user_by_email,
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


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    # Hardcoded sample data until the profile is wired to the database.
    user = {
        "name": "Demo User",
        "email": "demo@spendly.com",
        "initials": "DU",
        "member_since": "January 2026",
    }
    stats = [
        {"label": "Total Spent", "value": "₹37,564", "note": "Across all time"},
        {"label": "Transactions", "value": "8", "note": "Logged so far"},
        {"label": "Top Category", "value": "Bills", "note": "32% of spending"},
    ]
    transactions = [
        {"date": "Mar 22", "description": "Weekly groceries", "category": "Food", "amount": "₹3,240"},
        {"date": "Mar 18", "description": "Miscellaneous", "category": "Other", "amount": "₹1,500"},
        {"date": "Mar 15", "description": "New shoes", "category": "Shopping", "amount": "₹8,999"},
        {"date": "Mar 12", "description": "Movie tickets", "category": "Entertainment", "amount": "₹2,500"},
        {"date": "Mar 05", "description": "Electricity bill", "category": "Bills", "amount": "₹12,000"},
    ]
    categories = [
        {"name": "Bills", "amount": "₹12,000", "percent": 32},
        {"name": "Shopping", "amount": "₹8,999", "percent": 24},
        {"name": "Other", "amount": "₹7,500", "percent": 20},
        {"name": "Health", "amount": "₹4,575", "percent": 12},
        {"name": "Food", "amount": "₹4,490", "percent": 12},
    ]
    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
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
