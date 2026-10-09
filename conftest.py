import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(str(tmp_path / "test.db")))


@pytest.fixture
def seeded(client):
    """Three problems across two topics."""
    ids = {}
    for title, diff, topic in [
        ("Two Sum", "easy", "Arrays"),
        ("Merge Intervals", "medium", "Arrays"),
        ("LRU Cache", "hard", "Design"),
    ]:
        ids[title] = client.post("/problems", json={
            "title": title, "difficulty": diff, "topic": topic}).json()["id"]
    return ids


def submit(client, pid, status, ts, lang="python", runtime=10):
    return client.post("/submissions", json={
        "problem_id": pid, "status": status, "language": lang,
        "runtime_ms": runtime, "submitted_at": ts})
