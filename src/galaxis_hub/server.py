from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool
from supabase import create_client

from .config import VALID_SECTIONS, Settings
from .db import GalaxisDB
from .errors import DbError
from .tools import get_project_info, search_projects

logger = logging.getLogger("galaxis_hub")
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler(sys.stderr)
_handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(_handler)


def _audit(
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


def build_server(settings: Settings) -> Server:
    """Construct the FastMCP-compatible Server with both tools registered."""
    client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    db = GalaxisDB(client)
    server = Server("galaxis-hub")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="search_projects",
                description=(
                    "Find projects by client name. Returns up to 10 matches: "
                    "[{UUID, client_name, website}]."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Substring of the client name.",
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="get_project_info",
                description=(
                    "Fetch a project's generated content. Pass a project_id from "
                    "search_projects. Optional sections filter returns only those "
                    "section names (see schema enum). Unknown section names are "
                    "skipped and reported in an `unknown_sections` field; the call "
                    "does not fail."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project UUID.",
                        },
                        "sections": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": list(VALID_SECTIONS),
                            },
                            "description": (
                                "Optional list of sections to retrieve. "
                                "Use ONLY the bare section name strings below "
                                "— do NOT include the description text.\n"
                                "\n"
                                "  kyc, avatar, combined, keywords, "
                                "google_adcopy, fb_adcopy, meta_audience, "
                                "google_audience_1, google_audience_2, "
                                "customer_journey, competitors, seasonality\n"
                                "\n"
                                "Section meanings (for context only — never "
                                "include in the value):\n"
                                "- kyc: Business profile (company overview, "
                                "products, target market, positioning).\n"
                                "- avatar: Ideal customer personas.\n"
                                "- keywords: SEO and paid search keywords.\n"
                                "- google_adcopy: Generated Google Ads copy.\n"
                                "- fb_adcopy: Generated Facebook ad copy.\n"
                                "- meta_audience: Meta Ads audience "
                                "recommendations.\n"
                                "- google_audience_1: Primary Google Ads "
                                "audience.\n"
                                "- google_audience_2: Secondary Google Ads "
                                "audience.\n"
                                "- customer_journey: Customer journey "
                                "mapping.\n"
                                "- competitors: Competitor analysis.\n"
                                "- seasonality: Seasonal trends.\n"
                                "\n"
                                "Unknown names are skipped, not rejected. "
                                "Skipped names are returned in the response's "
                                "`unknown_sections` field so a typo can be "
                                "noticed without the call failing."
                            ),
                        },
                    },
                    "required": ["project_id"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        request_id = uuid.uuid4().hex[:12]
        started = time.perf_counter()
        project_id = arguments.get("project_id")
        sections = arguments.get("sections")
        try:
            if name == "search_projects":
                result = search_projects(db, arguments.get("query", ""))
            elif name == "get_project_info":
                result = get_project_info(db, project_id or "", sections)
        except DbError:
            result = {"error": "db_error"}
            _audit(
                name,
                project_id,
                sections,
                request_id,
                int((time.perf_counter() - started) * 1000),
                "db_error",
            )
            return [TextContent(type="text", text=json.dumps(result))]

        status = "error" if isinstance(result, dict) and "error" in result else "ok"
        _audit(
            name,
            project_id,
            sections,
            request_id,
            int((time.perf_counter() - started) * 1000),
            status,
        )
        return [TextContent(type="text", text=json.dumps(result))]

    return server


async def _run() -> None:
    settings = Settings()  # type: ignore[call-arg]
    server = build_server(settings)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
