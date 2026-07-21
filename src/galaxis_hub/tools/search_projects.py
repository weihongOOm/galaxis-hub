from __future__ import annotations

from typing import Any

from ..db import GalaxisDB


def search_projects(db: GalaxisDB, query: str) -> list[dict[str, Any]]:
    """Resolve a fuzzy client name to a list of {id, client_name, website}.

    Args:
      query: Substring of the client name (case-insensitive).
    """
    query = (query or "").strip()
    if not query:
        return []
    return db.search_projects(query, limit=10)
