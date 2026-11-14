# 🎓 Student Complaint Management System

A full-stack web application where students can submit complaints, attach proof, and track their status in real time, while administrators review, respond to, and resolve them from a dedicated control panel.

**🔗 Live Demo:** [https://complaint-system-0p2f.onrender.com](https://complaint-system-0p2f.onrender.com)

> ⏳ Hosted on a free plan, so the first load may take 30-50 seconds while the server wakes up.

---

## ✨ Features

### 👨‍🎓 Student Portal
- Register and log in securely
- Submit complaints with category, type, priority and detailed description
- Attach proof files (images, PDF, Word documents up to 5 MB)
- Dashboard with live counts of Pending, In Progress and Resolved complaints
- View admin responses and status updates on every complaint
- Auto-filled complaint form from the student profile

### 🛡️ Admin Panel
- Separate, protected admin login
- Overview dashboard with total students, total complaints, pending and resolved counts
- View all registered students with search
- View all complaints with search and status filter
- Respond to complaints and update status (Pending, In Progress, Resolved, Rejected)
- Open attached proof files directly

### 🔒 Security
- Passwords stored as salted hashes (Werkzeug), never in plain text
- Session based authentication with protected API routes for students and admins
- User input is escaped before rendering to prevent XSS
- Database credentials and API keys kept in environment variables
- File type and size validation on uploads

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask, Gunicorn |
| Database | PostgreSQL (Supabase) |
| File Storage | Supabase Storage |
| Frontend | HTML, Tailwind CSS, Vanilla JavaScript |
| Hosting | Render (app), Supabase (database and storage) |

---

## 📁 Project Structure

```
complaint-system/
├── app.py                  # Flask app: routes, auth, database logic
├── requirements.txt        # Python dependencies
├── schema.sql              # PostgreSQL schema (tables are also auto-created)
├── .env.example            # Example environment variables
├── templates/              # HTML pages
│   ├── index.html
│   ├── student_register.html
│   ├── student_login.html
│   ├── student_dashboard.html
│   ├── admin_login.html
│   └── admin_dashboard.html
└── static/
    └── js/                 # Frontend scripts
        ├── register.js
        ├── login.js
        ├── student-dashboard.js
        ├── admin-login.js
        └── admin-dashboard.js
```

---

## 🚀 Run Locally

**1. Clone the repository**
```bash
git clone https://github.com/Tamali2005/complaint-system.git
cd complaint-system
```

**2. Create a virtual environment and install dependencies**
```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

pip install -r requirements.txt
```

**3. Set up environment variables**

Copy `.env.example` to `.env` and fill in your own values (see the table below).

**4. Start the app**
```bash
python app.py
```
Open [http://localhost:5000](http://localhost:5000)

Tables are created automatically on first start, and the admin account is created from `ADMIN_USERNAME` and `ADMIN_PASSWORD`.

---

## ⚙️ Environment Variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string (Supabase Session Pooler) |
| `SECRET_KEY` | Long random string used to sign login sessions |
| `ADMIN_USERNAME` | Username for the admin account |
| `ADMIN_PASSWORD` | Password for the admin account |
| `ADMIN_EMAIL` | Admin email address |
| `SUPABASE_URL` | Supabase project URL (for proof file uploads) |
| `SUPABASE_SERVICE_KEY` | Supabase secret key (server side only) |
| `SUPABASE_BUCKET` | Storage bucket name, e.g. `proofs` |
| `SESSION_COOKIE_SECURE` | Set to `1` when running over HTTPS |

> ⚠️ Never commit your `.env` file or share these values publicly.

---

## ☁️ Deployment

1. Create a Supabase project, a public Storage bucket named `proofs`, and copy the Session Pooler connection string.
2. Push this repository to GitHub.
3. On Render, create a **Web Service** from the repository:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn app:app`
4. Add the environment variables listed above and deploy.

---

## 🔌 API Overview

| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| POST | `/api/register` | Public | Register a student |
| POST | `/api/login` | Public | Student login |
| POST | `/api/admin-login` | Public | Admin login |
| POST | `/api/logout` | Logged in | Log out |
| GET | `/api/student-info` | Student | Current student profile |
| GET | `/api/my-complaints` | Student | Student's own complaints |
| POST | `/api/submit-complaint` | Student | Submit a complaint with proof |
| GET | `/api/admin/students` | Admin | List all students |
| GET | `/api/admin/complaints` | Admin | List all complaints |
| POST | `/api/admin/respond-complaint` | Admin | Respond and update status |

---

## 🔮 Future Improvements

- Email notifications when a complaint status changes
- Google sign-in for students
- Password reset via email
- Analytics charts for admins (complaints by category and status)
- Admin and student sessions in the same browser

---

## 👩‍💻 Author

**Tamali Khan**
GitHub: [@Tamali2005](https://github.com/Tamali2005)

---

⭐ If you found this project useful, consider giving it a star!
