"""External account integrations."""

from flask import Blueprint

bp = Blueprint("integrations", __name__, url_prefix="/settings/integrations")

from app.integrations import routes  # noqa: E402, F401
