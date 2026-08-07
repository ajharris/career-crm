"""Thin routes for onboarding and career-profile editing."""

from typing import Any, cast

from flask import flash, redirect, render_template, url_for
from flask_login import login_required

from app.models.career_profile import (
    CareerPriority,
    Certification,
    Education,
    PortfolioItem,
    PreferredLocation,
    UserLanguage,
    UserSkill,
)
from app.profile import bp
from app.profile.forms import (
    BackgroundForm,
    CertificationForm,
    CompleteForm,
    EducationForm,
    InterestsForm,
    LanguageForm,
    LocationForm,
    PortfolioForm,
    PriorityForm,
    SkillForm,
    StrategyForm,
    WorkPreferencesForm,
)
from app.profile.services import (
    complete_onboarding,
    create_education,
    create_portfolio,
    delete_owned,
    get_profile,
    owned_records,
    profile_summary,
    save_interests,
    save_owned,
    save_priority,
    save_profile_step,
    save_skill,
    save_work_preferences,
    update_priority,
)

STEPS = (
    "Background",
    "Education",
    "Skills",
    "Career Interests",
    "Work Preferences",
    "Career Priorities",
    "Portfolio",
    "Job Search Strategy",
    "Review",
)


@bp.get("")
@login_required
def index():
    return render_template(
        "profile/index.html",
        profile=get_profile(),
        education=owned_records(Education),
        certifications=owned_records(Certification),
        languages=owned_records(UserLanguage),
        skills=owned_records(UserSkill),
        priorities=owned_records(CareerPriority),
        portfolio=owned_records(PortfolioItem),
        locations=owned_records(PreferredLocation),
        summary=profile_summary(),
    )


@bp.get("/onboarding")
@login_required
def onboarding():
    profile = get_profile()
    if profile.onboarding_completed:
        return redirect(url_for("dashboard.index"))
    return redirect(url_for("profile.step", step=profile.onboarding_step))


@bp.route("/onboarding/<int:step>", methods=["GET", "POST"])
@login_required
def step(step: int):
    if step not in range(1, 10):
        return redirect(url_for("profile.onboarding"))
    profile = get_profile()
    form = _form_for_step(step, profile)
    if form.validate_on_submit():
        if step == 1:
            save_profile_step(profile, _values(form), 2)
        elif step == 2:
            create_education(_values(form))
            save_profile_step(profile, {}, 3)
        elif step == 3:
            try:
                save_skill(_values(form))
            except ValueError as exc:
                form.name.errors = (*form.name.errors, str(exc))
                return _render_step(step, form)
            save_profile_step(profile, {}, 4)
        elif step == 4:
            save_interests(
                form.preferred_roles.data or "",
                form.industries.data,
                form.job_families.data,
            )
            save_profile_step(profile, {}, 5)
        elif step == 5:
            save_work_preferences(_values(form))
        elif step == 6:
            save_priority(_values(form))
            save_profile_step(profile, {}, 7)
        elif step == 7:
            create_portfolio(_values(form))
            save_profile_step(profile, {}, 8)
        elif step == 8:
            save_profile_step(profile, _values(form), 9)
        elif step == 9:
            complete_onboarding(profile)
            flash("Your career profile is ready.", "success")
            return redirect(url_for("dashboard.index"))
        return redirect(url_for("profile.step", step=min(step + 1, 9)))
    return _render_step(step, form)


@bp.post("/onboarding/<int:step>/skip")
@login_required
def skip_step(step: int):
    """Persist progress past an optional repeatable-record step."""
    if step not in {2, 3, 6, 7}:
        return redirect(url_for("profile.step", step=step))
    form = CompleteForm()
    if form.validate_on_submit():
        save_profile_step(get_profile(), {}, step + 1)
    return redirect(url_for("profile.step", step=step + 1))


@bp.post("/<kind>/<int:record_id>/delete")
@login_required
def delete_record(kind: str, record_id: int):
    models = {
        "education": Education,
        "certification": Certification,
        "language": UserLanguage,
        "skill": UserSkill,
        "priority": CareerPriority,
        "portfolio": PortfolioItem,
        "location": PreferredLocation,
    }
    if kind not in models:
        return redirect(url_for("profile.index"))
    delete_owned(models[kind], record_id)
    flash("Profile record deleted.", "success")
    return redirect(url_for("profile.index"))


@bp.route("/<kind>/new", methods=["GET", "POST"])
@bp.route("/<kind>/<int:record_id>/edit", methods=["GET", "POST"])
@login_required
def edit_record(kind: str, record_id: int | None = None):
    choices = {
        "education": (Education, EducationForm),
        "certification": (Certification, CertificationForm),
        "language": (UserLanguage, LanguageForm),
        "portfolio": (PortfolioItem, PortfolioForm),
        "location": (PreferredLocation, LocationForm),
        "skill": (UserSkill, SkillForm),
        "priority": (CareerPriority, PriorityForm),
    }
    if kind not in choices:
        return redirect(url_for("profile.index"))
    model, form_class = choices[kind]
    from app.profile.services import get_owned

    record = get_owned(model, record_id) if record_id else None
    form = cast(Any, form_class(obj=record))
    if form.validate_on_submit():
        try:
            if kind == "skill":
                save_skill(_values(form), record_id)
            elif kind == "priority":
                update_priority(_values(form), record_id)
            else:
                save_owned(model, _values(form), record_id)
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash("Profile record saved.", "success")
            return redirect(url_for("profile.index"))
    return render_template("profile/edit_record.html", form=form, kind=kind)


def _form_for_step(step: int, profile):
    forms = {
        1: BackgroundForm,
        2: EducationForm,
        3: SkillForm,
        4: InterestsForm,
        5: WorkPreferencesForm,
        6: PriorityForm,
        7: PortfolioForm,
        8: StrategyForm,
        9: CompleteForm,
    }
    return forms[step](obj=profile if step in {1, 8} else None)


def _values(form) -> dict:
    return {
        field.name: field.data
        for field in form
        if field.name not in {"csrf_token", "submit"}
    }


def _render_step(step: int, form):
    records = {
        2: owned_records(Education),
        3: owned_records(UserSkill),
        6: owned_records(CareerPriority),
        7: owned_records(PortfolioItem),
    }.get(step, [])
    return render_template(
        "profile/onboarding.html",
        form=form,
        step=step,
        steps=STEPS,
        records=records,
        profile=get_profile(),
        summary=profile_summary(),
    )
