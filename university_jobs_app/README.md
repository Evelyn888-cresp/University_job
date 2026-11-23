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
├── app.py               # Flask API (CRUD, skills, and queries)
├── gui.py               # Tkinter GUI connected to the API
├── config.py            # MySQL connection settings
├── setup_database.py    # creates the database and loads the sample data
├── requirements.txt
├── pytest.ini
├── database/
│   ├── schema.sql       # CREATE TABLE statements (7 tables)
│   └── sample_data.sql  # 30 sample records
└── tests/
    ├── conftest.py      # creates a fresh test database for each test
    ├── test_data.sql    # fixed data used only by the tests
    └── test_api.py      # 28 API test cases
```

## How to run (Windows PowerShell)

1. Start MySQL (for example, `docker start mysqlcontainer8`).
2. Install the libraries:
   ```
   pip install -r requirements.txt
   ```
3. Give the program your MySQL password (it is not saved in any file):
   ```
   $env:DB_HOST="127.0.0.1"
   $env:DB_PASSWORD="your_password"
   ```
4. Create the database with the sample data:
   ```
   python setup_database.py
   ```
5. Run the tests:
   ```
   python -m pytest -v
   ```
6. Start the API (leave this terminal open):
   ```
   python app.py
   ```
7. In a second terminal, start the GUI:
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

Skills of students and job offers (tables `student_skill` and `job_offer_skill`):

| Method | Endpoint | Operation |
|---|---|---|
| GET | `/api/students/<id>/skills` | Skills of a student |
| POST | `/api/students/<id>/skills` | Assign a skill: `{"skill_id": 1}` |
| DELETE | `/api/students/<id>/skills/<skill_id>` | Remove a skill from a student |
| GET | `/api/job-offers/<id>/skills` | Skills required by a job offer |
| POST | `/api/job-offers/<id>/skills` | Add a required skill: `{"skill_id": 1}` |
| DELETE | `/api/job-offers/<id>/skills/<skill_id>` | Remove a required skill |

The rows of these two tables only hold two keys, so they are created and
deleted but not updated.

Queries (INNER JOIN):

| Method | Endpoint | Returns |
|---|---|---|
| GET | `/api/companies/<id>/job-offers` | Job offers of a company |
| GET | `/api/students/<id>/applications` | Applications of a student |
| GET | `/api/applications/details` | Applications with student, position, and company |
| GET | `/api/job-offers/<id>/candidates` | Students who have the skills a job offer requires, best match first |
| GET | `/api/summary` | Number of records in the main tables |

### Error responses

| MySQL error | HTTP status | Meaning |
|---|---|---|
| 1062 | 409 | The value already exists (UNIQUE) |
| 1452 | 400 | The referenced record does not exist (FOREIGN KEY) |
| 1451 | 409 | The record has related records (FOREIGN KEY) |
| 1048 | 400 | A required field is empty (NOT NULL) |
| 3819 | 400 | The value is not allowed (CHECK) |

Missing records return 404, and missing required fields return 400.

## GUI

| Tab | Functions |
|---|---|
| Students | Search, create, edit, delete; profile card; assign and remove skills |
| Job offers | Create, edit, delete; required skills; matching candidates |
| Applications | Create, change status, delete; rows colored by status |
| Companies | Create, edit, delete |
| Skills | Create, edit, delete |

The header shows the number of records of each table.

## Tests

The tests use a separate database, `university_jobs_test`, which is
created again before each test from `database/schema.sql` and
`tests/test_data.sql`. The real database is not modified.

```
python -m pytest -v
```
