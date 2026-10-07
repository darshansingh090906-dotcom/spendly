import re

import pytest

from database import db

DEMO = {"email": "demo@spendly.com", "password": "demo123"}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    db.seed_db()
    # Imported lazily: app.py runs init_db()/seed_db() at import time.
    from app import app as flask_app

    flask_app.config["TESTING"] = True
    return flask_app.test_client()


def log_in(client):
    return client.post("/login", data=DEMO)


def test_profile_redirects_when_logged_out(client):
    response = client.get("/profile")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_profile_renders_when_logged_in(client):
    log_in(client)
    response = client.get("/profile")
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Demo User" in body
    assert "demo@spendly.com" in body
    assert "Member since" in body


def test_profile_has_stats_transactions_and_categories(client):
    log_in(client)
    body = client.get("/profile").get_data(as_text=True)
    assert body.count('class="stat-card"') >= 3
    assert body.count("<tr>") - 1 >= 3  # minus the header row
    assert body.count('class="breakdown-item"') >= 3


def test_navbar_links_when_logged_in(client):
    log_in(client)
    body = client.get("/profile").get_data(as_text=True)
    assert "Profile</a>" in body
    assert "Sign out" in body


def test_dashboard_route_is_gone(client):
    assert client.get("/dashboard").status_code == 404


def test_profile_template_has_no_hex_or_inline_styles():
    with open("templates/profile.html", encoding="utf-8") as f:
        source = f.read()
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", source)
    assert "style=" not in source


def test_table_and_breakdown_are_accessible(client):
    log_in(client)
    body = client.get("/profile").get_data(as_text=True)
    assert body.count('scope="col"') == 4
    assert "<caption" in body
    assert 'role="region"' in body
    assert body.count("<progress") == body.count("aria-label=\"") - 1  # minus table region


def test_empty_states_render_without_rows(client):
    from flask import render_template
    from app import app as flask_app

    user = {"name": "N", "email": "n@x.com", "initials": "N", "member_since": "now"}
    with flask_app.test_request_context("/profile"):
        body = render_template(
            "profile.html", user=user, stats=[], transactions=[], categories=[]
        )
    assert "No transactions yet." in body
    assert "No spending to break down yet." in body
    assert "<table" not in body


def test_profile_stylesheet_has_no_hex_colours():
    with open("static/css/profile.css", encoding="utf-8") as f:
        assert not re.search(r"#[0-9a-fA-F]{3,8}\b", f.read())


# ------------------------------------------------------------------ #
# Step 5: profile wired to the database                                #
# ------------------------------------------------------------------ #

def add_expense(user_id, amount, category, day, description="x"):
    with db.get_db() as conn:
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, day, description),
        )
    conn.close()


def log_in_as(client, user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def test_profile_shows_database_values(client):
    log_in(client)
    body = client.get("/profile").get_data(as_text=True)
    assert "₹376" in body  # 375.64 rounded
    assert ">8<" in body
    assert "Weekly groceries" in body


def test_transactions_are_newest_first(client):
    user = db.get_user_by_email(DEMO["email"])
    rows = db.get_recent_expenses(user["id"])
    dates = [r["date"] for r in rows]
    assert dates == sorted(dates, reverse=True)


def test_categories_ordered_and_top_category(client):
    user = db.get_user_by_email(DEMO["email"])
    totals = db.get_category_totals(user["id"])
    values = [r["total"] for r in totals]
    assert values == sorted(values, reverse=True)
    assert totals[0]["category"] == "Bills"
    log_in(client)
    body = client.get("/profile").get_data(as_text=True)
    assert "Top Category" in body
    assert "32% of spending" in body


def test_new_user_with_no_expenses_sees_empty_states(client):
    user_id = db.create_user("New Person", "new@x.com", "password123")
    log_in_as(client, user_id)
    response = client.get("/profile")
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "No transactions yet." in body
    assert "No spending to break down yet." in body
    assert "₹0" in body
    assert "NP" in body


def test_user_only_sees_own_expenses(client):
    other_id = db.create_user("Other One", "other@x.com", "password123")
    add_expense(other_id, 999, "Food", "2026-01-05", "Secret purchase")
    log_in(client)
    assert "Secret purchase" not in client.get("/profile").get_data(as_text=True)
    log_in_as(client, other_id)
    body = client.get("/profile").get_data(as_text=True)
    assert "Secret purchase" in body
    assert "Weekly groceries" not in body


def test_missing_session_user_returns_404(client):
    log_in_as(client, 9999)
    assert client.get("/profile").status_code == 404


def test_db_helpers_summary_and_missing_user(client):
    user = db.get_user_by_email(DEMO["email"])
    summary = db.get_expense_summary(user["id"])
    assert summary["transaction_count"] == 8
    assert summary["total_spent"] == pytest.approx(375.64)
    assert db.get_user_by_id(9999) is None
    empty = db.get_expense_summary(9999)
    assert empty["total_spent"] == 0 and empty["transaction_count"] == 0


def test_profile_route_has_no_sql():
    import inspect

    import app as app_module

    source = inspect.getsource(app_module.profile)
    assert "get_db" not in source
    assert "SELECT" not in source.upper()
