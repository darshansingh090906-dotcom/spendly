from flask import Flask, render_template

from database.db import get_db, init_db, seed_db  # noqa: F401  (get_db used in later steps)

app = Flask(__name__)


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register")
def register():
    return render_template("register.html")


@app.route("/login")
def login():
    return render_template("login.html")


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


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    return "Logout — coming in Step 3"


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
