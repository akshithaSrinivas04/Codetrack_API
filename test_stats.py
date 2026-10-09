from conftest import submit


def test_summary_empty(client):
    s = client.get("/stats/summary").json()
    assert s["total_problems"] == 0 and s["acceptance_rate"] == 0.0


def test_summary_counts_and_acceptance_rate(client, seeded):
    a, b = seeded["Two Sum"], seeded["Merge Intervals"]
    submit(client, a, "wrong_answer", "2026-03-01T10:00:00")
    submit(client, a, "accepted", "2026-03-01T10:30:00")
    submit(client, b, "runtime_error", "2026-03-02T10:00:00")
    s = client.get("/stats/summary").json()
    assert s["total_problems"] == 3
    assert s["attempted"] == 2 and s["solved"] == 1
    assert s["total_submissions"] == 3
    assert s["acceptance_rate"] == 33.3
    assert s["by_difficulty"]["easy"] == {"total": 1, "solved": 1}
    assert s["by_difficulty"]["hard"] == {"total": 1, "solved": 0}


def test_topic_ranking(client, seeded):
    submit(client, seeded["Two Sum"], "accepted", "2026-03-01T10:00:00")
    submit(client, seeded["Merge Intervals"], "accepted", "2026-03-02T10:00:00")
    items = client.get("/stats/topics").json()["items"]
    assert items[0]["topic"] == "Arrays" and items[0]["rank"] == 1
    assert items[0]["solved"] == 2 and items[0]["pct_solved"] == 100.0
    assert items[1]["topic"] == "Design" and items[1]["solved"] == 0 and items[1]["rank"] == 2


def test_progress_counts_only_first_solve(client, seeded):
    a, b = seeded["Two Sum"], seeded["Merge Intervals"]
    submit(client, a, "accepted", "2026-03-01T10:00:00")
    submit(client, a, "accepted", "2026-03-02T10:00:00")  # re-solve: ignored
    submit(client, b, "accepted", "2026-03-02T12:00:00")
    items = client.get("/stats/progress").json()["items"]
    assert items == [
        {"date": "2026-03-01", "newly_solved": 1, "cumulative_solved": 1},
        {"date": "2026-03-02", "newly_solved": 1, "cumulative_solved": 2},
    ]


def test_streaks(client, seeded):
    p = seeded["Two Sum"]
    # Run of 3 days (Mar 1-3), gap, then run of 2 days (Mar 10-11)
    for day in ["2026-03-01", "2026-03-02", "2026-03-03", "2026-03-10", "2026-03-11"]:
        submit(client, p, "accepted", f"{day}T09:00:00")
    submit(client, p, "wrong_answer", "2026-03-05T09:00:00")  # failures never extend a streak
    s = client.get("/stats/streak?as_of=2026-03-11").json()
    assert s["longest_streak"] == 3 and s["current_streak"] == 2
    # Streak is still alive the day after the last solve, but broken after two days
    assert client.get("/stats/streak?as_of=2026-03-12").json()["current_streak"] == 2
    assert client.get("/stats/streak?as_of=2026-03-13").json()["current_streak"] == 0


def test_streak_empty(client):
    s = client.get("/stats/streak?as_of=2026-03-01").json()
    assert s["current_streak"] == 0 and s["longest_streak"] == 0
