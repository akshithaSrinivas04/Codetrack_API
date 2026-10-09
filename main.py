"""CodeTrack API: track coding-practice problems, submissions and progress."""
import sqlite3
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response

from .db import connect, init_db
from .schemas import Difficulty, ProblemIn, Status, SubmissionIn


def _get_problem(conn: sqlite3.Connection, problem_id: int) -> dict:
    row = conn.execute("SELECT * FROM problems WHERE id = ?", (problem_id,)).fetchone()
    if row is None:
        raise HTTPException(404, f"Problem {problem_id} not found")
    return dict(row)


def create_app(db_path: str = "codetrack.db") -> FastAPI:
    app = FastAPI(title="CodeTrack API", version="1.0.0")
    app.state.db_path = db_path
    init_db(db_path)

    def get_conn(request: Request):
        conn = connect(request.app.state.db_path)
        try:
            yield conn
        finally:
            conn.close()

    # ------------------------------------------------------------ problems
    @app.post("/problems", status_code=201)
    def create_problem(body: ProblemIn, conn: sqlite3.Connection = Depends(get_conn)):
        try:
            cur = conn.execute(
                "INSERT INTO problems (title, difficulty, topic) VALUES (?, ?, ?)",
                (body.title, body.difficulty.value, body.topic),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(409, f"Problem '{body.title}' already exists")
        return _get_problem(conn, cur.lastrowid)

    @app.get("/problems")
    def list_problems(
        difficulty: Optional[Difficulty] = None,
        topic: Optional[str] = None,
        limit: int = Query(20, ge=1, le=100),
        offset: int = Query(0, ge=0),
        conn: sqlite3.Connection = Depends(get_conn),
    ):
        where, params = [], []
        if difficulty:
            where.append("difficulty = ?")
            params.append(difficulty.value)
        if topic:
            where.append("LOWER(topic) = LOWER(?)")
            params.append(topic)
        clause = ("WHERE " + " AND ".join(where)) if where else ""
        total = conn.execute(f"SELECT COUNT(*) FROM problems {clause}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM problems {clause} ORDER BY id LIMIT ? OFFSET ?",
            [*params, limit, offset],
        ).fetchall()
        return {"total": total, "limit": limit, "offset": offset,
                "items": [dict(r) for r in rows]}

    @app.get("/problems/{problem_id}")
    def get_problem(problem_id: int, conn: sqlite3.Connection = Depends(get_conn)):
        return _get_problem(conn, problem_id)

    @app.put("/problems/{problem_id}")
    def update_problem(problem_id: int, body: ProblemIn,
                       conn: sqlite3.Connection = Depends(get_conn)):
        _get_problem(conn, problem_id)
        try:
            conn.execute(
                "UPDATE problems SET title = ?, difficulty = ?, topic = ? WHERE id = ?",
                (body.title, body.difficulty.value, body.topic, problem_id),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(409, f"Problem '{body.title}' already exists")
        return _get_problem(conn, problem_id)

    @app.delete("/problems/{problem_id}", status_code=204)
    def delete_problem(problem_id: int, conn: sqlite3.Connection = Depends(get_conn)):
        _get_problem(conn, problem_id)
        conn.execute("DELETE FROM problems WHERE id = ?", (problem_id,))
        conn.commit()
        return Response(status_code=204)

    # --------------------------------------------------------- submissions
    @app.post("/submissions", status_code=201)
    def create_submission(body: SubmissionIn, conn: sqlite3.Connection = Depends(get_conn)):
        _get_problem(conn, body.problem_id)  # 404 if the problem does not exist
        ts = body.submitted_at or datetime.now(timezone.utc)
        ts_text = ts.replace(tzinfo=None).isoformat(sep=" ", timespec="seconds")
        cur = conn.execute(
            "INSERT INTO submissions (problem_id, status, language, runtime_ms, submitted_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (body.problem_id, body.status.value, body.language.strip().lower(),
             body.runtime_ms, ts_text),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM submissions WHERE id = ?", (cur.lastrowid,)).fetchone()
        return dict(row)

    @app.get("/submissions")
    def list_submissions(
        problem_id: Optional[int] = None,
        status: Optional[Status] = None,
        limit: int = Query(20, ge=1, le=100),
        offset: int = Query(0, ge=0),
        conn: sqlite3.Connection = Depends(get_conn),
    ):
        where, params = [], []
        if problem_id is not None:
            where.append("problem_id = ?")
            params.append(problem_id)
        if status:
            where.append("status = ?")
            params.append(status.value)
        clause = ("WHERE " + " AND ".join(where)) if where else ""
        rows = conn.execute(
            f"SELECT * FROM submissions {clause} ORDER BY submitted_at DESC, id DESC "
            "LIMIT ? OFFSET ?",
            [*params, limit, offset],
        ).fetchall()
        return {"items": [dict(r) for r in rows]}

    # --------------------------------------------------------------- stats
    @app.get("/stats/summary")
    def summary(conn: sqlite3.Connection = Depends(get_conn)):
        total_problems = conn.execute("SELECT COUNT(*) FROM problems").fetchone()[0]
        sub = conn.execute(
            "SELECT COUNT(*) AS total, "
            "       COALESCE(SUM(status = 'accepted'), 0) AS accepted, "
            "       COUNT(DISTINCT problem_id) AS attempted "
            "FROM submissions"
        ).fetchone()
        solved = conn.execute(
            "SELECT COUNT(DISTINCT problem_id) FROM submissions WHERE status = 'accepted'"
        ).fetchone()[0]
        by_diff = conn.execute(
            "SELECT p.difficulty, COUNT(*) AS total, "
            "       SUM(EXISTS (SELECT 1 FROM submissions s "
            "                   WHERE s.problem_id = p.id AND s.status = 'accepted')) AS solved "
            "FROM problems p GROUP BY p.difficulty"
        ).fetchall()
        return {
            "total_problems": total_problems,
            "attempted": sub["attempted"],
            "solved": solved,
            "total_submissions": sub["total"],
            "acceptance_rate": round(100 * sub["accepted"] / sub["total"], 1) if sub["total"] else 0.0,
            "by_difficulty": {r["difficulty"]: {"total": r["total"], "solved": r["solved"]}
                              for r in by_diff},
        }

    @app.get("/stats/topics")
    def topics(conn: sqlite3.Connection = Depends(get_conn)):
        """Per-topic progress, ranked with the RANK() window function."""
        rows = conn.execute(
            """
            WITH per_topic AS (
                SELECT p.topic,
                       COUNT(DISTINCT p.id) AS total,
                       COUNT(DISTINCT CASE WHEN s.status = 'accepted' THEN p.id END) AS solved
                FROM problems p LEFT JOIN submissions s ON s.problem_id = p.id
                GROUP BY p.topic
            )
            SELECT topic, total, solved,
                   ROUND(100.0 * solved / total, 1) AS pct_solved,
                   RANK() OVER (ORDER BY solved DESC, topic) AS rank
            FROM per_topic ORDER BY rank
            """
        ).fetchall()
        return {"items": [dict(r) for r in rows]}

    @app.get("/stats/progress")
    def progress(conn: sqlite3.Connection = Depends(get_conn)):
        """Cumulative count of problems solved for the first time, per day."""
        rows = conn.execute(
            """
            WITH first_solves AS (
                SELECT date(submitted_at) AS d,
                       ROW_NUMBER() OVER (PARTITION BY problem_id
                                          ORDER BY submitted_at, id) AS rn
                FROM submissions WHERE status = 'accepted'
            ), daily AS (
                SELECT d, COUNT(*) AS newly_solved FROM first_solves WHERE rn = 1 GROUP BY d
            )
            SELECT d AS date, newly_solved,
                   SUM(newly_solved) OVER (ORDER BY d) AS cumulative_solved
            FROM daily ORDER BY d
            """
        ).fetchall()
        return {"items": [dict(r) for r in rows]}

    @app.get("/stats/streak")
    def streak(as_of: Optional[date] = None, conn: sqlite3.Connection = Depends(get_conn)):
        """Current/longest run of consecutive days with an accepted submission.

        Uses the 'gaps and islands' trick: day_number - ROW_NUMBER() is constant
        within a run of consecutive days.
        """
        runs = conn.execute(
            """
            WITH days AS (
                SELECT DISTINCT date(submitted_at) AS d FROM submissions
                WHERE status = 'accepted'
            ), grp AS (
                SELECT d, CAST(julianday(d) AS INTEGER) - ROW_NUMBER() OVER (ORDER BY d) AS g
                FROM days
            )
            SELECT MIN(d) AS start, MAX(d) AS end, COUNT(*) AS length
            FROM grp GROUP BY g ORDER BY start
            """
        ).fetchall()
        today = as_of or datetime.now(timezone.utc).date()
        longest = max((r["length"] for r in runs), default=0)
        current = 0
        for r in runs:
            end = date.fromisoformat(r["end"])
            start = date.fromisoformat(r["start"])
            # A streak is "alive" if it ended today or yesterday.
            if start <= today and end >= today - timedelta(days=1):
                current = r["length"]
        return {"current_streak": current, "longest_streak": longest, "as_of": today.isoformat()}

    return app


app = create_app()
