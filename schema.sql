-- PostgreSQL schema for Supabase (SQL Editor te paste kore Run koro)
-- Note: app.py start howar somoy eta automatic o banay, tai eta optional/backup.

CREATE TABLE IF NOT EXISTS students (
    id SERIAL PRIMARY KEY,
    student_id VARCHAR(50) UNIQUE NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20) NOT NULL,
    department VARCHAR(100) NOT NULL,
    course VARCHAR(100),
    year_of_study VARCHAR(20),
    section VARCHAR(20),
    identity_type VARCHAR(50) DEFAULT 'Student',
    password VARCHAR(255),
    google_id VARCHAR(255),
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS complaints (
    id SERIAL PRIMARY KEY,
    student_id VARCHAR(50) NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    student_name VARCHAR(100) NOT NULL,
    student_email VARCHAR(100) NOT NULL,
    student_phone VARCHAR(20) NOT NULL,
    department VARCHAR(200) NOT NULL,
    identity_type VARCHAR(50) NOT NULL,
    category_type VARCHAR(100) NOT NULL,
    complaint_type VARCHAR(200) NOT NULL,
    complaint_title VARCHAR(300) NOT NULL,
    detailed_description TEXT NOT NULL,
    proof_file_path VARCHAR(500),
    complaint_mode VARCHAR(20) DEFAULT 'Online',
    priority VARCHAR(20) NOT NULL,
    status VARCHAR(50) DEFAULT 'Pending',
    admin_response TEXT,
    submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    response_date TIMESTAMP
);

CREATE TABLE IF NOT EXISTS admins (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Admin user app.py nijei banay (ADMIN_USERNAME / ADMIN_PASSWORD environment variable theke).
