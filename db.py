"""SQLite helpers: schema creation and per-request connections."""
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS problems (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL UNIQUE,
    difficulty  TEXT NOT NULL CHECK (difficulty IN ('easy', 'medium', 'hard')),
    topic       TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS submissions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    problem_id    INTEGER NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    status        TEXT NOT NULL CHECK (status IN
                    ('accepted', 'wrong_answer', 'time_limit', 'runtime_error')),
    language      TEXT NOT NULL,
    runtime_ms    INTEGER CHECK (runtime_ms IS NULL OR runtime_ms >= 0),
    submitted_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_submissions_problem ON submissions(problem_id);
CREATE INDEX IF NOT EXISTS idx_submissions_status_date ON submissions(status, submitted_at);
"""


def init_db(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
