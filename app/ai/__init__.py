"""Optional AI assistance boundary."""

from flask import Blueprint

bp = Blueprint("ai", __name__, url_prefix="/assistant")
from app.ai import routes  # noqa:E402,F401
