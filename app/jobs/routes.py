# app/jobs/routes.py

from flask import flash, redirect, render_template, url_for

from app.jobs import bp
from app.jobs.forms import JobPostingForm
from app.jobs.services import create_job_posting, get_job_postings


@bp.get("/")
def index():
    jobs = get_job_postings()
    return render_template("jobs/index.html", jobs=jobs)


@bp.route("/new", methods=["GET", "POST"])
def create():
    form = JobPostingForm()

    if form.validate_on_submit():
        job = create_job_posting(form)
        flash("Job posting created.", "success")
        return redirect(url_for("jobs.detail", job_id=job.id))

    return render_template("jobs/form.html", form=form)