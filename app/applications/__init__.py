"""Application management blueprint."""

from flask import Blueprint


bp = Blueprint("applications", __name__, url_prefix="/applications")

from app.applications import routes  # noqa: E402, F401
