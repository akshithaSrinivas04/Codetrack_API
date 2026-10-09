# CodeTrack API

A REST API to track coding-practice problems, submissions and progress, like a
personal HackerRank dashboard. Built with **FastAPI + SQLite** and covered by **20 pytest tests**.

## Features
- Full CRUD for problems (unique titles, filtering by difficulty/topic, pagination)
- Submissions with status, language and runtime; foreign keys + `ON DELETE CASCADE`
- Request validation (blank titles, bad enums, negative runtimes -> `422`), proper `404` / `409` errors
- SQL analytics endpoints:
  | Endpoint | SQL technique |
  |---|---|
  | `GET /stats/summary` | aggregation, `EXISTS` sub-query, acceptance rate |
  | `GET /stats/topics` | `LEFT JOIN` + CTE + `RANK() OVER (...)` |
  | `GET /stats/progress` | `ROW_NUMBER() OVER (PARTITION BY ...)` + running `SUM() OVER (...)` |
  | `GET /stats/streak` | "gaps and islands" with `ROW_NUMBER()` |

## Run it
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload        # docs at http://127.0.0.1:8000/docs
python -m pytest -q                  # 20 tests
```

## Try it
```bash
curl -X POST localhost:8000/problems -H "Content-Type: application/json" \
  -d '{"title":"Two Sum","difficulty":"easy","topic":"Arrays"}'

curl -X POST localhost:8000/submissions -H "Content-Type: application/json" \
  -d '{"problem_id":1,"status":"accepted","language":"python","runtime_ms":42}'

curl localhost:8000/stats/summary
curl "localhost:8000/stats/streak"
```

## Layout
```
app/main.py      routes + SQL queries
app/schemas.py   Pydantic validation models
app/db.py        schema + connection helper
tests/           problems, submissions and stats tests (temp DB per test)
```

## Design notes
- `create_app(db_path)` is an app factory, so every test gets its own throw-away database.
- Streak logic takes an optional `as_of` date, which makes time-based behaviour testable.
