# galaxis-hub (MCP server, prototype)

A read-only MCP server over the existing Supabase `galaxis-hub` DB.
Exposes two tools:

- `search_projects(query)` — fuzzy name → `project_id`.
- `get_project_info(project_id, sections?)` — full or sliced content.

## Setup

```bash
cd APP
uv venv
uv sync
cp .env.example .env
# edit .env with real SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
```

## Run

```bash
uv run python -m galaxis_hub
# or, equivalently:
uv run galaxis-hub
```

The server speaks MCP over stdio. The agent client (Claude desktop,
opencode, etc.) launches this as a subprocess and pipes JSON-RPC
over its stdin/stdout.

## Wire it into your MCP client

Add a `galaxis-hub` entry. Adjust the absolute path in `args` to
match your local clone.

**opencode** (`~/.config/opencode/opencode.json`):

```json
{
  "mcp": {
    "servers": {
      "galaxis-hub": {
        "command": "uv",
        "args": [
          "--directory",
          "/absolute/path/to/galaxis-hub/APP",
          "run",
          "python",
          "-m",
          "galaxis_hub"
        ]
      }
    }
  }
}
```

**Claude desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`
on macOS):

```json
{
  "mcpServers": {
    "galaxis-hub": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/galaxis-hub/APP",
        "run",
        "python",
        "-m",
        "galaxis_hub"
      ]
    }
  }
}
```

Restart the MCP client after editing the config so it picks up the
new server.

## Manual verification

There are no automated tests for the prototype. The success
criterion is the demo scenario in `docs/high-level/demo.md` running
end-to-end against the real Supabase project (owner-confirmed).

## Prerequisite DB views

The server queries `public.v_latest_project_output` and
`public.v_projects` only. See `db/views.sql` and
`docs/task/mcp-prototype/subplan_views.md`.
