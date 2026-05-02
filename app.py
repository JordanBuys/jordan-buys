
import os
import sqlite3
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
DB_PATH = BASE_DIR / "jordan_buys.db"
UPLOAD_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key-now")

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "JordanBuys2026!")
ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH", generate_password_hash(DEFAULT_ADMIN_PASSWORD))

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                shoe_name TEXT NOT NULL,
                shoe_size TEXT NOT NULL,
                condition TEXT NOT NULL,
                used_level TEXT,
                condition_notes TEXT,
                payment_method TEXT NOT NULL,
                payment_contact TEXT NOT NULL,
                full_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT NOT NULL,
                address TEXT NOT NULL,
                city TEXT NOT NULL,
                state TEXT NOT NULL,
                zip TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending',
                quote_amount TEXT,
                admin_notes TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                submission_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                FOREIGN KEY(submission_id) REFERENCES submissions(id)
            )
        """)
        conn.commit()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapped


@app.before_request
def ensure_db():
    init_db()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/submit", methods=["POST"])
def submit():
    required = ["shoeName", "shoeSize", "condition", "payment", "paymentContact", "fullName", "phone", "email", "address", "city", "state", "zip"]
    for field in required:
        if not request.form.get(field, "").strip():
            flash("Please complete all required fields.")
            return redirect(url_for("index") + "#submit")

    if request.form.get("condition") == "Used" and not request.form.get("usedLevel"):
        flash("Please select a used condition level.")
        return redirect(url_for("index") + "#submit")

    valid_files = [f for f in request.files.getlist("photos") if f and allowed_file(f.filename)]
    if not valid_files:
        flash("Please upload at least one shoe photo.")
        return redirect(url_for("index") + "#submit")

    with get_db() as conn:
        cur = conn.execute("""
            INSERT INTO submissions (
                created_at, shoe_name, shoe_size, condition, used_level, condition_notes,
                payment_method, payment_contact, full_name, phone, email,
                address, city, state, zip
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            request.form["shoeName"].strip(),
            request.form["shoeSize"].strip(),
            request.form["condition"].strip(),
            request.form.get("usedLevel", "").strip(),
            request.form.get("conditionNotes", "").strip(),
            request.form["payment"].strip(),
            request.form["paymentContact"].strip(),
            request.form["fullName"].strip(),
            request.form["phone"].strip(),
            request.form["email"].strip(),
            request.form["address"].strip(),
            request.form["city"].strip(),
            request.form["state"].strip(),
            request.form["zip"].strip(),
        ))
        submission_id = cur.lastrowid
        folder = UPLOAD_DIR / str(submission_id)
        folder.mkdir(exist_ok=True)

        for file in valid_files:
            safe_name = secure_filename(file.filename)
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{safe_name}"
            file.save(folder / filename)
            conn.execute("INSERT INTO photos (submission_id, filename) VALUES (?, ?)", (submission_id, filename))

        conn.commit()

    return render_template("success.html")


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username_ok = request.form.get("username") == ADMIN_USERNAME
        password_ok = check_password_hash(ADMIN_PASSWORD_HASH, request.form.get("password", ""))
        if username_ok and password_ok:
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))
        flash("Incorrect username or password.")
    return render_template("admin_login.html")


@app.route("/admin/logout")
@login_required
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.route("/admin")
@login_required
def admin_dashboard():
    status = request.args.get("status", "")
    search = request.args.get("search", "").strip()

    where = []
    params = []

    if status:
        where.append("status = ?")
        params.append(status)

    if search:
        where.append("(shoe_name LIKE ? OR full_name LIKE ? OR email LIKE ? OR shoe_size LIKE ?)")
        params.extend([f"%{search}%"] * 4)

    sql = "SELECT * FROM submissions"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id DESC"

    with get_db() as conn:
        submissions = conn.execute(sql, params).fetchall()
        counts = {
            "Total": conn.execute("SELECT COUNT(*) FROM submissions").fetchone()[0],
            "Pending": conn.execute("SELECT COUNT(*) FROM submissions WHERE status='Pending'").fetchone()[0],
            "Accepted": conn.execute("SELECT COUNT(*) FROM submissions WHERE status='Accepted'").fetchone()[0],
            "Quoted": conn.execute("SELECT COUNT(*) FROM submissions WHERE status='Quoted'").fetchone()[0],
            "Rejected": conn.execute("SELECT COUNT(*) FROM submissions WHERE status='Rejected'").fetchone()[0],
        }

    return render_template("admin_dashboard.html", submissions=submissions, counts=counts, status=status, search=search)


@app.route("/admin/submission/<int:submission_id>")
@login_required
def admin_submission(submission_id):
    with get_db() as conn:
        sub = conn.execute("SELECT * FROM submissions WHERE id=?", (submission_id,)).fetchone()
        photos = conn.execute("SELECT * FROM photos WHERE submission_id=?", (submission_id,)).fetchall()
    if not sub:
        return "Submission not found", 404
    return render_template("admin_submission.html", sub=sub, photos=photos)


@app.route("/admin/submission/<int:submission_id>/update", methods=["POST"])
@login_required
def update_submission(submission_id):
    with get_db() as conn:
        conn.execute("""
            UPDATE submissions
            SET status=?, quote_amount=?, admin_notes=?
            WHERE id=?
        """, (
            request.form.get("status", "Pending"),
            request.form.get("quote_amount", ""),
            request.form.get("admin_notes", ""),
            submission_id
        ))
        conn.commit()
    flash("Submission updated.")
    return redirect(url_for("admin_submission", submission_id=submission_id))


@app.route("/uploads/<int:submission_id>/<path:filename>")
@login_required
def uploaded_file(submission_id, filename):
    return send_from_directory(UPLOAD_DIR / str(submission_id), filename)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
