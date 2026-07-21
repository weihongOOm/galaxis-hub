from __future__ import annotations

from typing import Any, Protocol

from .errors import DbError, ProjectNotFoundError


class _SupabaseLike(Protocol):
    """The subset of supabase.Client that GalaxisDB actually uses."""

    def table(self, name: str) -> _TableQuery: ...


class _TableQuery(Protocol):
    def select(self, columns: str) -> _TableQuery: ...
    def ilike(self, column: str, pattern: str) -> _TableQuery: ...
    def eq(self, column: str, value: Any) -> _TableQuery: ...
    def order(self, column: str, *, desc: bool = False) -> _TableQuery: ...
    def limit(self, n: int) -> _TableQuery: ...
    def execute(self) -> Any: ...


class GalaxisDB:
    """Thin wrapper around the Supabase client. Only queries views — never base tables."""

    def __init__(self, client: _SupabaseLike) -> None:
        self._client = client

    def search_projects(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Return up to `limit` projects whose client_name contains `query` (case-insensitive)."""
        try:
            res = (
                self._client.table("v_projects")
                .select("id,client_name,website")
                .ilike("client_name", f"%{query}%")
                .order("client_name", desc=False)
                .limit(limit)
                .execute()
            )
        except Exception as exc:  # noqa: BLE001 — boundary; re-raise as our own type
            raise DbError(str(exc)) from exc
        return list(res.data or [])

    def get_latest_output(
        self,
        project_id: str,
        sections: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Return the most recent row per matching section for `project_id`.

        Raises ProjectNotFoundError if the project has no rows at all.
        """
        try:
            q = (
                self._client.table("v_latest_project_output")
                .select("project_id,section,content,created_at")
                .eq("project_id", project_id)
            )
            if sections:
                # supabase-py 2.x exposes .in_(column, values) for "column in (...)".
                # If a future client version removes it, fail loudly rather than silently
                # producing a wrong query.
                in_filter = getattr(q, "in_", None)
                if in_filter is None:
                    raise RuntimeError("Supabase client is missing .in_(); update galaxis_hub.db.")
                q = in_filter("section", sections)
            res = q.order("section", desc=False).execute()
        except Exception as exc:  # noqa: BLE001
            raise DbError(str(exc)) from exc

        rows = list(res.data or [])
        if not rows:
            # Confirm the project itself exists before declaring "not found".
            try:
                proj_res = (
                    self._client.table("v_projects")
                    .select("id")
                    .eq("id", project_id)
                    .limit(1)
                    .execute()
                )
            except Exception as exc:  # noqa: BLE001
                raise DbError(str(exc)) from exc
            if not (proj_res.data or []):
                raise ProjectNotFoundError(project_id)
        return rows
