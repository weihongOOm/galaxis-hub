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

You don't need to `source .venv/bin/activate` — every command below uses
`uv run`, which activates the venv for that one command.

By default the server speaks MCP over stdio. To run it as an HTTP
server (reachable at `http://127.0.0.1:8000/mcp`), export
`GALAXIS_TRANSPORT=http` in your shell before launching. **Do not
put it in `.env`** — only the two Supabase vars above are loaded from
`.env`; the transport flag is read directly from the process
environment. No code change needed.

## Run

```bash
# default: stdio (for Claude desktop / opencode as a subprocess)
uv run python -m galaxis_hub
# or equivalently:
uv run galaxis-hub

# HTTP (for testing from a web client or remote opencode):
GALAXIS_TRANSPORT=http uv run python -m galaxis_hub
```

In stdio mode, the agent client (Claude desktop, opencode, etc.)
launches this as a subprocess and pipes JSON-RPC over its stdin/stdout.
In HTTP mode, the server is reachable at `http://127.0.0.1:8000/mcp`.

## Smoke-test in the inspector

The FastMCP CLI ships an inspector:

```bash
uv run fastmcp dev src/galaxis_hub/server.py:mcp
```

The `mcp[cli]` inspector also still works, same syntax:

```bash
uv run mcp dev src/galaxis_hub/server.py:mcp
```

## Wire it into your MCP client

Add a `galaxis-hub` entry. Adjust the absolute path in `args` to
match your local clone.

**opencode** (`~/.config/opencode/opencode.json`):

```json
{
  "mcp": {
    "galaxis-hub": {
      "type": "local",
      "command": [
        "uv",
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
