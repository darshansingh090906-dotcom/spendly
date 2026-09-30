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
            return redirect(url_for("dashboard"))
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
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    # Sample data until expenses are stored in a database.
    stats = [
        {"label": "Total Liquidity", "value": "₹3,42,800", "note": "↑ +8.4% from last month", "tone": "up"},
        {"label": "Monthly Outflow", "value": "₹54,200", "note": "Cap: ₹68,000", "tone": "muted"},
        {"label": "Net Savings Rate", "value": "41.8%", "note": "On track for targets", "tone": "up", "accent": True},
    ]
    cash_flow = [
        {"month": "Oct", "inflow": 75, "expense": 45},
        {"month": "Nov", "inflow": 80, "expense": 50},
        {"month": "Dec", "inflow": 95, "expense": 65},
        {"month": "Jan", "inflow": 85, "expense": 42},
        {"month": "Feb", "inflow": 90, "expense": 40},
        {"month": "Mar", "inflow": 100, "expense": 38, "current": True},
    ]
    transactions = [
        {"icon": "🛒", "name": "Nature's Basket", "when": "Today", "category": "Groceries", "amount": "-₹1,420", "tone": "green"},
        {"icon": "⚡", "name": "State Electricity", "when": "Yesterday", "category": "Utility", "amount": "-₹2,100", "tone": "blue"},
        {"icon": "🎵", "name": "Spotify Annual", "when": "Mar 22", "category": "Subs", "amount": "-₹1,199", "tone": "purple"},
        {"icon": "☕", "name": "Blue Tokai Coffee", "when": "Mar 20", "category": "Dining", "amount": "-₹380", "tone": "amber"},
    ]
    return render_template(
        "dashboard.html", stats=stats, cash_flow=cash_flow, transactions=transactions
    )


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


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/profile")
def profile():
    return "Profile page — coming in Step 4"


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
