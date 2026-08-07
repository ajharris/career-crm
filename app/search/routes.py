"""Cross-entity search with private saved queries."""

import json

from flask import flash, redirect, render_template, request, url_for
from sqlalchemy import or_, select

from app.auth.permissions import actor_id
from app.extensions import db
from app.models import (
    Activity,
    Application,
    Contact,
    JobPosting,
    Organization,
    SavedSearch,
    Task,
)
from app.search import bp


def _contains(column, query):
    return column.ilike(f"%{query}%")


def search_data(query: str, kind: str = "all") -> dict:
    results: dict[str, list] = {
        "organizations": [],
        "contacts": [],
        "jobs": [],
        "applications": [],
        "activities": [],
        "tasks": [],
    }
    if not query:
        return results
    if kind in ("all", "organizations"):
        results["organizations"] = list(
            db.session.scalars(
                select(Organization)
                .where(
                    or_(
                        _contains(Organization.name, query),
                        _contains(Organization.notes, query),
                    )
                )
                .limit(25)
            )
        )
    if kind in ("all", "contacts"):
        results["contacts"] = list(
            db.session.scalars(
                select(Contact)
                .where(
                    Contact.owner_id == actor_id(),
                    or_(
                        _contains(Contact.first_name, query),
                        _contains(Contact.last_name, query),
                        _contains(Contact.email, query),
                    ),
                )
                .limit(25)
            )
        )
    if kind in ("all", "jobs"):
        results["jobs"] = list(
            db.session.scalars(
                select(JobPosting)
                .where(
                    or_(
                        _contains(JobPosting.title, query),
                        _contains(JobPosting.description, query),
                    )
                )
                .limit(25)
            )
        )
    if kind in ("all", "applications"):
        results["applications"] = list(
            db.session.scalars(
                select(Application)
                .join(JobPosting)
                .where(
                    Application.owner_id == actor_id(),
                    _contains(JobPosting.title, query),
                )
                .limit(25)
            )
        )
    if kind in ("all", "activities"):
        results["activities"] = list(
            db.session.scalars(
                select(Activity)
                .where(
                    Activity.owner_id == actor_id(),
                    or_(
                        _contains(Activity.subject, query),
                        _contains(Activity.notes, query),
                    ),
                )
                .limit(25)
            )
        )
    if kind in ("all", "tasks"):
        results["tasks"] = list(
            db.session.scalars(
                select(Task)
                .where(
                    Task.owner_id == actor_id(),
                    or_(
                        _contains(Task.title, query), _contains(Task.description, query)
                    ),
                )
                .limit(25)
            )
        )
    return results


@bp.route("", methods=["GET", "POST"])
def index():
    query = request.args.get("q", "").strip()
    kind = request.args.get("type", "all")
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if name and query:
            db.session.add(
                SavedSearch(
                    name=name, query=query, filters_json=json.dumps({"type": kind})
                )
            )
            db.session.commit()
            flash("Search saved.", "success")
        return redirect(url_for("search.index", q=query, type=kind))
    saved = list(
        db.session.scalars(
            select(SavedSearch)
            .where(SavedSearch.owner_id == actor_id())
            .order_by(SavedSearch.name)
        )
    )
    return render_template(
        "search/index.html",
        q=query,
        kind=kind,
        results=search_data(query, kind),
        saved=saved,
    )


@bp.post("/saved/<int:saved_id>/delete")
def delete(saved_id):
    saved = db.session.scalar(
        select(SavedSearch).where(
            SavedSearch.id == saved_id, SavedSearch.owner_id == actor_id()
        )
    )
    if saved:
        db.session.delete(saved)
        db.session.commit()
    return redirect(url_for("search.index"))
