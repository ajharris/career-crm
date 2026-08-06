# app/jobs/services.py

from sqlalchemy import select

from app.extensions import db
from app.models import JobPosting


def get_job_postings() -> list[JobPosting]:
    statement = (
        select(JobPosting)
        .order_by(JobPosting.date_found.desc())
    )

    return list(db.session.scalars(statement))


def create_job_posting(form) -> JobPosting:
    job = JobPosting(
        organization_id=form.organization_id.data,
        title=form.title.data.strip(),
        department=form.department.data.strip() or None,
        posting_url=form.posting_url.data.strip() or None,
        location=form.location.data.strip() or None,
        closing_date=form.closing_date.data,
    )

    db.session.add(job)
    db.session.commit()

    return job