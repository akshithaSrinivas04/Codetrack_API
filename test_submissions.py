from conftest import submit


def test_submission_requires_existing_problem(client):
    r = client.post("/submissions", json={"problem_id": 42, "status": "accepted", "language": "python"})
    assert r.status_code == 404


def test_submission_validation(client, seeded):
    pid = seeded["Two Sum"]
    bad_status = client.post("/submissions", json={"problem_id": pid, "status": "great", "language": "py"})
    neg_runtime = client.post("/submissions", json={"problem_id": pid, "status": "accepted",
                                                    "language": "py", "runtime_ms": -5})
    assert bad_status.status_code == 422 and neg_runtime.status_code == 422


def test_language_is_normalised(client, seeded):
    r = client.post("/submissions", json={"problem_id": seeded["Two Sum"], "status": "accepted",
                                          "language": " Python "})
    assert r.json()["language"] == "python"


def test_filter_submissions(client, seeded):
    a, b = seeded["Two Sum"], seeded["LRU Cache"]
    submit(client, a, "wrong_answer", "2026-03-01T10:00:00")
    submit(client, a, "accepted", "2026-03-01T11:00:00")
    submit(client, b, "time_limit", "2026-03-02T09:00:00")
    assert len(client.get(f"/submissions?problem_id={a}").json()["items"]) == 2
    assert len(client.get("/submissions?status=accepted").json()["items"]) == 1
    newest = client.get("/submissions").json()["items"][0]
    assert newest["problem_id"] == b  # ordered newest first
