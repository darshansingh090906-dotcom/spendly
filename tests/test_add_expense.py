import inspect
import re
from datetime import date

import pytest

from database import db

DEMO = {"email": "demo@spendly.com", "password": "demo123"}
VALID = {
    "amount": "42.50",
    "category": "Food",
    "date": "2026-03-10",
    "description": "Dinner",
}


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


def demo_id():
    return db.get_user_by_email(DEMO["email"])["id"]


def expense_count(user_id):
    return db.get_expense_summary(user_id)["transaction_count"]


def test_add_redirects_when_logged_out(client):
    for response in (client.get("/expenses/add"), client.post("/expenses/add", data=VALID)):
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")


def test_form_renders_with_fields_and_today(client):
    log_in(client)
    response = client.get("/expenses/add")
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    for name in ("amount", "category", "date", "description"):
        assert f'name="{name}"' in body
    assert f'value="{date.today().isoformat()}"' in body


def test_profile_links_to_add_form(client):
    log_in(client)
    assert 'href="/expenses/add"' in client.get("/profile").get_data(as_text=True)


def test_valid_post_saves_and_redirects(client):
    log_in(client)
    uid = demo_id()
    before = db.get_expense_summary(uid)
    response = client.post("/expenses/add", data=VALID)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")

    after = db.get_expense_summary(uid)
    assert after["transaction_count"] == before["transaction_count"] + 1
    assert after["total_spent"] == pytest.approx(before["total_spent"] + 42.50)
    newest = db.get_recent_expenses(uid, start_date="2026-03-10", end_date="2026-03-10")[0]
    assert (newest["amount"], newest["category"], newest["description"]) == (42.5, "Food", "Dinner")


def test_new_expense_shows_on_profile(client):
    log_in(client)
    client.post("/expenses/add", data={**VALID, "description": "Unique dinner xyz"})
    assert "Unique dinner xyz" in client.get("/profile").get_data(as_text=True)


def test_blank_description_saves(client):
    log_in(client)
    uid = demo_id()
    before = expense_count(uid)
    response = client.post("/expenses/add", data={**VALID, "description": ""})
    assert response.status_code == 302
    assert expense_count(uid) == before + 1


@pytest.mark.parametrize(
    "overrides",
    [
        {"amount": ""},
        {"amount": "0"},
        {"amount": "-5"},
        {"amount": "abc"},
        {"amount": "nan"},
        {"amount": "inf"},
        {"category": "Nonsense"},
        {"category": ""},
        {"date": "2026-13-45"},
        {"date": ""},
        {"date": "20260310"},
        {"description": "x" * 201},
    ],
)
def test_invalid_input_rejected(client, overrides):
    log_in(client)
    uid = demo_id()
    before = expense_count(uid)
    response = client.post("/expenses/add", data={**VALID, **overrides})
    assert response.status_code == 400
    assert 'class="auth-error"' in response.get_data(as_text=True)
    assert expense_count(uid) == before


def test_input_preserved_on_error(client):
    log_in(client)
    response = client.post(
        "/expenses/add", data={**VALID, "amount": "-1", "description": "Keep me"}
    )
    body = response.get_data(as_text=True)
    assert 'value="Keep me"' in body
    assert 'value="2026-03-10"' in body
    assert re.search(r'<option value="Food" selected>', body)


def test_expense_saved_only_for_session_user(client):
    other = db.create_user("Other", "other@x.com", "password123")
    log_in(client)
    other_before = expense_count(other)
    # A user_id smuggled into the form must be ignored.
    client.post("/expenses/add", data={**VALID, "user_id": str(other)})
    assert expense_count(other) == other_before
    assert "Dinner" not in " ".join(
        r["description"] or "" for r in db.get_recent_expenses(other)
    )


def test_amount_rounded_to_two_decimals(client):
    log_in(client)
    uid = demo_id()
    client.post("/expenses/add", data={**VALID, "amount": "10.456", "date": "2026-02-02"})
    row = db.get_recent_expenses(uid, start_date="2026-02-02", end_date="2026-02-02")[0]
    assert row["amount"] == 10.46


def test_edit_and_delete_stay_stubs(client):
    assert "coming in Step 8" in client.get("/expenses/1/edit").get_data(as_text=True)
    assert "coming in Step 9" in client.get("/expenses/1/delete").get_data(as_text=True)


def test_route_has_no_sql_or_db_connection():
    from app import add_expense

    source = inspect.getsource(add_expense)
    assert "get_db" not in source
    assert not re.search(r"\b(INSERT|SELECT|UPDATE|DELETE)\b", source)


def test_new_files_have_no_hex_or_inline_styles():
    for path in ("templates/add_expense.html", "static/css/add_expense.css"):
        with open(path, encoding="utf-8") as f:
            source = f.read()
        assert not re.search(r"#[0-9a-fA-F]{3,8}\b", source), path
        assert "style=" not in source, path
