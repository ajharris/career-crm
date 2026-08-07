from flask import Blueprint

bp = Blueprint("collaboration", __name__, url_prefix="/community")
from app.collaboration import routes  # noqa:E402,F401
