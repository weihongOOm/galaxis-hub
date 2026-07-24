from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from fastmcp.server.context import Context
from fastmcp.server.middleware import Middleware, MiddlewareContext
from pydantic import Field
from supabase import create_client

from .config import VALID_SECTIONS, Settings
from .db import GalaxisDB
from .errors import DbError
from .tools import get_project_info as get_project_info_impl
from .tools import search_projects as search_projects_impl

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    stream=sys.stderr,
    force=True,
)
logger = logging.getLogger("galaxis_hub")
logger.setLevel(logging.INFO)
logger.propagate = True

VALID_SECTIONS_LITERAL = Literal[*VALID_SECTIONS]  # type: ignore[valid-type]

SECTIONS_DESCRIPTION = """
Optional list of sections to retrieve. Pass ONLY the bare
section name strings below — do not include the description text.

  kyc: Business profile (company overview, products, target
    market, positioning).
  avatar: Ideal customer personas.
  combined: Combined business + persona snapshot.
  keywords: SEO and paid search keywords.
  google_adcopy: Generated Google Ads copy.
  fb_adcopy: Generated Facebook ad copy.
  meta_audience: Meta Ads audience recommendations.
  google_audience_1: Primary Google Ads audience.
  google_audience_2: Secondary Google Ads audience.
  customer_journey: Customer journey mapping.
  competitors: Competitor analysis.
  seasonality: Seasonal trends.

Unknown names are skipped, not rejected. Skipped names are
returned in the response's `unknown_sections` field so a typo
can be noticed without the call failing.
""".strip()


@asynccontextmanager
async def _lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    settings = Settings()  # type: ignore[call-arg]
    client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    yield {"db": GalaxisDB(client)}


mcp = FastMCP("galaxis-hub", lifespan=_lifespan)


def _emit_audit(
    tool: str,
    project_id: str | None,
    sections: list[str] | None,
    request_id: str,
    duration_ms: int,
    status: str,
) -> None:
    logger.info(
        json.dumps(
            {
                "ts": datetime.now(UTC).isoformat(),
                "tool": tool,
                "project_id": project_id,
                "sections": sections,
                "request_id": request_id,
                "duration_ms": duration_ms,
                "status": status,
            }
        )
    )


def _status_of(result: Any) -> str:
    """Map a ToolResult to an audit 'status' string.

    Priority order:
      1. is_error (raised exception) -> 'exception'
      2. structured_content == {'error': 'db_error'} -> 'db_error'
      3. structured_content has any other 'error' key -> 'error'
      4. otherwise -> 'ok'
    """
    if getattr(result, "is_error", False):
        return "exception"
    sc = getattr(result, "structured_content", None)
    if isinstance(sc, dict):
        if sc.get("error") == "db_error":
            return "db_error"
        if "error" in sc:
            return "error"
    return "ok"


class AuditMiddleware(Middleware):
    """Emit one JSON audit line per tool call to stderr (PRD N-4)."""

    async def on_call_tool(
        self, context: MiddlewareContext, call_next,
    ) -> Any:
        request_id = uuid.uuid4().hex[:12]
        started = time.perf_counter()
        message = context.message
        tool = getattr(message, "name", None) or "unknown"
        arguments = getattr(message, "arguments", None) or {}
        project_id = (
            arguments.get("project_id") if isinstance(arguments, dict) else None
        )
        sections = (
            arguments.get("sections") if isinstance(arguments, dict) else None
        )
        try:
            result = await call_next(context)
        except Exception:
            _emit_audit(
                tool, project_id, sections, request_id,
                int((time.perf_counter() - started) * 1000), "exception",
            )
            raise
        _emit_audit(
            tool, project_id, sections, request_id,
            int((time.perf_counter() - started) * 1000), _status_of(result),
        )
        return result


mcp.add_middleware(AuditMiddleware())


@mcp.tool(
    name="search_projects",
    description=(
        "Find projects by client name. Returns up to 10 matches: "
        "[{UUID, client_name, website}]."
    ),
)
async def search_projects(query: str, ctx: Context) -> list[dict[str, Any]] | dict[str, Any]:
    """Find projects by client name.

    Args:
        query: Substring of the client name (case-insensitive).
    """
    db: GalaxisDB = ctx.lifespan_context["db"]
    try:
        return search_projects_impl(db, query)
    except DbError:
        return {"error": "db_error"}


@mcp.tool(
    name="get_project_info",
    description=(
        "Fetch a project's generated content. Pass a project_id from "
        "search_projects. Optional sections filter returns only those "
        "section names. Unknown section names are skipped and reported "
        "in an `unknown_sections` field; the call does not fail."
    ),
)
async def get_project_info(
    project_id: str,
    sections: Annotated[
        list[VALID_SECTIONS_LITERAL] | None,
        Field(description=SECTIONS_DESCRIPTION),
    ] = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Fetch a project's generated content.

    Args:
        project_id: Project UUID.
        sections: Optional list of section names. Unknown names are
            skipped (returned in `unknown_sections`).
    """
    db: GalaxisDB = ctx.lifespan_context["db"]  # type: ignore[union-attr]
    try:
        return get_project_info_impl(
            db, project_id, list(sections) if sections else None,
        )
    except DbError:
        return {"error": "db_error"}


def main() -> None:
    transport = os.getenv("GALAXIS_TRANSPORT", "stdio")
    if transport == "http":
        os.environ.pop("GALAXIS_TRANSPORT", None)
        mcp.run(transport="http", host="127.0.0.1", port=8000)
    else:
        os.environ.pop("GALAXIS_TRANSPORT", None)
        mcp.run()


if __name__ == "__main__":
    main()
