"""Job posting management blueprint."""

from flask import Blueprint


bp = Blueprint("jobs", __name__, url_prefix="/jobs")

from app.jobs import routes  # noqa: E402, F401
