# University Job Opportunities Management System

Relational database, REST API, and desktop GUI for managing job
opportunities for university students.

| Layer | Technology | File |
|---|---|---|
| Database | MySQL (`university_jobs`) | `database/schema.sql`, `database/sample_data.sql` |
| API | Python + Flask | `app.py` |
| GUI | Python + Tkinter | `gui.py` |
| Tests | pytest | `tests/test_api.py` |

```
GUI (gui.py)  --HTTP/JSON-->  API (app.py)  --SQL-->  MySQL (university_jobs)
```

The GUI never connects to MySQL directly: every action is sent to the API.

## Project structure

```
university_jobs_app/
├── app.py               # Flask API (CRUD + queries)
├── gui.py               # Tkinter GUI connected to the API
├── config.py            # MySQL connection settings
├── requirements.txt
├── pytest.ini
├── database/
│   ├── schema.sql       # CREATE TABLE statements (7 tables)
│   └── sample_data.sql  # 30 sample records
└── tests/
    ├── conftest.py      # creates a fresh test database for each test
    └── test_api.py      # 21 API test cases
```

## How to run

1. Install the dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Create the database in MySQL (skip this step if `university_jobs` already exists):
   ```
   CREATE DATABASE university_jobs;
   USE university_jobs;
   SOURCE database/schema.sql;
   SOURCE database/sample_data.sql;
   ```
3. Write your MySQL user and password in `config.py`, or set the
   environment variables `DB_USER` and `DB_PASSWORD`.
4. Start the API:
   ```
   python app.py
   ```
   The API runs at `http://localhost:5000`.
5. In another terminal, start the GUI:
   ```
   python gui.py
   ```

## API endpoints

The same five CRUD operations are available for each resource:
`students`, `companies`, `skills`, `job-offers`, and `applications`.

| Method | Endpoint | Operation |
|---|---|---|
| GET | `/api/<resource>` | Read all records |
| GET | `/api/<resource>/<id>` | Read one record |
| POST | `/api/<resource>` | Create a record |
| PUT | `/api/<resource>/<id>` | Update a record |
| DELETE | `/api/<resource>/<id>` | Delete a record |

Queries (INNER JOIN):

| Method | Endpoint | Returns |
|---|---|---|
| GET | `/api/companies/<id>/job-offers` | Job offers of a company |
| GET | `/api/job-offers/<id>/skills` | Skills required by a job offer |
| GET | `/api/students/<id>/skills` | Skills of a student |
| GET | `/api/students/<id>/applications` | Applications of a student |
| GET | `/api/applications/details` | Applications with student, position, and company |

Example:

```
POST /api/students
{"name": "Andrea", "last_name": "Ruiz",
 "email": "andrea.ruiz@example.com", "academic_program": "Biology"}
```

### Error responses

MySQL constraint errors are returned as JSON with a clear message:

| MySQL error | HTTP status | Meaning |
|---|---|---|
| 1062 | 409 | The value already exists (UNIQUE) |
| 1452 | 400 | The referenced record does not exist (FOREIGN KEY) |
| 1451 | 409 | The record has related records (FOREIGN KEY) |
| 1048 | 400 | A required field is empty (NOT NULL) |
| 3819 | 400 | The value is not allowed (CHECK) |

Missing records return 404, and missing required fields return 400.

## Progress of this stage

| Component | Implemented | Pending |
|---|---|---|
| API CRUD | Full CRUD for `student`, `company`, `skill`, `job_offer`, and `application` (20 of 28 operations, 71%), plus 5 query endpoints | CRUD for `student_skill` and `job_offer_skill` |
| GUI | Students: create, read, update, delete. Applications: create, read, update status, delete. Companies and job offers: read (10 of 20 API operations, 50%) | Editing companies, job offers, and skills |

## Tests

The tests use a separate database, `university_jobs_test`, which is
created again before each test from `database/schema.sql` and
`database/sample_data.sql`. The real database is not modified.

```
python -m pytest -v
```
