from __future__ import annotations

from typing import Any

from ..config import VALID_SECTIONS, is_valid_section
from ..db import GalaxisDB
from ..errors import ProjectNotFoundError, UnknownSectionError


def _validate_sections(sections: list[str] | None) -> list[str] | None:
    if sections is None:
        return None
    cleaned = [s for s in (s.strip() for s in sections) if s]
    if not cleaned:
        return None
    unknown = [s for s in cleaned if not is_valid_section(s)]
    if unknown:
        raise UnknownSectionError(unknown[0])
    seen: set[str] = set()
    deduped: list[str] = []
    for s in cleaned:
        if s not in seen:
            seen.add(s)
            deduped.append(s)
    return deduped


def get_project_info(
    db: GalaxisDB,
    project_id: str,
    sections: list[str] | None = None,
) -> dict[str, Any]:
    """Fetch a project's generated content, optionally sliced to a list of sections.

    Returns:
      On success:
        {"project_id": str, "sections": {section_name: content, ...}}
      On unknown project:
        {"error": "project_not_found", "project_id": str}
      On unknown section:
        {"error": "unknown_section", "section": str, "valid_sections": [...]}
    """
    if not project_id or not project_id.strip():
        return {"error": "project_not_found", "project_id": project_id}

    try:
        validated = _validate_sections(sections)
    except UnknownSectionError as exc:
        return {
            "error": "unknown_section",
            "section": exc.section,
            "valid_sections": list(VALID_SECTIONS),
        }

    try:
        rows = db.get_latest_output(project_id.strip(), validated)
    except ProjectNotFoundError:
        return {"error": "project_not_found", "project_id": project_id}

    grouped: dict[str, str] = {}
    for row in rows:
        grouped[row["section"]] = row["content"]
    return {"project_id": project_id, "sections": grouped}
