from flask import Blueprint

bp = Blueprint("search", __name__, url_prefix="/search")
from app.search import routes  # noqa: E402,F401
