-- University Job Opportunities Management System
-- Database schema (MySQL)

CREATE TABLE student (
    student_id INT NOT NULL AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    academic_program VARCHAR(100) NOT NULL,
    PRIMARY KEY (student_id)
);

CREATE TABLE company (
    company_id INT NOT NULL AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    phone VARCHAR(20),
    PRIMARY KEY (company_id)
);

CREATE TABLE skill (
    skill_id INT NOT NULL AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(255),
    PRIMARY KEY (skill_id)
);

CREATE TABLE job_offer (
    job_offer_id INT NOT NULL AUTO_INCREMENT,
    company_id INT NOT NULL,
    position VARCHAR(100) NOT NULL,
    description TEXT,
    location VARCHAR(100),
    requirements TEXT,
    PRIMARY KEY (job_offer_id),
    FOREIGN KEY (company_id) REFERENCES company(company_id)
);

CREATE TABLE application (
    application_id INT NOT NULL AUTO_INCREMENT,
    student_id INT NOT NULL,
    job_offer_id INT NOT NULL,
    application_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'Pending',
    comments TEXT,
    PRIMARY KEY (application_id),
    UNIQUE (student_id, job_offer_id),
    FOREIGN KEY (student_id) REFERENCES student(student_id),
    FOREIGN KEY (job_offer_id) REFERENCES job_offer(job_offer_id),
    CONSTRAINT chk_application_status CHECK (
        status = 'Pending'
        OR status = 'Under Review'
        OR status = 'Accepted'
        OR status = 'Rejected'
    )
);

CREATE TABLE student_skill (
    student_id INT NOT NULL,
    skill_id INT NOT NULL,
    PRIMARY KEY (student_id, skill_id),
    FOREIGN KEY (student_id) REFERENCES student(student_id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES skill(skill_id) ON DELETE CASCADE
);

CREATE TABLE job_offer_skill (
    job_offer_id INT NOT NULL,
    skill_id INT NOT NULL,
    PRIMARY KEY (job_offer_id, skill_id),
    FOREIGN KEY (job_offer_id) REFERENCES job_offer(job_offer_id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES skill(skill_id) ON DELETE CASCADE
);
