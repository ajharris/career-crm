"""Pluggable job-import infrastructure."""

import csv
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ImportedJob:
    title: str
    organization: str
    posting_url: str | None = None
    location: str | None = None
    description: str | None = None


class JobImporter(ABC):
    """Adapter contract for career pages, RSS, ATS exports, and manual files."""

    @abstractmethod
    def load(self) -> Iterable[ImportedJob]: ...


class CSVJobImporter(JobImporter):
    def __init__(self, path: Path):
        self.path = path

    def load(self):
        with self.path.open(newline="", encoding="utf-8-sig") as stream:
            for row in csv.DictReader(stream):
                if row.get("title") and row.get("organization"):
                    yield ImportedJob(
                        title=row["title"].strip(),
                        organization=row["organization"].strip(),
                        posting_url=row.get("posting_url") or None,
                        location=row.get("location") or None,
                        description=row.get("description") or None,
                    )


def persist(importer, user_id):
    from sqlalchemy import select

    from app.extensions import db
    from app.models import JobPosting, Organization

    created = 0
    for item in importer.load():
        organization = db.session.scalar(
            select(Organization).where(Organization.name == item.organization)
        )
        if organization is None:
            organization = Organization(
                name=item.organization, created_by_id=user_id, updated_by_id=user_id
            )
            db.session.add(organization)
            db.session.flush()
        duplicate = db.session.scalar(
            select(JobPosting.id).where(
                JobPosting.organization_id == organization.id,
                JobPosting.title == item.title,
                JobPosting.posting_url == item.posting_url,
            )
        )
        if duplicate is None:
            db.session.add(
                JobPosting(
                    title=item.title,
                    organization=organization,
                    posting_url=item.posting_url,
                    location=item.location,
                    description=item.description,
                    created_by_id=user_id,
                    updated_by_id=user_id,
                )
            )
            created += 1
    db.session.commit()
    return created
