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


def test_get_login_renders_form(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b'action="/login"' in response.data


def test_valid_login_sets_session_and_redirects(client):
    response = client.post("/login", data=DEMO)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")
    with client.session_transaction() as sess:
        assert sess["user_id"] == db.get_user_by_email(DEMO["email"])["id"]


def test_login_email_is_case_insensitive(client):
    response = client.post(
        "/login", data={"email": " Demo@Spendly.com ", "password": DEMO["password"]}
    )
    assert response.status_code == 302


def test_wrong_password_returns_401_without_session(client):
    response = client.post(
        "/login", data={"email": DEMO["email"], "password": "wrong-password"}
    )
    assert response.status_code == 401
    assert b"Invalid email or password." in response.data
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_unknown_email_gives_same_error_as_wrong_password(client):
    response = client.post(
        "/login", data={"email": "nobody@example.com", "password": "whatever123"}
    )
    assert response.status_code == 401
    assert b"Invalid email or password." in response.data


@pytest.mark.parametrize(
    "data",
    [
        {"email": "", "password": "demo123"},
        {"email": "demo@spendly.com", "password": ""},
        {"email": "   ", "password": ""},
    ],
)
def test_missing_fields_return_400_without_session(client, data):
    response = client.post("/login", data=data)
    assert response.status_code == 400
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_error_prefills_email_but_not_password(client):
    response = client.post(
        "/login", data={"email": DEMO["email"], "password": "wrong-password"}
    )
    assert b'value="demo@spendly.com"' in response.data
    assert b"wrong-password" not in response.data


def test_registered_user_can_log_in(client):
    db.create_user("Asha Rao", "asha@example.com", "longenough")
    response = client.post(
        "/login", data={"email": "asha@example.com", "password": "longenough"}
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")


def test_login_page_redirects_when_logged_in(client):
    client.post("/login", data=DEMO)
    response = client.get("/login")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")


def test_navbar_reflects_login_state(client):
    assert b"Sign out" not in client.get("/").data
    client.post("/login", data=DEMO)
    page = client.get("/").data
    assert b"Sign out" in page
    assert b"Get started" not in page


def test_logout_clears_session_and_redirects(client):
    client.post("/login", data=DEMO)
    response = client.get("/logout")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")
    with client.session_transaction() as sess:
        assert "user_id" not in sess
    assert b"Sign in" in client.get("/").data


def test_logout_while_logged_out_redirects(client):
    response = client.get("/logout")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")
