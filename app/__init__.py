"""Career CRM application factory."""

import logging
import os
from logging.config import dictConfig
from pathlib import Path
from typing import Any

import click
from flask import Flask, g, render_template, request
from flask_login import current_user
from werkzeug.middleware.proxy_fix import ProxyFix

from app.config import CONFIGURATIONS, Config
from app.extensions import csrf, db, login_manager, migrate
from app.utils.text import linkify_text


def create_app(config: str | type[Config] | dict[str, Any] | None = None) -> Flask:
    """Create and configure a Career CRM application instance."""
    configure_logging()
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(resolve_config(config))
    if isinstance(config, dict):
        app.config.from_mapping(config)
    if (
        app.config.get("PREFERRED_URL_SCHEME") == "https"
        and app.config["SECRET_KEY"] == "development-only-secret"
    ):
        raise RuntimeError(
            "SECRET_KEY must be set to a strong unique value in production."
        )
    if app.config.get("PREFERRED_URL_SCHEME") == "https":
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)  # type: ignore[method-assign]

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    initialize_extensions(app)
    app.jinja_env.filters["linkify"] = linkify_text
    from app.performance import init_performance

    init_performance(app)
    register_blueprints(app)
    register_error_handlers(app)
    register_commands(app)
    app.logger.info("Career CRM application initialized")
    return app


def resolve_config(config: str | type[Config] | dict[str, Any] | None) -> type[Config]:
    """Resolve a configuration name or class to a configuration class."""
    if isinstance(config, type) and issubclass(config, Config):
        return config
    name = config if isinstance(config, str) else os.getenv("APP_ENV", "development")
    try:
        return CONFIGURATIONS[name.lower()]
    except KeyError as exc:
        choices = ", ".join(CONFIGURATIONS)
        raise ValueError(f"Unknown configuration '{name}'. Choose: {choices}.") from exc


def initialize_extensions(app: Flask) -> None:
    """Bind extensions and authentication callbacks to the app."""
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.session_protection = "strong"

    from app.auth.models import User
    from app.models.activity import Activity  # noqa: F401
    from app.models.application import Application  # noqa: F401
    from app.models.career_profile import CareerProfile  # noqa: F401
    from app.models.contact import Contact  # noqa: F401
    from app.models.dashboard_widget import DashboardWidget  # noqa: F401
    from app.models.integration import GoogleAccountConnection  # noqa: F401
    from app.models.job_posting import JobPosting  # noqa: F401
    from app.models.organization import Organization  # noqa: F401
    from app.models.storage import InstanceStorageConfiguration  # noqa: F401
    from app.models.task import Task  # noqa: F401

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        try:
            return db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None


def register_blueprints(app: Flask) -> None:
    """Register blueprints implemented in this milestone."""
    from app.activities import bp as activities_bp
    from app.ai import bp as ai_bp
    from app.api import bp as api_bp
    from app.applications import bp as applications_bp
    from app.auth import bp as auth_bp
    from app.collaboration import bp as collaboration_bp
    from app.contacts import bp as contacts_bp
    from app.dashboard import bp as dashboard_bp
    from app.documents import bp as documents_bp
    from app.integrations import bp as integrations_bp
    from app.jobs import bp as jobs_bp
    from app.notifications import bp as notifications_bp
    from app.organizations import bp as organizations_bp
    from app.profile import bp as profile_bp
    from app.reports import bp as reports_bp
    from app.search import bp as search_bp
    from app.skills import bp as skills_bp
    from app.storage import bp as storage_bp
    from app.tasks import bp as tasks_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(activities_bp)
    app.register_blueprint(applications_bp)
    app.register_blueprint(organizations_bp)
    app.register_blueprint(contacts_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(skills_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(collaboration_bp)
    app.register_blueprint(storage_bp)
    app.register_blueprint(integrations_bp)
    csrf.exempt(api_bp)
    app.register_blueprint(api_bp)

    @app.get("/health")
    def health():
        from sqlalchemy import text

        db.session.execute(text("SELECT 1"))
        return {"status": "ok"}

    @app.before_request
    def require_authentication():
        """Limit anonymous users to authentication pages and static assets."""
        # Tests and CLI tooling may retain an application context across requests.
        # Always reload Flask-Login's identity from the current request session.
        g.pop("_login_user", None)
        endpoint = request.endpoint or ""
        if (
            endpoint in ("static", "health")
            or endpoint.startswith("auth.")
            or endpoint.startswith("api.")
        ):
            return None
        if not current_user.is_authenticated:
            return login_manager.unauthorized()
        return None


def register_error_handlers(app: Flask) -> None:
    """Register friendly HTTP error pages."""
    app.register_error_handler(
        404, lambda error: (render_template("errors/404.html"), 404)
    )

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault(
            "Referrer-Policy", "strict-origin-when-cross-origin"
        )
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        return response

    @app.errorhandler(500)
    def internal_server_error(error: Exception) -> tuple[str, int]:
        db.session.rollback()
        app.logger.error("Unhandled server error", exc_info=error)
        return render_template("errors/500.html"), 500


def register_commands(app: Flask) -> None:
    """Register database-related Flask CLI commands."""

    @app.cli.command("init-db")
    def init_db_command() -> None:
        """Create tables for a fresh development installation."""
        db.create_all()
        click.echo("Initialized the Career CRM database.")

    @app.cli.command("import-jobs")
    @click.argument(
        "csv_file", type=click.Path(exists=True, dir_okay=False, path_type=Path)
    )
    @click.option(
        "--user-id",
        required=True,
        type=int,
        help="Account owning the import operation.",
    )
    def import_jobs_command(csv_file: Path, user_id: int) -> None:
        """Import a normalized CSV through the adapter interface."""
        from app.auth.models import User
        from app.commands.import_jobs import CSVJobImporter, persist

        if db.session.get(User, user_id) is None:
            raise click.ClickException("User not found.")
        click.echo(f"Imported {persist(CSVJobImporter(csv_file), user_id)} jobs.")

    @app.cli.command("profile-db")
    def profile_db_command() -> None:
        """Print key table sizes for capacity and query planning."""
        from sqlalchemy import func, select

        from app.models import Activity, Application, JobPosting, Organization, Task

        for model in (Organization, JobPosting, Application, Activity, Task):
            click.echo(
                f"{model.__tablename__}: {db.session.scalar(select(func.count(model.id)))}"
            )


def configure_logging() -> None:
    """Configure consistent console logging without duplicate handlers."""
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "stream": "ext://sys.stderr",
                }
            },
            "root": {"level": logging.INFO, "handlers": ["console"]},
        }
    )
