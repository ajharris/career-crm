"""Career CRM application factory."""

import logging
import os
from logging.config import dictConfig
from pathlib import Path
from typing import Any

import click
from flask import Flask, render_template

from app.config import CONFIGURATIONS, Config
from app.extensions import csrf, db, login_manager, migrate


def create_app(config: str | type[Config] | dict[str, Any] | None = None) -> Flask:
    """Create and configure a Career CRM application instance."""
    configure_logging()
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(resolve_config(config))
    if isinstance(config, dict):
        app.config.from_mapping(config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    initialize_extensions(app)
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

    from app.auth.models import User
    from app.models.organization import Organization

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        try:
            return db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None


def register_blueprints(app: Flask) -> None:
    """Register blueprints implemented in this milestone."""
    from app.dashboard import bp as dashboard_bp
    from app.organizations import bp as organizations_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(organizations_bp)


def register_error_handlers(app: Flask) -> None:
    """Register friendly HTTP error pages."""
    app.register_error_handler(
        404, lambda error: (render_template("errors/404.html"), 404)
    )

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
