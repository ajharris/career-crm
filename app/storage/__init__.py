"""Instance storage configuration blueprint."""

from flask import Blueprint

bp = Blueprint("storage", __name__, url_prefix="/settings/storage")

from app.storage import routes  # noqa: E402, F401
