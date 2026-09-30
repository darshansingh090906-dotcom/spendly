import sqlite3
from contextlib import closing

import pytest
from werkzeug.security import check_password_hash

from database import db

VALID = {"name": "Asha Rao", "email": "asha@example.com", "password": "longenough"}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    db.seed_db()
    # Imported lazily: app.py runs init_db()/seed_db() at import time.
    from app import app as flask_app

    flask_app.config["TESTING"] = True
    return flask_app.test_client()


def count_users():
    with closing(db.get_db()) as conn:
        return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]


def test_get_register_renders_form(client):
    response = client.get("/register")
    assert response.status_code == 200
    assert b'action="/register"' in response.data


def test_valid_registration_redirects_and_hashes_password(client):
    before = count_users()
    response = client.post("/register", data=VALID)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    assert count_users() == before + 1

    user = db.get_user_by_email("asha@example.com")
    assert user["name"] == "Asha Rao"
    assert user["password_hash"] != VALID["password"]
    assert check_password_hash(user["password_hash"], VALID["password"])


def test_email_is_trimmed_and_lowercased(client):
    data = {**VALID, "email": "  New@Example.COM "}
    assert client.post("/register", data=data).status_code == 302
    assert db.get_user_by_email("new@example.com") is not None


def test_password_of_exactly_eight_characters_is_accepted(client):
    data = {**VALID, "password": "12345678"}
    assert client.post("/register", data=data).status_code == 302


@pytest.mark.parametrize("email", ["demo@spendly.com", "Demo@Spendly.com"])
def test_duplicate_email_rejected(client, email):
    before = count_users()
    response = client.post("/register", data={**VALID, "email": email})
    assert response.status_code == 400
    assert b"already exists" in response.data
    assert count_users() == before


@pytest.mark.parametrize(
    "field, value",
    [
        ("password", "1234567"),
        ("name", ""),
        ("name", "   "),
        ("email", ""),
        ("email", "   "),
        ("email", "abc"),
        ("email", "@x.com"),
        ("email", "a@"),
    ],
)
def test_invalid_input_rejected(client, field, value):
    before = count_users()
    response = client.post("/register", data={**VALID, field: value})
    assert response.status_code == 400
    assert b"auth-error" in response.data
    assert count_users() == before


def test_empty_form_rejected(client):
    before = count_users()
    response = client.post("/register", data={})
    assert response.status_code == 400
    assert count_users() == before


def test_error_repopulates_name_and_email_but_not_password(client):
    data = {"name": "Asha Rao", "email": "asha@example.com", "password": "short"}
    response = client.post("/register", data=data)
    body = response.get_data(as_text=True)
    assert response.status_code == 400
    assert 'value="Asha Rao"' in body
    assert 'value="asha@example.com"' in body
    assert "short" not in body.split('id="password"')[1].split(">")[0]


@pytest.mark.parametrize("path", ["/", "/login", "/dashboard"])
def test_other_pages_still_load(client, path):
    assert client.get(path).status_code == 200


def test_create_user_returns_id_and_rejects_duplicates(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "unit.db"))
    db.init_db()
    user_id = db.create_user("A B", "ab@example.com", "password123")
    assert isinstance(user_id, int)
    with pytest.raises(sqlite3.IntegrityError):
        db.create_user("A B", "ab@example.com", "password123")


def test_get_user_by_email(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "unit.db"))
    db.init_db()
    db.seed_db()
    assert db.get_user_by_email("nobody@example.com") is None
    assert db.get_user_by_email("demo@spendly.com")["name"] == "Demo User"
