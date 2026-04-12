"""HTML report generator — no Chainlit imports."""

import os
from jinja2 import Environment, FileSystemLoader
from core.models import AnalysisResult


class ReportError(ValueError):
    """Raised when required fields are missing from AnalysisResult."""


# Resolve templates/ relative to this file's package root
_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")


def generate_html(result: AnalysisResult, project_name: str) -> str:
    """Render the Jinja2 report template and return the HTML string.

    Args:
        result: A fully populated AnalysisResult.
        project_name: Display name for the project.

    Returns:
        Rendered HTML string.

    Raises:
        ReportError: if required fields are missing from result.
    """
    missing = _check_required_fields(result)
    if missing:
        raise ReportError(f"AnalysisResult is missing required fields: {', '.join(missing)}")

    env = Environment(
        loader=FileSystemLoader(os.path.abspath(_TEMPLATES_DIR)),
        autoescape=True,
    )
    template = env.get_template("report.html")

    return template.render(
        result=result,
        project_name=project_name,
        generated_at=result.generated_at or "N/A",
    )


def _check_required_fields(result: AnalysisResult) -> list[str]:
    """Return a list of missing required field names."""
    missing = []

    if result.composite is None:
        missing.append("composite")
    if not result.rag_status:
        missing.append("rag_status")
    if result.dimensions is None:
        missing.append("dimensions")
    else:
        for attr in ("time", "cost", "scope", "people", "dependencies", "risks"):
            if getattr(result.dimensions, attr, None) is None:
                missing.append(f"dimensions.{attr}")
    if not result.project_name:
        missing.append("project_name")

    return missing
