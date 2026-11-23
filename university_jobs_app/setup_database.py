"""Create the database university_jobs and load the sample data.

Run:  python setup_database.py

It uses the connection settings of config.py (and the environment
variables DB_HOST, DB_PORT, DB_USER, DB_PASSWORD). The database
university_jobs is deleted and created again with:
  - database/schema.sql       (the 7 tables)
  - database/sample_data.sql  (the 30 sample records)
"""
import pathlib
import sys

import mysql.connector

from config import DB_CONFIG

DATABASE_DIR = pathlib.Path(__file__).resolve().parent / "database"


def run_sql_file(cursor, path):
    """Execute every statement of a .sql file."""
    for statement in path.read_text(encoding="utf-8").split(";"):
        lines = [l for l in statement.splitlines() if not l.strip().startswith("--")]
        sql = "\n".join(lines).strip()
        if sql:
            cursor.execute(sql)


def main():
    name = DB_CONFIG["database"]
    if "--yes" not in sys.argv:
        answer = input(f"This deletes the database '{name}' and creates it again with the sample data. Continue? (y/n) ")
        if answer.strip().lower() != "y":
            print("Cancelled.")
            return

    settings = {k: v for k, v in DB_CONFIG.items() if k != "database"}
    try:
        conn = mysql.connector.connect(**settings)
    except mysql.connector.Error as exc:
        print(f"Could not connect to MySQL: {exc}")
        print("Check that the MySQL container is running and that DB_PASSWORD is correct.")
        return

    cursor = conn.cursor()
    cursor.execute(f"DROP DATABASE IF EXISTS {name}")
    cursor.execute(f"CREATE DATABASE {name}")
    cursor.execute(f"USE {name}")
    run_sql_file(cursor, DATABASE_DIR / "schema.sql")
    run_sql_file(cursor, DATABASE_DIR / "sample_data.sql")
    conn.commit()

    print(f"Database '{name}' created. Records per table:")
    for table in ("student", "company", "skill", "job_offer", "application", "student_skill", "job_offer_skill"):
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        print(f"  {table:<16} {cursor.fetchone()[0]}")
    conn.close()


if __name__ == "__main__":
    main()
