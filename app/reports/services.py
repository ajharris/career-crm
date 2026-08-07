"""Structured reporting data and dependency-free exports."""

import csv
import io
from collections import Counter
from html import escape
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy import select

from app.auth.permissions import actor_id
from app.extensions import db
from app.models import Activity, Application
from app.utils.enums import ApplicationStatus

INTERVIEW = {
    ApplicationStatus.PHONE_INTERVIEW,
    ApplicationStatus.TECHNICAL_INTERVIEW,
    ApplicationStatus.PANEL_INTERVIEW,
    ApplicationStatus.FINAL_INTERVIEW,
    ApplicationStatus.OFFER,
    ApplicationStatus.ACCEPTED,
}
RESPONSE = {ApplicationStatus.SCREENING, *INTERVIEW, ApplicationStatus.REJECTED}


def report_data() -> dict:
    applications = list(
        db.session.scalars(
            select(Application)
            .where(Application.owner_id == actor_id())
            .order_by(Application.application_date)
        )
    )
    activities = list(
        db.session.scalars(
            select(Activity)
            .where(Activity.owner_id == actor_id())
            .order_by(Activity.occurred_at.desc())
        )
    )
    monthly = Counter(
        a.application_date.strftime("%Y-%m") for a in applications if a.application_date
    )
    applied = [a for a in applications if a.status != ApplicationStatus.PLANNED]
    recruiters = Counter(
        a.recruiter_name.strip()
        for a in applications
        if a.recruiter_name and a.recruiter_name.strip()
    )
    organizations = Counter(
        activity.organization.name
        for activity in activities
        if activity.organization is not None
    )
    return {
        "applications": applications,
        "activities": activities,
        "applications_by_month": [
            {"month": m, "count": c} for m, c in sorted(monthly.items())
        ],
        "interview_count": sum(
            a.status in INTERVIEW or a.interview_date is not None for a in applied
        ),
        "interview_rate": (
            round(
                sum(
                    a.status in INTERVIEW or a.interview_date is not None
                    for a in applied
                )
                / len(applied)
                * 100
            )
            if applied
            else 0
        ),
        "response_rate": (
            round(sum(a.status in RESPONSE for a in applied) / len(applied) * 100)
            if applied
            else 0
        ),
        "recruiter_activity": [
            {"name": name, "applications": count}
            for name, count in recruiters.most_common()
        ],
        "organization_history": [
            {"name": name, "activities": count}
            for name, count in organizations.most_common()
        ],
    }


def rows(data):
    yield [
        "Application date",
        "Organization",
        "Job",
        "Status",
        "Recruiter",
        "Interview date",
    ]
    for a in data["applications"]:
        yield [
            a.application_date or "",
            a.job_posting.organization.name,
            a.job_posting.title,
            a.status.label,
            a.recruiter_name or "",
            a.interview_date or "",
        ]


def csv_bytes(data):
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerows(rows(data))
    return stream.getvalue().encode("utf-8-sig")


def xlsx_bytes(data):
    table = list(rows(data))
    shared = []
    for row in table:
        for value in row:
            text = str(value)
            if text not in shared:
                shared.append(text)
    sheet = []
    for ri, row in enumerate(table, 1):
        cells = []
        for ci, value in enumerate(row):
            col = ""
            n = ci + 1
            while n:
                n, rem = divmod(n - 1, 26)
                col = chr(65 + rem) + col
            cells.append(
                f'<c r="{col}{ri}" t="s"><v>{shared.index(str(value))}</v></c>'
            )
        sheet.append(f'<row r="{ri}">{"".join(cells)}</row>')
    out = io.BytesIO()
    with ZipFile(out, "w", ZIP_DEFLATED) as z:
        z.writestr(
            "[Content_Types].xml",
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/></Types>',
        )
        z.writestr(
            "_rels/.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        )
        z.writestr(
            "xl/workbook.xml",
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Applications" sheetId="1" r:id="rId1"/></sheets></workbook>',
        )
        z.writestr(
            "xl/_rels/workbook.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/></Relationships>',
        )
        z.writestr(
            "xl/worksheets/sheet1.xml",
            f'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>{"".join(sheet)}</sheetData></worksheet>',
        )
        z.writestr(
            "xl/sharedStrings.xml",
            f'<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="{len(shared)}" uniqueCount="{len(shared)}">'
            + "".join(f"<si><t>{escape(v)}</t></si>" for v in shared)
            + "</sst>",
        )
    return out.getvalue()


def pdf_bytes(data):
    lines = [
        "Career CRM Application Report",
        f"Interview rate: {data['interview_rate']}%",
        f"Response rate: {data['response_rate']}%",
    ] + [" | ".join(map(str, r))[:100] for r in list(rows(data))[:35]]
    content = (
        "BT /F1 10 Tf 45 760 Td "
        + " ".join(
            f"({line.replace('\\','').replace('(','[').replace(')',']')}) Tj 0 -16 Td"
            for line in lines
        )
        + " ET"
    )
    objects = [
        "1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj",
        "2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj",
        "3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>endobj",
        "4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj",
        f"5 0 obj<</Length {len(content)}>>stream\n{content}\nendstream endobj",
    ]
    pdf = "%PDF-1.4\n"
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf.encode()))
        pdf += obj + "\n"
    xref = len(pdf.encode())
    pdf += (
        "xref\n0 6\n0000000000 65535 f \n"
        + "".join(f"{o:010d} 00000 n \n" for o in offsets[1:])
        + f"trailer<</Size 6/Root 1 0 R>>\nstartxref\n{xref}\n%%EOF"
    )
    return pdf.encode("latin-1", "replace")
