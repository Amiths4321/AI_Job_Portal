import os
import random
import string
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.utils import secure_filename

from config import Config
from extensions import db
from models import Job, Application

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

with app.app_context():
    db.create_all()
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]


def generate_reference_no():
    return "JOB" + datetime.now().strftime("%y%m%d") + "".join(random.choices(string.digits, k=4))


# ---------- Public: Job listings ----------
@app.route("/")
def home():
    jobs = Job.query.filter_by(is_active=True).order_by(Job.posted_on.desc()).all()
    return render_template("home.html", jobs=jobs)


@app.route("/job/<int:job_id>")
def job_detail(job_id):
    job = Job.query.get_or_404(job_id)
    return render_template("job_detail.html", job=job)


# ---------- STEP 1: Personal details ----------
@app.route("/apply/<int:job_id>/step1", methods=["GET", "POST"])
def step1(job_id):
    job = Job.query.get_or_404(job_id)
    if request.method == "POST":
        session["job_id"] = job_id
        session["full_name"] = request.form["full_name"]
        session["email"] = request.form["email"]
        session["phone"] = request.form["phone"]
        session["dob"] = request.form["dob"]
        session["address"] = request.form["address"]
        return redirect(url_for("step2", job_id=job_id))
    return render_template("apply_step1.html", job=job, data=session)


# ---------- STEP 2: Education & experience ----------
@app.route("/apply/<int:job_id>/step2", methods=["GET", "POST"])
def step2(job_id):
    job = Job.query.get_or_404(job_id)
    if "full_name" not in session:
        return redirect(url_for("step1", job_id=job_id))
    if request.method == "POST":
        session["highest_qualification"] = request.form["highest_qualification"]
        session["university"] = request.form["university"]
        session["graduation_year"] = request.form["graduation_year"]
        session["current_company"] = request.form.get("current_company", "")
        session["years_experience"] = request.form["years_experience"]
        session["current_ctc"] = request.form.get("current_ctc", "")
        session["expected_ctc"] = request.form["expected_ctc"]
        session["notice_period"] = request.form["notice_period"]
        return redirect(url_for("step3", job_id=job_id))
    return render_template("apply_step2.html", job=job, data=session)


# ---------- STEP 3: Resume upload ----------
@app.route("/apply/<int:job_id>/step3", methods=["GET", "POST"])
def step3(job_id):
    job = Job.query.get_or_404(job_id)
    if "years_experience" not in session:
        return redirect(url_for("step2", job_id=job_id))
    if request.method == "POST":
        resume = request.files.get("resume")
        cover_letter = request.files.get("cover_letter")

        if resume and allowed_file(resume.filename):
            fname = secure_filename(f"{session['phone']}_resume_{resume.filename}")
            resume.save(os.path.join(app.config["UPLOAD_FOLDER"], fname))
            session["resume_filename"] = fname
        else:
            flash("Please upload a valid resume file (pdf, doc, docx).")
            return redirect(url_for("step3", job_id=job_id))

        if cover_letter and cover_letter.filename and allowed_file(cover_letter.filename):
            fname2 = secure_filename(f"{session['phone']}_cover_{cover_letter.filename}")
            cover_letter.save(os.path.join(app.config["UPLOAD_FOLDER"], fname2))
            session["cover_letter_filename"] = fname2
        else:
            session["cover_letter_filename"] = ""

        return redirect(url_for("step4", job_id=job_id))
    return render_template("apply_step3.html", job=job)


# ---------- STEP 4: Review & submit ----------
@app.route("/apply/<int:job_id>/step4", methods=["GET", "POST"])
def step4(job_id):
    job = Job.query.get_or_404(job_id)
    if "resume_filename" not in session:
        return redirect(url_for("step3", job_id=job_id))

    if request.method == "POST":
        reference_no = generate_reference_no()
        application = Application(
            reference_no=reference_no,
            job_id=job_id,
            full_name=session["full_name"],
            email=session["email"],
            phone=session["phone"],
            dob=session["dob"],
            address=session["address"],
            highest_qualification=session["highest_qualification"],
            university=session["university"],
            graduation_year=int(session["graduation_year"]),
            current_company=session.get("current_company") or None,
            years_experience=float(session["years_experience"]),
            current_ctc=float(session["current_ctc"]) if session.get("current_ctc") else None,
            expected_ctc=float(session["expected_ctc"]),
            notice_period=session["notice_period"],
            resume_filename=session["resume_filename"],
            cover_letter_filename=session.get("cover_letter_filename") or None,
        )
        db.session.add(application)
        db.session.commit()
        session.clear()
        return redirect(url_for("confirmation", ref=reference_no))

    return render_template("apply_step4.html", job=job, data=session)


@app.route("/apply/confirmation")
def confirmation():
    ref = request.args.get("ref")
    return render_template("confirmation.html", ref=ref)


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# ---------- Admin: Applications dashboard ----------
@app.route("/admin")
def admin_dashboard():
    job_filter = request.args.get("job_id", type=int)
    status_filter = request.args.get("status")

    query = Application.query
    if job_filter:
        query = query.filter_by(job_id=job_filter)
    if status_filter:
        query = query.filter_by(status=status_filter)

    applications = query.order_by(Application.applied_on.desc()).all()
    jobs = Job.query.all()
    return render_template("admin_dashboard.html", applications=applications, jobs=jobs,
                            job_filter=job_filter, status_filter=status_filter)


@app.route("/admin/application/<int:app_id>/status", methods=["POST"])
def update_status(app_id):
    application = Application.query.get_or_404(app_id)
    application.status = request.form["status"]
    db.session.commit()
    flash(f"Status updated for {application.full_name}.")
    return redirect(url_for("admin_dashboard"))


# ---------- Admin: Job postings management ----------
@app.route("/admin/jobs")
def admin_jobs():
    jobs = Job.query.order_by(Job.posted_on.desc()).all()
    return render_template("admin_jobs.html", jobs=jobs)


@app.route("/admin/jobs/new", methods=["GET", "POST"])
def admin_job_new():
    if request.method == "POST":
        job = Job(
            title=request.form["title"],
            department=request.form["department"],
            location=request.form["location"],
            job_type=request.form["job_type"],
            experience_required=request.form["experience_required"],
            description=request.form["description"],
        )
        db.session.add(job)
        db.session.commit()
        flash(f"Job '{job.title}' posted successfully.")
        return redirect(url_for("admin_jobs"))
    return render_template("admin_job_form.html")


@app.route("/admin/jobs/<int:job_id>/toggle", methods=["POST"])
def admin_job_toggle(job_id):
    job = Job.query.get_or_404(job_id)
    job.is_active = not job.is_active
    db.session.commit()
    return redirect(url_for("admin_jobs"))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)