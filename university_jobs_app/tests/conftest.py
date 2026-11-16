"""Test setup.

Each test runs on a fresh copy of the database called
university_jobs_test, created from database/schema.sql and
database/sample_data.sql. The real database is not modified.
"""
import os
import pathlib

import mysql.connector
import pytest

os.environ.setdefault("DB_NAME", "university_jobs_test")

from config import DB_CONFIG  # noqa: E402
from app import app  # noqa: E402

DATABASE_DIR = pathlib.Path(__file__).resolve().parent.parent / "database"


def run_sql_file(cursor, path):
    for statement in path.read_text().split(";"):
        lines = [l for l in statement.splitlines() if not l.strip().startswith("--")]
        sql = "\n".join(lines).strip()
        if sql:
            cursor.execute(sql)


@pytest.fixture()
def client():
    settings = {k: v for k, v in DB_CONFIG.items() if k != "database"}
    name = DB_CONFIG["database"]
    conn = mysql.connector.connect(**settings)
    cursor = conn.cursor()
    cursor.execute(f"DROP DATABASE IF EXISTS {name}")
    cursor.execute(f"CREATE DATABASE {name}")
    cursor.execute(f"USE {name}")
    run_sql_file(cursor, DATABASE_DIR / "schema.sql")
    run_sql_file(cursor, DATABASE_DIR / "sample_data.sql")
    conn.commit()
    conn.close()

    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client
