from flask import Response, render_template

from app.reports import bp
from app.reports.services import csv_bytes, pdf_bytes, report_data, xlsx_bytes


@bp.get("")
def index():
    return render_template("reports/index.html", data=report_data())


@bp.get("/applications.<format>")
def export(format):
    exporters = {
        "csv": (csv_bytes, "text/csv"),
        "xlsx": (
            xlsx_bytes,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
        "pdf": (pdf_bytes, "application/pdf"),
    }
    if format not in exporters:
        return ("Not found", 404)
    fn, mime = exporters[format]
    return Response(
        fn(report_data()),
        mimetype=mime,
        headers={
            "Content-Disposition": f"attachment; filename=career-crm-report.{format}"
        },
    )
