import os
import re
import sqlite3
from datetime import date

import pytest
from werkzeug.security import check_password_hash

from database import db

CATEGORIES = {"Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"}


def test_db_path_is_absolute_and_named():
    assert os.path.isabs(db.DB_PATH)
    assert os.path.basename(db.DB_PATH) == "expense_tracker.db"


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()


def test_get_db_settings(tmp_db):
    conn = db.get_db()
    try:
        assert conn.row_factory is sqlite3.Row
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    finally:
        conn.close()


def test_init_db_creates_tables_and_is_idempotent(tmp_db):
    db.init_db()
    conn = db.get_db()
    try:
        names = {
            r["name"]
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
    finally:
        conn.close()
    assert {"users", "expenses"} <= names


def test_seed_db_data(tmp_db):
    db.seed_db()
    conn = db.get_db()
    try:
        users = conn.execute("SELECT * FROM users").fetchall()
        expenses = conn.execute("SELECT * FROM expenses").fetchall()
    finally:
        conn.close()

    assert len(users) == 1
    user = users[0]
    assert user["name"] == "Demo User"
    assert user["email"] == "demo@spendly.com"
    assert user["password_hash"] != "demo123"
    assert check_password_hash(user["password_hash"], "demo123")

    assert len(expenses) == 8
    assert {e["user_id"] for e in expenses} == {user["id"]}
    assert {e["category"] for e in expenses} == CATEGORIES
    month_prefix = date.today().strftime("%Y-%m")
    for e in expenses:
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", e["date"])
        assert e["date"].startswith(month_prefix)


def test_seed_db_is_idempotent(tmp_db):
    db.seed_db()
    db.seed_db()
    conn = db.get_db()
    try:
        assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0] == 8
    finally:
        conn.close()


def test_foreign_key_enforced(tmp_db):
    conn = db.get_db()
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO expenses (user_id, amount, category, date) VALUES (?, ?, ?, ?)",
                (9999, 1.0, "Food", "2026-01-01"),
            )
    finally:
        conn.close()


def test_unique_email_enforced(tmp_db):
    db.seed_db()
    conn = db.get_db()
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                ("Other", "demo@spendly.com", "x"),
            )
    finally:
        conn.close()
