import re
from datetime import date

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


# ------------------------------------------------------------------ #
# Step 6: date filter                                                  #
# ------------------------------------------------------------------ #

def seeded_day(day):
    """ISO date for a day of the current month (the seed uses this month)."""
    return date.today().replace(day=day).isoformat()


def get_profile(client, query=""):
    log_in(client)
    response = client.get("/profile" + query)
    return response, response.get_data(as_text=True)


def test_profile_without_params_is_unfiltered(client):
    response, body = get_profile(client)
    assert response.status_code == 200
    assert "Across all time" in body
    assert "₹376" in body
    assert 'role="alert"' not in body


def test_range_includes_both_end_dates(client):
    query = f"?start={seeded_day(3)}&end={seeded_day(12)}"
    _, body = get_profile(client, query)
    assert "Metro card top-up" in body  # day 3, start bound
    assert "Movie tickets" in body  # day 12, end bound
    assert "Lunch at cafe" not in body  # day 1
    assert "New shoes" not in body  # day 15
    assert body.count("<tr>") - 1 == 4


def test_filter_applies_to_stats_table_and_breakdown(client):
    query = f"?start={seeded_day(3)}&end={seeded_day(12)}"
    _, body = get_profile(client, query)
    # 35.00 + 120.00 + 45.75 + 25.00 = 225.75
    assert "₹226" in body
    assert ">4<" in body
    assert "53% of spending" in body  # Bills 120 / 225.75
    assert body.count('class="breakdown-item"') == 4
    assert "Food" not in body.split("breakdown-list")[1]


def test_only_start_filters_from_that_date(client):
    _, body = get_profile(client, f"?start={seeded_day(18)}")
    assert "Weekly groceries" in body
    assert "Miscellaneous" in body
    assert "New shoes" not in body


def test_only_end_filters_up_to_that_date(client):
    _, body = get_profile(client, f"?end={seeded_day(3)}")
    assert "Lunch at cafe" in body
    assert "Metro card top-up" in body
    assert "Electricity bill" not in body


def test_inputs_are_prefilled_with_active_range(client):
    start, end = seeded_day(3), seeded_day(12)
    _, body = get_profile(client, f"?start={start}&end={end}")
    assert f'value="{start}"' in body
    assert f'value="{end}"' in body


def test_clear_and_all_time_links_are_unfiltered(client):
    _, body = get_profile(client, f"?start={seeded_day(3)}")
    assert 'class="filter-clear" href="/profile"' in body
    assert re.search(r'href="/profile"[^>]*>All time<', body)


def test_quick_range_links_have_correct_dates():
    from app import build_quick_ranges

    unfiltered = {"start": None, "end": None}
    feb = {r["label"]: r for r in build_quick_ranges(unfiltered, today=date(2026, 2, 10))}
    assert (feb["This month"]["start"], feb["This month"]["end"]) == ("2026-02-01", "2026-02-28")
    assert (feb["Last 30 days"]["start"], feb["Last 30 days"]["end"]) == ("2026-01-12", "2026-02-10")
    assert feb["All time"]["active"] is True
    leap = build_quick_ranges(unfiltered, today=date(2024, 2, 10))
    assert leap[0]["end"] == "2024-02-29"


def test_quick_range_marked_active_and_linked(client):
    from app import build_quick_ranges

    this_month = build_quick_ranges({"start": None, "end": None})[0]
    query = f"?start={this_month['start']}&end={this_month['end']}"
    _, body = get_profile(client, query)
    assert f"start={this_month['start']}" in body
    assert 'class="quick-range is-active"' in body


def test_empty_range_shows_zero_stats_and_empty_states(client):
    response, body = get_profile(client, "?start=2020-01-01&end=2020-01-31")
    assert response.status_code == 200
    assert "₹0" in body
    assert "No transactions in this range." in body
    assert "No spending in this range." in body
    assert "<table" not in body
    assert 'class="breakdown-item"' not in body
    assert 'role="alert"' not in body


