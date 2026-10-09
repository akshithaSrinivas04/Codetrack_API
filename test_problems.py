def test_create_and_get_problem(client):
    r = client.post("/problems", json={"title": "  Two Sum ", "difficulty": "easy", "topic": "Arrays"})
    assert r.status_code == 201
    body = r.json()
    assert body["title"] == "Two Sum"  # whitespace stripped
    assert client.get(f"/problems/{body['id']}").json()["topic"] == "Arrays"


def test_duplicate_title_conflict(client):
    payload = {"title": "Two Sum", "difficulty": "easy", "topic": "Arrays"}
    assert client.post("/problems", json=payload).status_code == 201
    assert client.post("/problems", json=payload).status_code == 409


def test_invalid_difficulty_rejected(client):
    r = client.post("/problems", json={"title": "X", "difficulty": "impossible", "topic": "T"})
    assert r.status_code == 422


def test_blank_title_rejected(client):
    r = client.post("/problems", json={"title": "   ", "difficulty": "easy", "topic": "T"})
    assert r.status_code == 422


def test_get_missing_problem_404(client):
    assert client.get("/problems/999").status_code == 404


def test_list_filter_and_pagination(client, seeded):
    assert client.get("/problems").json()["total"] == 3
    assert client.get("/problems?difficulty=easy").json()["total"] == 1
    assert client.get("/problems?topic=arrays").json()["total"] == 2  # case-insensitive
    page = client.get("/problems?limit=2&offset=2").json()
    assert page["total"] == 3 and len(page["items"]) == 1


def test_limit_out_of_range_rejected(client):
    assert client.get("/problems?limit=0").status_code == 422
    assert client.get("/problems?limit=101").status_code == 422


def test_update_problem(client, seeded):
    pid = seeded["Two Sum"]
    r = client.put(f"/problems/{pid}", json={"title": "Two Sum II", "difficulty": "medium", "topic": "Arrays"})
    assert r.status_code == 200 and r.json()["difficulty"] == "medium"


def test_update_to_existing_title_conflict(client, seeded):
    r = client.put(f"/problems/{seeded['Two Sum']}",
                   json={"title": "LRU Cache", "difficulty": "easy", "topic": "Arrays"})
    assert r.status_code == 409


def test_delete_cascades_submissions(client, seeded):
    pid = seeded["Two Sum"]
    client.post("/submissions", json={"problem_id": pid, "status": "accepted", "language": "python"})
    assert client.delete(f"/problems/{pid}").status_code == 204
    assert client.get(f"/problems/{pid}").status_code == 404
    assert client.get("/submissions").json()["items"] == []
