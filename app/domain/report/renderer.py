from __future__ import annotations

from app.domain.report.models import GeneratedReport, ReportFormat


def _format_citations(cited_source_ids: list[str]) -> str:
    if not cited_source_ids:
        return ""
    return " [Sources: " + ", ".join(cited_source_ids) + "]"


def render_markdown(report: GeneratedReport) -> str:
    lines = [f"# {report.title}", ""]
    if report.overview:
        lines.extend([report.overview, ""])
    for section in report.sections:
        lines.append(f"## {section.title}")
        lines.append(f"{section.body}{_format_citations(section.cited_source_ids)}")
        lines.append("")
    return "\n".join(lines).strip()


def render_bullet_summary(report: GeneratedReport) -> str:
    lines = [f"# {report.title}", ""]
    if report.overview:
        lines.extend([f"- Overview: {report.overview}", ""])
    for section in report.sections:
        lines.append(f"- {section.title}: {section.body}{_format_citations(section.cited_source_ids)}")
    return "\n".join(lines).strip()


def render_report_content(report: GeneratedReport, output_format: ReportFormat) -> str:
    if output_format == "json":
        return report.to_pretty_json()
    if output_format == "bullet_summary":
        return render_bullet_summary(report)
    return render_markdown(report)
