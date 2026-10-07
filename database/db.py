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


def get_user_by_email(email):
    """Return the user row for this email, or None if there is no match."""
    with closing(get_db()) as conn:
        return conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()


def create_user(name, email, password):
    """Insert a new user with a hashed password and return the new user id.

    Raises sqlite3.IntegrityError if the email is already registered.
    """
    with closing(get_db()) as conn, conn:
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, generate_password_hash(password)),
        )
        return cursor.lastrowid


def get_user_by_id(user_id):
    """Return the user row for this id, or None if there is no match."""
    with closing(get_db()) as conn:
        return conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()


def _date_range_clause(start_date, end_date):
    """Return (sql_fragment, params) limiting expenses to an inclusive date range.

    Bounds are ISO date strings; a None bound adds no condition. The fragment
    is made only of fixed text, so values always travel as parameters.
    """
    clause = ""
    params = []
    if start_date is not None:
        clause += " AND date >= ?"
        params.append(start_date)
    if end_date is not None:
        clause += " AND date <= ?"
        params.append(end_date)
    return clause, params


def get_expense_summary(user_id, start_date=None, end_date=None):
    """Return a row with total_spent and transaction_count for this user."""
    clause, params = _date_range_clause(start_date, end_date)
    with closing(get_db()) as conn:
        return conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total_spent, "
            "COUNT(*) AS transaction_count "
            "FROM expenses WHERE user_id = ?" + clause,
            (user_id, *params),
        ).fetchone()


def get_recent_expenses(user_id, limit=10, start_date=None, end_date=None):
    """Return this user's expenses, newest first."""
    clause, params = _date_range_clause(start_date, end_date)
    with closing(get_db()) as conn:
        return conn.execute(
            "SELECT id, amount, category, date, description FROM expenses "
            "WHERE user_id = ?" + clause + " ORDER BY date DESC, id DESC LIMIT ?",
            (user_id, *params, limit),
        ).fetchall()


def get_category_totals(user_id, start_date=None, end_date=None):
    """Return (category, total) rows for this user, highest total first."""
    clause, params = _date_range_clause(start_date, end_date)
    with closing(get_db()) as conn:
        return conn.execute(
            "SELECT category, SUM(amount) AS total FROM expenses "
            "WHERE user_id = ?" + clause + " GROUP BY category "
            "ORDER BY total DESC, category ASC",
            (user_id, *params),
        ).fetchall()
