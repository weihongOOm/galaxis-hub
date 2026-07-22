from __future__ import annotations

import re
from typing import Any

from ..config import VALID_SECTIONS
from ..db import GalaxisDB
from ..errors import ProjectNotFoundError

_SEPARATOR_PATTERN = re.compile(r"[\s:,\-()/]+")
_CASE_INSENSITIVE_SECTIONS: dict[str, str] = {
    name.lower(): name for name in VALID_SECTIONS
}


def _resolve_section(raw: str) -> str | None:
    """Try to recover a canonical section name from a possibly-verbose input.

    Resolution order:
      1. Exact case-insensitive match against VALID_SECTIONS.
      2. First whitespace/separator-delimited token that case-insensitively
         matches a VALID_SECTIONS entry.

    Returns the canonical (lowercase) name, or None if nothing matched.
    Token-boundary matching is intentional: prefix matching (e.g.
    ``"competitorsxyz"`` -> ``"competitors"``) is rejected to avoid
    false positives.
    """
    lowered = raw.lower()
    canonical = _CASE_INSENSITIVE_SECTIONS.get(lowered)
    if canonical is not None:
        return canonical
    for token in _SEPARATOR_PATTERN.split(raw):
        if not token:
            continue
        canonical = _CASE_INSENSITIVE_SECTIONS.get(token.lower())
        if canonical is not None:
            return canonical
    return None


def _partition_sections(
    sections: list[str] | None,
) -> tuple[list[str] | None, list[str]]:
    """Strip, classify, and dedupe `sections` into (valid, unknown) lists.

    Each input is first cleaned (whitespace stripped, empties dropped) and
    then passed through ``_resolve_section`` so that a verbose string like
    ``"kyc: Business profile..."`` still resolves to ``"kyc"``. Inputs that
    don't resolve are reported verbatim in ``unknown`` so the caller can see
    what was rejected.

    Both lists preserve first-occurrence order and are deduped. ``valid`` is
    deduped by canonical name; ``unknown`` is deduped case-insensitively.
    Returns ``(None, [])`` when ``sections`` is ``None`` or all-empty.
    """
    if sections is None:
        return None, []
    cleaned = [s.strip() for s in sections if s and s.strip()]
    if not cleaned:
        return None, []

    seen_valid: set[str] = set()
    valid: list[str] = []
    seen_unknown: set[str] = set()
    unknown: list[str] = []
    for s in cleaned:
        canonical = _resolve_section(s)
        if canonical is not None:
            if canonical not in seen_valid:
                seen_valid.add(canonical)
                valid.append(canonical)
        else:
            key = s.lower()
            if key not in seen_unknown:
                seen_unknown.add(key)
                unknown.append(s)
    return valid, unknown


def get_project_info(
    db: GalaxisDB,
    project_id: str,
    sections: list[str] | None = None,
) -> dict[str, Any]:
    """Fetch a project's generated content, optionally sliced to a list of sections.

    Unknown section names are skipped, not fatal: the response includes the
    sections that did resolve plus an `unknown_sections` list. If *every*
    requested section is unknown, the response is the F-7 envelope
    (`{"error": "unknown_section", "section": [...], "valid_sections": [...]}`)
    so the agent still gets a discoverability hint.

    Returns:
      On success (all-or-some valid sections):
        {"project_id": str, "sections": {section_name: content, ...},
         "unknown_sections": [...]  # only present when non-empty}
      On all-unknown:
        {"error": "unknown_section", "section": [...], "valid_sections": [...]}
      On unknown project:
        {"error": "project_not_found", "project_id": str}
    """
    if not project_id or not project_id.strip():
        return {"error": "project_not_found", "project_id": project_id}

    valid, unknown = _partition_sections(sections)

    if valid is None and unknown:
        # Every requested section is unknown; nothing to query. Return the
        # F-7 envelope with all unknowns (and a project_id for context-free
        # routing, mirroring the project_not_found envelope).
        return {
            "error": "unknown_section",
            "section": unknown,
            "valid_sections": list(VALID_SECTIONS),
        }

    try:
        rows = db.get_latest_output(project_id.strip(), valid)
    except ProjectNotFoundError:
        return {"error": "project_not_found", "project_id": project_id}

    grouped: dict[str, str] = {}
    for row in rows:
        grouped[row["section"]] = row["content"]
    result: dict[str, Any] = {"project_id": project_id, "sections": grouped}
    if unknown:
        result["unknown_sections"] = unknown
    return result
