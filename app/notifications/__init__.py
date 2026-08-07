from flask import Blueprint

bp = Blueprint("notifications", __name__, url_prefix="/notifications")
from app.notifications import routes  # noqa: E402,F401
