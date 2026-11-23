"""REST API for the University Job Opportunities Management System.

The API connects to the MySQL database university_jobs and offers
CRUD operations (Create, Read, Update, Delete) in JSON format.
The desktop GUI (gui.py) uses this API to read and change the data.

Run with:  python app.py   ->  http://localhost:5000
"""
import datetime
import decimal

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
    """Convert dates to text and decimals to numbers so they can be sent as JSON."""
    result = {}
    for key, value in row.items():
        if isinstance(value, (datetime.date, datetime.datetime)):
            value = value.isoformat()
        elif isinstance(value, decimal.Decimal):
            value = float(value)
        result[key] = value
    return result


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


# ------------------------------------------------------------
# Skills of students and job offers (associative tables)
#   student_skill    ->  /api/students/<id>/skills
#   job_offer_skill  ->  /api/job-offers/<id>/skills
# ------------------------------------------------------------
SKILL_LINKS = {
    "students": {"table": "student_skill", "owner_key": "student_id", "owner_table": "student"},
    "job-offers": {"table": "job_offer_skill", "owner_key": "job_offer_id", "owner_table": "job_offer"},
}


def linked_skills(link, owner_id):
    """Skill names linked to one student or one job offer (INNER JOIN)."""
    return run_query(
        f"""SELECT sk.skill_id, sk.name
            FROM {link['table']} AS l
            INNER JOIN skill AS sk ON l.skill_id = sk.skill_id
            WHERE l.{link['owner_key']} = %s
            ORDER BY sk.name""",
        (owner_id,),
    )


@app.route("/api/<owner>/<int:owner_id>/skills", methods=["GET"])
def list_linked_skills(owner, owner_id):
    """READ the skills of a student or the skills required by a job offer."""
    link = SKILL_LINKS.get(owner)
    if not link:
        return error(404, "Resource not found.")
    return jsonify(linked_skills(link, owner_id))


@app.route("/api/<owner>/<int:owner_id>/skills", methods=["POST"])
def add_linked_skill(owner, owner_id):
    """CREATE: assign a skill to a student or to a job offer."""
    link = SKILL_LINKS.get(owner)
    if not link:
        return error(404, "Resource not found.")
    data = request.get_json(silent=True) or {}
    if data.get("skill_id") in (None, ""):
        return error(400, "Missing required fields: skill_id")
    exists = run_query(
        f"SELECT {link['owner_key']} FROM {link['owner_table']} WHERE {link['owner_key']} = %s",
        (owner_id,), fetch="one",
    )
    if exists is None:
        return error(404, f"{link['owner_table']} {owner_id} does not exist.")
    run_query(
        f"INSERT INTO {link['table']} ({link['owner_key']}, skill_id) VALUES (%s, %s)",
        (owner_id, data["skill_id"]), fetch=None,
    )
    return jsonify(linked_skills(link, owner_id)), 201


@app.route("/api/<owner>/<int:owner_id>/skills/<int:skill_id>", methods=["DELETE"])
def remove_linked_skill(owner, owner_id, skill_id):
    """DELETE: remove a skill from a student or from a job offer."""
    link = SKILL_LINKS.get(owner)
    if not link:
        return error(404, "Resource not found.")
    _, deleted = run_query(
        f"DELETE FROM {link['table']} WHERE {link['owner_key']} = %s AND skill_id = %s",
        (owner_id, skill_id), fetch=None,
    )
    if deleted == 0:
        return error(404, "That skill is not assigned.")
    return jsonify({"message": "Skill removed."})


@app.route("/api/job-offers/<int:job_offer_id>/candidates", methods=["GET"])
def job_offer_candidates(job_offer_id):
    """Students who have at least one skill required by a job offer,
    ordered by the number of matching skills."""
    rows = run_query(
        """SELECT s.student_id,
                  CONCAT(s.name, ' ', s.last_name) AS student,
                  COUNT(*) AS matching_skills,
                  (SELECT COUNT(*) FROM job_offer_skill WHERE job_offer_id = %s) AS required_skills,
                  GROUP_CONCAT(sk.name ORDER BY sk.name SEPARATOR ', ') AS skills
           FROM student AS s
           INNER JOIN student_skill AS ss ON s.student_id = ss.student_id
           INNER JOIN job_offer_skill AS js ON ss.skill_id = js.skill_id
           INNER JOIN skill AS sk ON ss.skill_id = sk.skill_id
           WHERE js.job_offer_id = %s
           GROUP BY s.student_id, s.name, s.last_name
           ORDER BY matching_skills DESC, s.student_id""",
        (job_offer_id, job_offer_id),
    )
    # For each candidate, list the required skills the student does not have yet
    required = [skill["name"] for skill in linked_skills(SKILL_LINKS["job-offers"], job_offer_id)]
    for row in rows:
        has = row["skills"].split(", ")
        row["missing"] = ", ".join(name for name in required if name not in has)
    return jsonify(rows)


@app.route("/api/skills/<int:skill_id>/students", methods=["GET"])
def skill_students(skill_id):
    """Students who have a skill (student_skill + student)."""
    rows = run_query(
        """SELECT st.student_id, CONCAT(st.name, ' ', st.last_name) AS student
           FROM student_skill AS ss
           INNER JOIN student AS st ON ss.student_id = st.student_id
           WHERE ss.skill_id = %s
           ORDER BY st.student_id""",
        (skill_id,),
    )
    return jsonify(rows)


@app.route("/api/skills/<int:skill_id>/job-offers", methods=["GET"])
def skill_job_offers(skill_id):
    """Job offers that require a skill (job_offer_skill + job_offer + company)."""
    rows = run_query(
        """SELECT jo.job_offer_id, jo.position, c.name AS company
           FROM job_offer_skill AS js
           INNER JOIN job_offer AS jo ON js.job_offer_id = jo.job_offer_id
           INNER JOIN company AS c ON jo.company_id = c.company_id
           WHERE js.skill_id = %s
           ORDER BY jo.job_offer_id""",
        (skill_id,),
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


@app.route("/api/summary", methods=["GET"])
def summary():
    """Number of records in the main tables (used by the GUI header)."""
    row = run_query(
        """SELECT (SELECT COUNT(*) FROM student) AS students,
                  (SELECT COUNT(*) FROM company) AS companies,
                  (SELECT COUNT(*) FROM job_offer) AS job_offers,
                  (SELECT COUNT(*) FROM application) AS applications,
                  (SELECT COUNT(*) FROM skill) AS skills""",
        fetch="one",
    )
    return jsonify(row)


@app.route("/")
def index():
    """Basic information about the API."""
    return jsonify({"api": "University Job Opportunities Management System",
                    "resources": ["/api/" + name for name in RESOURCES]})


if __name__ == "__main__":
    app.run(debug=True)