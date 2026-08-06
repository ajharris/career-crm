# app/__init__.py

from flask import Flask

from app.config import Config
from app.extensions import db, login_manager, migrate


def create_app(config_class=Config) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    register_blueprints(app)
    register_commands(app)

    return app


def register_blueprints(app: Flask) -> None:
    from app.applications import bp as applications_bp
    from app.contacts import bp as contacts_bp
    from app.dashboard import bp as dashboard_bp
    from app.jobs import bp as jobs_bp
    from app.organizations import bp as organizations_bp
    from app.tasks import bp as tasks_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(organizations_bp, url_prefix="/organizations")
    app.register_blueprint(contacts_bp, url_prefix="/contacts")
    app.register_blueprint(jobs_bp, url_prefix="/jobs")
    app.register_blueprint(applications_bp, url_prefix="/applications")
    app.register_blueprint(tasks_bp, url_prefix="/tasks")


def register_commands(app: Flask) -> None:
    from app.commands.seed import seed_command

    app.cli.add_command(seed_command)