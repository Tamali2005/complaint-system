import os
import secrets
from contextlib import contextmanager
from datetime import datetime, date
from functools import wraps

import psycopg2
import requests
from psycopg2 import errors
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

try:
    from dotenv import load_dotenv
    load_dotenv()  # local testing er jonno .env file porbe
except ImportError:
    pass

app = Flask(__name__)

# ---------------------------------------------------------------- Config
secret = os.environ.get("SECRET_KEY")
if not secret:
    secret = secrets.token_hex(32)
    print("WARNING: SECRET_KEY set kora nei. Restart hole sobai logout hoye jabe.")

app.secret_key = secret
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE") == "1",
    MAX_CONTENT_LENGTH=5 * 1024 * 1024,  # 5 MB
)

DATABASE_URL = os.environ.get("DATABASE_URL")

SUPABASE_URL = (os.environ.get("SUPABASE_URL") or "").rstrip("/")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
SUPABASE_BUCKET = os.environ.get("SUPABASE_BUCKET", "proofs")

UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf", "doc", "docx"}
VALID_STATUSES = {"Pending", "In Progress", "Resolved", "Rejected"}

try:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
except OSError:
    pass


# ---------------------------------------------------------------- Database
@contextmanager
def get_cursor():
    """Connection kholbe, kaj shesh hole commit korbe, error hole rollback."""
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL environment variable set kora nei")
    conn = psycopg2.connect(DATABASE_URL, sslmode="require", connect_timeout=10)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Table na thakle banabe, ar admin user create/update korbe."""
    with get_cursor() as cur:
        cur.execute("""
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
            )
        """)
        cur.execute("""
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
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                email VARCHAR(100) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        admin_user = os.environ.get("ADMIN_USERNAME")
        admin_pass = os.environ.get("ADMIN_PASSWORD")
        admin_email = os.environ.get("ADMIN_EMAIL", "admin@example.com")
        if admin_user and admin_pass:
            cur.execute("""
                INSERT INTO admins (username, password, email)
                VALUES (%s, %s, %s)
                ON CONFLICT (username)
                DO UPDATE SET password = EXCLUDED.password, email = EXCLUDED.email
            """, (admin_user, generate_password_hash(admin_pass), admin_email))
    print("Database ready.")


try:
    init_db()
except Exception as exc:  # app chalu thakbe, kintu log e error dekhabe
    print(f"DATABASE INIT FAILED: {exc}")


# ---------------------------------------------------------------- Helpers
def clean_row(row):
    """datetime ke string e convert kore (JSON er jonno)."""
    return {k: (v.isoformat() if isinstance(v, (datetime, date)) else v)
            for k, v in row.items()}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_proof(file, student_id):
    """Supabase Storage e upload kore (set kora thakle), na hole local folder e."""
    ext = file.filename.rsplit(".", 1)[1].lower()
    name = secure_filename(
        f"{student_id}_{datetime.now():%Y%m%d%H%M%S}_{secrets.token_hex(4)}.{ext}"
    )

    if SUPABASE_URL and SUPABASE_SERVICE_KEY:
        headers = {
            "apikey": SUPABASE_SERVICE_KEY,
            "Content-Type": file.mimetype or "application/octet-stream",
        }
        # Purano JWT style key (eyJ...) hole Authorization lage.
        # Notun sb_secret_ key e shudhu apikey header lage.
        if SUPABASE_SERVICE_KEY.startswith("eyJ"):
            headers["Authorization"] = f"Bearer {SUPABASE_SERVICE_KEY}"

        resp = requests.post(
            f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{name}",
            headers=headers,
            data=file.read(),
            timeout=30,
        )
        if resp.status_code not in (200, 201):
            app.logger.error("Supabase upload failed: %s %s", resp.status_code, resp.text)
            raise RuntimeError("File upload failed")
        return f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{name}"

    file.save(os.path.join(UPLOAD_FOLDER, name))
    return f"/static/uploads/{name}"


