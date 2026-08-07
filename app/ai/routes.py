from datetime import UTC, datetime

from flask import flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy import select

from app.ai import bp
from app.ai.services import CredentialService, generate, provider_for_user, providers
from app.auth.permissions import actor_id
from app.extensions import db
from app.models import Application, UserAIProviderCredential


@bp.route("", methods=["GET", "POST"])
@login_required
def index():
    from app.profile.services import get_profile

    profile = get_profile()
    applications = list(
        db.session.scalars(
            select(Application)
            .where(Application.owner_id == actor_id())
            .order_by(Application.updated_at.desc())
        )
    )
    result = None
    if request.method == "POST":
        application = db.session.scalar(
            select(Application).where(
                Application.id == request.form.get("application_id", type=int),
                Application.owner_id == actor_id(),
            )
        )
        if application:
            if not profile.ai_assistance_enabled:
                flash("Enable an AI provider in AI Settings first.", "warning")
                return redirect(url_for("ai.settings"))
            context = {
                "job": application.job_posting.title,
                "organization": application.job_posting.organization.name,
                "description": application.job_posting.description or "",
                "user_notes": request.form.get("notes", "")[:4000],
            }
            try:
                result = generate(request.form.get("task", "job_summary"), context)
            except (RuntimeError, ValueError) as exc:
                flash(str(exc), "warning")
    return render_template(
        "ai/index.html", applications=applications, result=result, profile=profile
    )


@bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    """Configure a provider without ever rendering its stored secret."""
    from app.profile.services import get_profile

    profile = get_profile()
    credentials = {
        item.provider: item
        for item in db.session.scalars(
            select(UserAIProviderCredential).where(
                UserAIProviderCredential.user_id == actor_id()
            )
        )
    }
    if request.method == "POST":
        action = request.form.get("action", "save")
        provider = request.form.get("provider", "deterministic")
        if provider not in dict(providers.choices()):
            flash("Unsupported AI provider.", "danger")
            return redirect(url_for("ai.settings"))
        if action == "disconnect":
            CredentialService.disconnect(actor_id(), provider)
            profile.ai_assistance_enabled = False
            db.session.commit()
            flash("AI provider disconnected.", "success")
        else:
            secret = request.form.get("api_key", "")
            try:
                if secret:
                    CredentialService.save(actor_id(), provider, secret)
                profile.preferred_ai_provider = provider
                profile.preferred_ai_model = (
                    request.form.get("model", "").strip() or None
                )
                profile.ai_assistance_enabled = request.form.get("enabled") == "y"
                profile.ai_suggestions_enabled = request.form.get("suggestions") == "y"
                db.session.commit()
                if action == "test":
                    provider_for_user(actor_id()).test_connection()
                    credential = credentials.get(provider) or db.session.scalar(
                        select(UserAIProviderCredential).where(
                            UserAIProviderCredential.user_id == actor_id(),
                            UserAIProviderCredential.provider == provider,
                        )
                    )
                    if credential:
                        credential.verification_status = "verified"
                        credential.last_verified_at = datetime.now(UTC)
                        db.session.commit()
                    flash("AI provider connection verified.", "success")
                else:
                    flash("AI settings saved.", "success")
            except (RuntimeError, ValueError) as exc:
                db.session.rollback()
                flash(str(exc), "warning")
        return redirect(url_for("ai.settings"))
    return render_template(
        "ai/settings.html",
        profile=profile,
        provider_choices=providers.choices(),
        credentials=credentials,
    )
