"""Bodyweight tracking — the series the coach reasons about.

Regression target: "current weight" used to be `profile.weight_kg`, frozen at
onboarding, so the dashboard could never show progress.
"""
from datetime import date, timedelta


def test_weight_series_is_empty_before_any_weigh_in(client, auth_headers):
    r = client.get("/api/v1/progress/weight", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["entries"] == [] and body["latest_kg"] is None


def test_log_and_read_back_a_weigh_in(client, auth_headers):
    r = client.put("/api/v1/progress/weight", json={"weight_kg": 81.4}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["weight_kg"] == 81.4

    series = client.get("/api/v1/progress/weight", headers=auth_headers).json()
    assert series["latest_kg"] == 81.4
    assert series["days_tracked"] == 1


def test_same_day_reweigh_corrects_rather_than_duplicates(client, auth_headers):
    for w in (80.0, 79.5):
        client.put("/api/v1/progress/weight", json={"weight_kg": w}, headers=auth_headers)
    series = client.get("/api/v1/progress/weight", headers=auth_headers).json()
    assert series["days_tracked"] == 1
    assert series["latest_kg"] == 79.5


def test_change_is_measured_across_the_window(client, auth_headers):
    today = date.today()
    for i, w in enumerate((84.0, 83.0, 82.0)):
        day = (today - timedelta(days=2 - i)).isoformat()
        client.put(
            "/api/v1/progress/weight", json={"weight_kg": w, "date": day}, headers=auth_headers
        )
    series = client.get("/api/v1/progress/weight", headers=auth_headers).json()
    assert series["days_tracked"] == 3
    assert series["latest_kg"] == 82.0
    assert series["change_kg"] == -2.0


def test_absurd_weights_are_rejected(client, auth_headers):
    for bad in (7.5, 750, 0, -5):
        r = client.put("/api/v1/progress/weight", json={"weight_kg": bad}, headers=auth_headers)
        assert r.status_code == 422, f"accepted {bad} kg"


def test_dashboard_tracks_the_latest_weigh_in(client, auth_headers, onboarded):
    """The regression that mattered: the weight card must move."""
    before = client.get("/api/v1/dashboard/summary", headers=auth_headers).json()
    start = before["current_weight_kg"]

    client.put("/api/v1/progress/weight", json={"weight_kg": start - 3}, headers=auth_headers)
    after = client.get("/api/v1/dashboard/summary", headers=auth_headers).json()

    assert after["current_weight_kg"] == round(start - 3, 1)
    assert after["current_weight_kg"] != start


def test_weight_endpoints_require_auth(client):
    assert client.get("/api/v1/progress/weight").status_code == 401
    assert client.put("/api/v1/progress/weight", json={"weight_kg": 80}).status_code == 401


def _log_series(client, headers, weights):
    """Weigh in once a day, oldest first."""
    today = date.today()
    n = len(weights)
    for i, w in enumerate(weights):
        client.put(
            "/api/v1/progress/weight",
            json={"weight_kg": w, "date": (today - timedelta(days=n - 1 - i)).isoformat()},
            headers=headers,
        )


def test_weekly_review_reads_stored_weigh_ins(client, auth_headers, onboarded):
    """The client sends no history; the server supplies it from what it stored."""
    client.post("/api/v1/plans/generate", headers=auth_headers)
    _log_series(client, auth_headers, [84.0] * 14)          # flat = plateau
    for _ in range(14):
        client.put(
            "/api/v1/logs/today",
            json={"calories": 2000, "protein_g": 160, "steps": 9000, "workout_done": True},
            headers=auth_headers,
        )

    r = client.post("/api/v1/plans/weekly-review", json={"history": {}}, headers=auth_headers)
    assert r.status_code == 200
    final = r.json()["final"]
    assert "progress" in final["agents_used"], final["agents_used"]
    assert final["progress"] is not None
    # A flat 14-day series is the plateau signal; previously this was unreachable
    # because no weight history existed server-side at all.
    assert final["progress"]["slope_kg_per_week"] == 0.0


def test_weekly_review_still_honours_an_explicit_series(client, auth_headers, onboarded):
    client.post("/api/v1/plans/generate", headers=auth_headers)
    _log_series(client, auth_headers, [84.0] * 14)
    explicit = {"weight_series": [{"weight_kg": 84.0 - i * 0.2} for i in range(10)], "logs": []}
    r = client.post(
        "/api/v1/plans/weekly-review", json={"history": explicit}, headers=auth_headers
    )
    assert r.status_code == 200
    final = r.json()["final"]
    # Losing, not the flat stored series -> the explicit body still wins.
    assert final["progress"]["slope_kg_per_week"] < 0
