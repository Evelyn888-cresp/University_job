"""API test cases (CRUD operations).

Run with:  python -m pytest -v
"""

NEW_STUDENT = {
    "name": "Andrea",
    "last_name": "Ruiz",
    "email": "andrea.ruiz@example.com",
    "academic_program": "Biology",
}


# ---------------- READ ----------------
def test_api_01_list_students(client):
    response = client.get("/api/students")
    assert response.status_code == 200
    assert len(response.get_json()) == 3


def test_api_02_get_one_student(client):
    response = client.get("/api/students/1")
    assert response.status_code == 200
    assert response.get_json()["name"] == "Evelyn"


def test_api_03_get_missing_student(client):
    response = client.get("/api/students/99")
    assert response.status_code == 404


# ---------------- CREATE ----------------
def test_api_04_create_student(client):
    response = client.post("/api/students", json=NEW_STUDENT)
    assert response.status_code == 201
    assert response.get_json()["student_id"] == 4


def test_api_05_create_student_missing_fields(client):
    response = client.post("/api/students", json={"name": "Andrea"})
    assert response.status_code == 400


def test_api_06_create_student_duplicate_email(client):
    data = dict(NEW_STUDENT, email="evelyn.crespo@example.com")
    response = client.post("/api/students", json=data)
    assert response.status_code == 409


def test_api_07_create_job_offer_missing_company(client):
    response = client.post("/api/job-offers", json={"company_id": 99, "position": "Analyst"})
    assert response.status_code == 400


def test_api_08_create_application_default_status(client):
    data = {"student_id": 2, "job_offer_id": 1, "application_date": "2026-11-15"}
    response = client.post("/api/applications", json=data)
    assert response.status_code == 201
    assert response.get_json()["status"] == "Pending"


def test_api_09_create_duplicate_application(client):
    data = {"student_id": 1, "job_offer_id": 1, "application_date": "2026-11-15"}
    response = client.post("/api/applications", json=data)
    assert response.status_code == 409


def test_api_10_create_application_invalid_status(client):
    data = {"student_id": 1, "job_offer_id": 2, "application_date": "2026-11-15", "status": "Approved"}
    response = client.post("/api/applications", json=data)
    assert response.status_code == 400


def test_api_11_create_duplicate_skill(client):
    response = client.post("/api/skills", json={"name": "Python"})
    assert response.status_code == 409


# ---------------- UPDATE ----------------
def test_api_12_update_student(client):
    response = client.put("/api/students/2", json={"academic_program": "Computer Science"})
    assert response.status_code == 200
    assert response.get_json()["academic_program"] == "Computer Science"


def test_api_13_update_application_status(client):
    response = client.put("/api/applications/2", json={"status": "Under Review"})
    assert response.status_code == 200
    assert response.get_json()["status"] == "Under Review"


def test_api_14_update_company_phone(client):
    response = client.put("/api/companies/2", json={"phone": "0999999999"})
    assert response.status_code == 200
    assert response.get_json()["phone"] == "0999999999"


def test_api_15_update_missing_student(client):
    response = client.put("/api/students/99", json={"name": "Nobody"})
    assert response.status_code == 404


# ---------------- DELETE ----------------
def test_api_16_delete_student_without_dependencies(client):
    new_id = client.post("/api/students", json=NEW_STUDENT).get_json()["student_id"]
    response = client.delete(f"/api/students/{new_id}")
    assert response.status_code == 200
    assert client.get(f"/api/students/{new_id}").status_code == 404


def test_api_17_delete_student_with_application(client):
    response = client.delete("/api/students/1")
    assert response.status_code == 409


def test_api_18_delete_company_with_job_offers(client):
    response = client.delete("/api/companies/1")
    assert response.status_code == 409


# ---------------- QUERIES (FR-05) ----------------
def test_api_19_company_job_offers(client):
    rows = client.get("/api/companies/1/job-offers").get_json()
    assert [r["position"] for r in rows] == ["Junior Python Developer", "Software Engineer"]


def test_api_20_job_offer_skills(client):
    rows = client.get("/api/job-offers/1/skills").get_json()
    assert [r["name"] for r in rows] == ["Python", "SQL"]


def test_api_21_student_applications(client):
    rows = client.get("/api/students/1/applications").get_json()
    assert rows[0]["position"] == "Junior Python Developer"
    assert rows[0]["status"] == "Under Review"
