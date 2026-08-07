"""Document management blueprint."""

from flask import Blueprint

bp = Blueprint("documents", __name__, url_prefix="/documents")
from app.documents import routes  # noqa: E402,F401
