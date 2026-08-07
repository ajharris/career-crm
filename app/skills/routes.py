"""Routes for skill analytics and job requirements."""

from flask import flash, redirect, render_template, url_for

from app.jobs.forms import JobSkillForm
from app.jobs.services import get_job_posting
from app.skills import bp
from app.skills.services import (
    add_job_skill,
    delete_job_skill,
    skill_choices,
    skill_matrix,
)


@bp.get("")
def index():
    return render_template("skills/index.html", **skill_matrix())


@bp.route("/jobs/<int:job_id>", methods=["GET", "POST"])
def job_requirements(job_id: int):
    job = get_job_posting(job_id)
    form = JobSkillForm()
    form.skill_id.choices = skill_choices()
    if form.validate_on_submit():
        try:
            add_job_skill(
                job,
                skill_id=form.skill_id.data,
                required=form.required.data,
                importance=form.importance.data,
                notes=form.notes.data,
            )
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash("Job skill saved.", "success")
            return redirect(url_for("skills.job_requirements", job_id=job.id))
    return render_template("skills/job_requirements.html", job=job, form=form)


@bp.post("/jobs/<int:job_id>/<int:record_id>/delete")
def delete_requirement(job_id: int, record_id: int):
    job = get_job_posting(job_id)
    delete_job_skill(job, record_id)
    flash("Job skill removed.", "success")
    return redirect(url_for("skills.job_requirements", job_id=job.id))
