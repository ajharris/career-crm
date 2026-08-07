"""Activity management blueprint."""

from flask import Blueprint

bp = Blueprint("activities", __name__, url_prefix="/activities")

from app.activities import routes  # noqa: E402, F401