def student_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "student_id" not in session:
            return jsonify({"success": False, "message": "Please login first"}), 401
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "admin_username" not in session:
            return jsonify({"success": False, "message": "Admin login required"}), 401
        return f(*args, **kwargs)
    return wrapper


def server_error(exc):
    app.logger.exception(exc)
    return jsonify({"success": False, "message": "Something went wrong. Please try again."}), 500


@app.errorhandler(413)
def too_large(_):
    return jsonify({"success": False, "message": "File too large (max 5 MB)"}), 413


# ---------------------------------------------------------------- Pages
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/student-register")
def student_register():
    return render_template("student_register.html")


@app.route("/student-login")
def student_login():
    return render_template("student_login.html")


@app.route("/admin-login")
def admin_login():
    return render_template("admin_login.html")


@app.route("/student-dashboard")
def student_dashboard():
    if "student_id" not in session:
        return redirect(url_for("student_login"))
    return render_template("student_dashboard.html")


@app.route("/admin-dashboard")
def admin_dashboard():
    if "admin_username" not in session:
        return redirect(url_for("admin_login"))
    return render_template("admin_dashboard.html")


# ---------------------------------------------------------------- Auth API
@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    required = ["studentId", "fullName", "email", "phone", "department", "password"]
    if any(not str(data.get(k, "")).strip() for k in required):
        return jsonify({"success": False, "message": "Please fill all required fields"}), 400
    if len(data["password"]) < 6:
        return jsonify({"success": False, "message": "Password must be at least 6 characters"}), 400

    try:
        with get_cursor() as cur:
            cur.execute("""
                INSERT INTO students (student_id, full_name, email, phone, department,
                                      course, year_of_study, section, identity_type, password)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                data["studentId"].strip(), data["fullName"].strip(),
                data["email"].strip().lower(), data["phone"].strip(),
                data["department"].strip(), data.get("course"),
                data.get("yearOfStudy"), data.get("section"),
                data.get("identityType") or "Student",
                generate_password_hash(data["password"]),
            ))
        return jsonify({"success": True, "message": "Registration successful!"})
    except errors.UniqueViolation:
        return jsonify({"success": False,
                        "message": "This Student ID or email is already registered"}), 409
    except Exception as exc:
        return server_error(exc)


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    try:
        with get_cursor() as cur:
            cur.execute("SELECT student_id, full_name, password FROM students WHERE student_id = %s",
                        (str(data.get("studentId", "")).strip(),))
            student = cur.fetchone()

        if student and student["password"] and check_password_hash(student["password"], data.get("password", "")):
            session.clear()
            session["student_id"] = student["student_id"]
            session["student_name"] = student["full_name"]
            return jsonify({"success": True, "message": "Login successful!"})
        return jsonify({"success": False, "message": "Invalid Student ID or password"}), 401
    except Exception as exc:
        return server_error(exc)


@app.route("/api/admin-login", methods=["POST"])
def admin_login_api():
    data = request.get_json(silent=True) or {}
    try:
        with get_cursor() as cur:
            cur.execute("SELECT username, password FROM admins WHERE username = %s",
                        (str(data.get("username", "")).strip(),))
            admin = cur.fetchone()

        if admin and check_password_hash(admin["password"], data.get("password", "")):
            session.clear()
            session["admin_username"] = admin["username"]
            return jsonify({"success": True})
        return jsonify({"success": False, "message": "Invalid username or password"}), 401
    except Exception as exc:
        return server_error(exc)


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully"})


# ---------------------------------------------------------------- Student API
@app.route("/api/student-info")
@student_required
def student_info():
    try:
        with get_cursor() as cur:
            cur.execute("""
                SELECT student_id, full_name, email, phone, department, course,
                       year_of_study, section, identity_type, registration_date
                FROM students WHERE student_id = %s
            """, (session["student_id"],))
            student = cur.fetchone()
        if not student:
            session.clear()
            return jsonify({"success": False, "message": "Student not found"}), 404
        return jsonify({"success": True, "student": clean_row(student)})
    except Exception as exc:
        return server_error(exc)


@app.route("/api/my-complaints")
@student_required
def my_complaints():
    try:
        with get_cursor() as cur:
            cur.execute("""
                SELECT * FROM complaints
                WHERE student_id = %s
                ORDER BY submission_date DESC
            """, (session["student_id"],))
            rows = cur.fetchall()
        return jsonify({"success": True, "complaints": [clean_row(r) for r in rows]})
    except Exception as exc:
        return server_error(exc)


@app.route("/api/submit-complaint", methods=["POST"])
@student_required
def submit_complaint():
    form = request.form
    required = ["categoryType", "complaintType", "complaintTitle", "detailedDescription"]
    if any(not form.get(k, "").strip() for k in required):
        return jsonify({"success": False, "message": "Please fill all required fields"}), 400

    try:
        file_path = None
        file = request.files.get("proofFile")
        if file and file.filename:
            if not allowed_file(file.filename):
                return jsonify({"success": False,
                                "message": "File type not allowed (png, jpg, gif, pdf, doc, docx only)"}), 400
            file_path = save_proof(file, session["student_id"])

        with get_cursor() as cur:
            cur.execute("SELECT * FROM students WHERE student_id = %s", (session["student_id"],))
            student = cur.fetchone()
            if not student:
                return jsonify({"success": False, "message": "Student not found"}), 404

            cur.execute("""
                INSERT INTO complaints (student_id, student_name, student_email, student_phone,
                                        department, identity_type, category_type, complaint_type,
                                        complaint_title, detailed_description, proof_file_path,
                                        complaint_mode, priority)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                student["student_id"], student["full_name"], student["email"], student["phone"],
                student["department"], student["identity_type"] or "Student",
                form.get("categoryType"), form.get("complaintType"),
                form.get("complaintTitle").strip(), form.get("detailedDescription").strip(),
                file_path, form.get("complaintMode") or "Online", form.get("priority") or "Medium",
            ))
        return jsonify({"success": True, "message": "Complaint submitted"})
    except Exception as exc:
        return server_error(exc)


