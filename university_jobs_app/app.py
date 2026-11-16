"""REST API for the University Job Opportunities Management System.

The API connects to the MySQL database university_jobs and offers
CRUD operations (Create, Read, Update, Delete) in JSON format.
The desktop GUI (gui.py) uses this API to read and change the data.

Run with:  python app.py   ->  http://localhost:5000
"""
import datetime

import mysql.connector
from mysql.connector import errorcode
from flask import Flask, jsonify, request

from config import DB_CONFIG

app = Flask(__name__)

# ------------------------------------------------------------
# Resources: one entry for each table with CRUD operations.
#   table    -> table name in MySQL
#   pk       -> primary key column
#   fields   -> columns that can be sent in POST / PUT
#   required -> columns that must be sent in POST
# ------------------------------------------------------------
RESOURCES = {
    "students": {
        "table": "student",
        "pk": "student_id",
        "fields": ["name", "last_name", "email", "academic_program"],
        "required": ["name", "last_name", "email", "academic_program"],
    },
    "companies": {
        "table": "company",
        "pk": "company_id",
        "fields": ["name", "email", "phone"],
        "required": ["name", "email"],
    },
    "skills": {
        "table": "skill",
        "pk": "skill_id",
        "fields": ["name", "description"],
        "required": ["name"],
    },
    "job-offers": {
        "table": "job_offer",
        "pk": "job_offer_id",
        "fields": ["company_id", "position", "description", "location", "requirements"],
        "required": ["company_id", "position"],
    },
    "applications": {
        "table": "application",
        "pk": "application_id",
        "fields": ["student_id", "job_offer_id", "application_date", "status", "comments"],
        "required": ["student_id", "job_offer_id", "application_date"],
    },
}

# MySQL error codes translated into HTTP responses.
# 4025 is the CHECK error code of MariaDB (MySQL uses 3819).
DB_ERRORS = {
    errorcode.ER_DUP_ENTRY: (409, "The value already exists (UNIQUE constraint)."),
    errorcode.ER_NO_REFERENCED_ROW_2: (400, "The referenced record does not exist (FOREIGN KEY constraint)."),
    errorcode.ER_ROW_IS_REFERENCED_2: (409, "The record has related records and cannot be deleted (FOREIGN KEY constraint)."),
    errorcode.ER_BAD_NULL_ERROR: (400, "A required field is empty (NOT NULL constraint)."),
    3819: (400, "The value is not allowed (CHECK constraint)."),
    4025: (400, "The value is not allowed (CHECK constraint)."),
}


# ------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------
def get_connection():
    """Open a new connection to the MySQL database."""
    return mysql.connector.connect(**DB_CONFIG)


def to_json(row):
    """Convert dates to text so they can be sent as JSON."""
    return {
        key: value.isoformat() if isinstance(value, (datetime.date, datetime.datetime)) else value
        for key, value in row.items()
    }


def run_query(sql, params=(), fetch="all"):
    """Execute a SQL statement.

    fetch = "all"  -> returns a list of rows
    fetch = "one"  -> returns one row or None
    fetch = None   -> commits the change and returns (lastrowid, rowcount)
    """
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params)
        if fetch == "all":
            return [to_json(r) for r in cursor.fetchall()]
        if fetch == "one":
            row = cursor.fetchone()
            return to_json(row) if row else None
        conn.commit()
        return cursor.lastrowid, cursor.rowcount
    finally:
        conn.close()


def error(status, message):
    return jsonify({"error": message}), status


@app.errorhandler(mysql.connector.Error)
def handle_db_error(exc):
    """Translate MySQL errors into clear JSON messages."""
    status, message = DB_ERRORS.get(exc.errno, (500, "Database error."))
    return jsonify({"error": message, "mysql_error": exc.errno}), status


# ------------------------------------------------------------
# Generic CRUD endpoints:  /api/<resource>  and  /api/<resource>/<id>
# ------------------------------------------------------------
def get_resource(name):
    return RESOURCES.get(name)


@app.route("/api/<resource>", methods=["GET"])
def list_items(resource):
    """READ all records of a table."""
    res = get_resource(resource)
    if not res:
        return error(404, "Resource not found.")
    rows = run_query(f"SELECT * FROM {res['table']} ORDER BY {res['pk']}")
    return jsonify(rows)


@app.route("/api/<resource>/<int:item_id>", methods=["GET"])
def get_item(resource, item_id):
    """READ one record by its primary key."""
    res = get_resource(resource)
    if not res:
        return error(404, "Resource not found.")
    row = run_query(f"SELECT * FROM {res['table']} WHERE {res['pk']} = %s", (item_id,), fetch="one")
    if row is None:
        return error(404, f"{res['table']} {item_id} does not exist.")
    return jsonify(row)