@pytest.mark.parametrize(
    "query",
    [
        "?start=banana",
        "?end=2026-02-30",
        "?start=20260301",
        "?start=2026-05-01&end=2026-04-01",
        "?start=" + "9" * 500,
    ],
)
def test_invalid_dates_return_200_with_error(client, query):
    response, body = get_profile(client, query)
    assert response.status_code == 200
    assert 'role="alert"' in body


def test_reversed_range_falls_back_to_all_time(client):
    _, body = get_profile(client, f"?start={seeded_day(20)}&end={seeded_day(2)}")
    assert body.count("<tr>") - 1 == 8
    assert "Across all time" in body


def test_one_bad_bound_still_applies_the_valid_one(client):
    _, body = get_profile(client, f"?start=banana&end={seeded_day(3)}")
    assert 'role="alert"' in body
    assert "Metro card top-up" in body
    assert "Electricity bill" not in body


def test_filter_never_shows_other_users_expenses(client):
    other_id = db.create_user("Other One", "other@x.com", "password123")
    add_expense(other_id, 999, "Food", seeded_day(5), "Secret purchase")
    query = f"?start={seeded_day(1)}&end={seeded_day(28)}"
    _, body = get_profile(client, query)
    assert "Secret purchase" not in body
    log_in_as(client, other_id)
    body = client.get("/profile" + query).get_data(as_text=True)
    assert "Secret purchase" in body
    assert "Weekly groceries" not in body


def test_filtered_profile_redirects_when_logged_out(client):
    response = client.get("/profile?start=2026-01-01")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_empty_state_wording_when_filter_active(client):
    from flask import render_template
    from app import app as flask_app

    user = {"name": "N", "email": "n@x.com", "initials": "N", "member_since": "now"}
    filters = {"start": "2020-01-01", "end": None, "error": None, "active": True}
    with flask_app.test_request_context("/profile"):
        body = render_template(
            "profile.html",
            user=user,
            stats=[],
            transactions=[],
            categories=[],
            filters=filters,
            quick_ranges=[],
        )
    assert "No transactions in this range." in body
    assert "No spending in this range." in body


def test_db_helpers_default_args_unchanged(client):
    user = db.get_user_by_email(DEMO["email"])
    assert db.get_expense_summary(user["id"])["transaction_count"] == 8
    assert len(db.get_recent_expenses(user["id"])) == 8
    assert len(db.get_category_totals(user["id"])) == 7


def test_db_helpers_inclusive_bounds_and_limit(client):
    uid = db.get_user_by_email(DEMO["email"])["id"]
    start, end = seeded_day(3), seeded_day(12)
    summary = db.get_expense_summary(uid, start, end)
    assert summary["transaction_count"] == 4
    assert summary["total_spent"] == pytest.approx(225.75)
    rows = db.get_recent_expenses(uid, limit=2, start_date=start, end_date=end)
    assert [r["date"] for r in rows] == [seeded_day(12), seeded_day(8)]
    assert db.get_expense_summary(uid, start)["transaction_count"] == 7
    assert db.get_expense_summary(uid, None, end)["transaction_count"] == 5
    totals = db.get_category_totals(uid, start, end)
    assert totals[0]["category"] == "Bills"
    values = [r["total"] for r in totals]
    assert values == sorted(values, reverse=True)


def test_db_helpers_treat_dates_as_parameters(client):
    uid = db.get_user_by_email(DEMO["email"])["id"]
    other_id = db.create_user("Other One", "other@x.com", "password123")
    add_expense(other_id, 5, "Food", seeded_day(5), "Other row")
    # The payload is compared as a plain string: above every real date as a
    # start bound, below every real date as an end bound. If it were spliced
    # into the SQL, the OR clause would match rows regardless of the range.
    high = "9999-12-31' OR user_id != 0 --"
    low = "0000-01-01' OR user_id != 0 --"
    assert db.get_expense_summary(uid, high)["transaction_count"] == 0
    assert db.get_recent_expenses(uid, start_date=high) == []
    assert db.get_category_totals(uid, end_date=low) == []


def test_db_module_has_no_f_string_sql():
    with open("database/db.py", encoding="utf-8") as f:
        source = f.read()
    assert not re.search(r'\bf["\'][^"\']*(SELECT|INSERT|UPDATE|DELETE|WHERE)', source, re.I)
