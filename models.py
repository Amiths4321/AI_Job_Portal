from datetime import datetime
from extensions import db


class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    department = db.Column(db.String(80), nullable=False)
    location = db.Column(db.String(80), nullable=False)
    job_type = db.Column(db.String(30), nullable=False)
    experience_required = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    posted_on = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    applications = db.relationship("Application", backref="job", lazy=True)


class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reference_no = db.Column(db.String(20), unique=True, nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"), nullable=False)

    # Step 1: Personal details
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    dob = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(300), nullable=False)

    # Step 2: Education & experience
    highest_qualification = db.Column(db.String(80), nullable=False)
    university = db.Column(db.String(120), nullable=False)
    graduation_year = db.Column(db.Integer, nullable=False)
    current_company = db.Column(db.String(120), nullable=True)
    years_experience = db.Column(db.Float, nullable=False)
    current_ctc = db.Column(db.Float, nullable=True)
    expected_ctc = db.Column(db.Float, nullable=False)
    notice_period = db.Column(db.String(40), nullable=False)

    # Step 3: Documents
    resume_filename = db.Column(db.String(200), nullable=True)
    cover_letter_filename = db.Column(db.String(200), nullable=True)

    status = db.Column(db.String(20), default="Applied")
    applied_on = db.Column(db.DateTime, default=datetime.utcnow)