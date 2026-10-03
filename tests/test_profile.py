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
