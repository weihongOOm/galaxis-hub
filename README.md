# galaxis-hub (MCP server, prototype)

A read-only MCP server over the existing Supabase `galaxis-hub` DB.
Exposes two tools:

- `search_projects(query)` — fuzzy name → `project_id`.
- `get_project_info(project_id, sections?)` — full or sliced content.

## Setup

```bash
cd APP
uv venv
uv sync --extra dev
cp .env.example .env
# edit .env with real SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
```

## Run

```bash
uv run python -m galaxis_hub
```

Speaks MCP over stdio. Wire it into Claude desktop / opencode as a
stdio MCP server.

## Test

```bash
uv run pytest
uv run ruff check
uv run ruff format --check
```

## Prerequisite DB views

The server queries `public.v_latest_project_output` and
`public.v_projects` only. See `db/views.sql` and
`docs/task/mcp-prototype/subplan_views.md`.