# ---------------------------------------------------------------- Admin API
@app.route("/api/admin/students")
@admin_required
def admin_students():
    try:
        with get_cursor() as cur:
            cur.execute("""
                SELECT student_id, full_name, email, phone, department, course,
                       year_of_study, section, identity_type, registration_date
                FROM students ORDER BY registration_date DESC
            """)
            rows = cur.fetchall()
        return jsonify({"success": True, "students": [clean_row(r) for r in rows]})
    except Exception as exc:
        return server_error(exc)


@app.route("/api/admin/complaints")
@admin_required
def admin_complaints():
    try:
        with get_cursor() as cur:
            cur.execute("SELECT * FROM complaints ORDER BY submission_date DESC")
            rows = cur.fetchall()
        return jsonify({"success": True, "complaints": [clean_row(r) for r in rows]})
    except Exception as exc:
        return server_error(exc)


@app.route("/api/admin/respond-complaint", methods=["POST"])
@admin_required
def respond_complaint():
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    response_text = (data.get("response") or "").strip()

    try:
        complaint_id = int(data.get("complaintId"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Invalid complaint id"}), 400

    if status not in VALID_STATUSES:
        return jsonify({"success": False, "message": "Invalid status"}), 400
    if not response_text:
        return jsonify({"success": False, "message": "Response cannot be empty"}), 400

    try:
        with get_cursor() as cur:
            cur.execute("""
                UPDATE complaints
                SET status = %s, admin_response = %s, response_date = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (status, response_text, complaint_id))
            if cur.rowcount == 0:
                return jsonify({"success": False, "message": "Complaint not found"}), 404
        return jsonify({"success": True, "message": "Response saved"})
    except Exception as exc:
        return server_error(exc)


# ---------------------------------------------------------------- Misc
@app.route("/api/test")
def test():
    return jsonify({"success": True, "message": "API working"})


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1",
            port=int(os.environ.get("PORT", 5000)))
