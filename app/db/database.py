import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "resilience.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    with open(SCHEMA_PATH, "r") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")


if __name__ == "__main__":
    init_db()