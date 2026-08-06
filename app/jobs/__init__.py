# app/jobs/__init__.py

from flask import Blueprint

bp = Blueprint(
    "jobs",
    __name__,
    template_folder="../templates/jobs",
)

from app.jobs import routes