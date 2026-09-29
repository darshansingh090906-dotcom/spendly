import os
import sqlite3
from contextlib import closing
from datetime import date

from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "expense_tracker.db",
)


def get_db():
    """Return a SQLite connection with dict-like rows and foreign keys enforced.

    The caller is responsible for closing the connection.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables if they do not exist. Safe to call repeatedly."""
    with closing(get_db()) as conn, conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT NOT NULL,
                email         TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at    TEXT DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(id),
                amount      REAL NOT NULL,
                category    TEXT NOT NULL,
                date        TEXT NOT NULL,
                description TEXT,
                created_at  TEXT DEFAULT (datetime('now'))
            )
            """
        )


def seed_db():
    """Insert a demo user and sample expenses, only if no users exist yet."""
    with closing(get_db()) as conn:
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
            return

        today = date.today()
        # Days are all <= 28 so they are valid in every month.
        sample_expenses = [
            (1, 12.50, "Food", "Lunch at cafe"),
            (3, 35.00, "Transport", "Metro card top-up"),
            (5, 120.00, "Bills", "Electricity bill"),
            (8, 45.75, "Health", "Pharmacy"),
            (12, 25.00, "Entertainment", "Movie tickets"),
            (15, 89.99, "Shopping", "New shoes"),
            (18, 15.00, "Other", "Miscellaneous"),
            (22, 32.40, "Food", "Weekly groceries"),
        ]

        with conn:
            cursor = conn.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
            )
            user_id = cursor.lastrowid
            conn.executemany(
                "INSERT INTO expenses (user_id, amount, category, date, description) "
                "VALUES (?, ?, ?, ?, ?)",
                [
                    (
                        user_id,
                        amount,
                        category,
                        date(today.year, today.month, day).isoformat(),
                        description,
                    )
                    for day, amount, category, description in sample_expenses
                ],
            )
