"""Organization management blueprint."""

from flask import Blueprint


bp = Blueprint("organizations", __name__, url_prefix="/organizations")

from app.organizations import routes  # noqa: E402, F401