@app.route("/api/<resource>", methods=["POST"])
def create_item(resource):
    """CREATE a new record."""
    res = get_resource(resource)
    if not res:
        return error(404, "Resource not found.")
    data = request.get_json(silent=True) or {}
    missing = [f for f in res["required"] if data.get(f) in (None, "")]
    if missing:
        return error(400, "Missing required fields: " + ", ".join(missing))

    columns = [f for f in res["fields"] if f in data]
    values = [data[c] for c in columns]
    placeholders = ", ".join(["%s"] * len(columns))
    sql = f"INSERT INTO {res['table']} ({', '.join(columns)}) VALUES ({placeholders})"
    new_id, _ = run_query(sql, values, fetch=None)

    row = run_query(f"SELECT * FROM {res['table']} WHERE {res['pk']} = %s", (new_id,), fetch="one")
    return jsonify(row), 201


@app.route("/api/<resource>/<int:item_id>", methods=["PUT"])
def update_item(resource, item_id):
    """UPDATE one or more columns of a record."""
    res = get_resource(resource)
    if not res:
        return error(404, "Resource not found.")
    data = request.get_json(silent=True) or {}
    columns = [f for f in res["fields"] if f in data]
    if not columns:
        return error(400, "No fields to update.")

    exists = run_query(f"SELECT {res['pk']} FROM {res['table']} WHERE {res['pk']} = %s", (item_id,), fetch="one")
    if exists is None:
        return error(404, f"{res['table']} {item_id} does not exist.")

    assignments = ", ".join(f"{c} = %s" for c in columns)
    values = [data[c] for c in columns] + [item_id]
    run_query(f"UPDATE {res['table']} SET {assignments} WHERE {res['pk']} = %s", values, fetch=None)

    row = run_query(f"SELECT * FROM {res['table']} WHERE {res['pk']} = %s", (item_id,), fetch="one")
    return jsonify(row)


@app.route("/api/<resource>/<int:item_id>", methods=["DELETE"])
def delete_item(resource, item_id):
    """DELETE a record."""
    res = get_resource(resource)
    if not res:
        return error(404, "Resource not found.")
    _, deleted = run_query(f"DELETE FROM {res['table']} WHERE {res['pk']} = %s", (item_id,), fetch=None)
    if deleted == 0:
        return error(404, f"{res['table']} {item_id} does not exist.")
    return jsonify({"message": f"{res['table']} {item_id} deleted."})


# ------------------------------------------------------------
# Queries of FR-05 (read with INNER JOIN)
# ------------------------------------------------------------
@app.route("/api/companies/<int:company_id>/job-offers", methods=["GET"])
def company_job_offers(company_id):
    """Job offers published by a company."""
    rows = run_query(
        """SELECT j.job_offer_id, j.position, j.location, c.name AS company
           FROM job_offer AS j
           INNER JOIN company AS c ON j.company_id = c.company_id
           WHERE c.company_id = %s
           ORDER BY j.job_offer_id""",
        (company_id,),
    )
    return jsonify(rows)


@app.route("/api/job-offers/<int:job_offer_id>/skills", methods=["GET"])
def job_offer_skills(job_offer_id):
    """Skills required by a job offer."""
    rows = run_query(
        """SELECT sk.skill_id, sk.name
           FROM job_offer_skill AS js
           INNER JOIN skill AS sk ON js.skill_id = sk.skill_id
           WHERE js.job_offer_id = %s
           ORDER BY sk.skill_id""",
        (job_offer_id,),
    )
    return jsonify(rows)


@app.route("/api/students/<int:student_id>/skills", methods=["GET"])
def student_skills(student_id):
    """Skills of a student."""
    rows = run_query(
        """SELECT sk.skill_id, sk.name
           FROM student_skill AS ss
           INNER JOIN skill AS sk ON ss.skill_id = sk.skill_id
           WHERE ss.student_id = %s
           ORDER BY sk.skill_id""",
        (student_id,),
    )
    return jsonify(rows)


@app.route("/api/students/<int:student_id>/applications", methods=["GET"])
def student_applications(student_id):
    """Applications submitted by a student."""
    rows = run_query(
        """SELECT a.application_id, j.position, a.application_date, a.status
           FROM application AS a
           INNER JOIN job_offer AS j ON a.job_offer_id = j.job_offer_id
           WHERE a.student_id = %s
           ORDER BY a.application_date""",
        (student_id,),
    )
    return jsonify(rows)


@app.route("/api/applications/details", methods=["GET"])
def application_details():
    """All applications with the student name and the position (used by the GUI)."""
    rows = run_query(
        """SELECT a.application_id, a.application_date, a.status, a.comments,
                  s.student_id, CONCAT(s.name, ' ', s.last_name) AS student,
                  j.job_offer_id, j.position, c.name AS company
           FROM application AS a
           INNER JOIN student AS s   ON a.student_id = s.student_id
           INNER JOIN job_offer AS j ON a.job_offer_id = j.job_offer_id
           INNER JOIN company AS c   ON j.company_id = c.company_id
           ORDER BY a.application_id"""
    )
    return jsonify(rows)


@app.route("/")
def index():
    """Basic information about the API."""
    return jsonify({"api": "University Job Opportunities Management System",
                    "resources": ["/api/" + name for name in RESOURCES]})


if __name__ == "__main__":
    app.run(debug=True)
