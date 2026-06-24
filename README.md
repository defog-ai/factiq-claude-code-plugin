# FactIQ Claude Code Plugin

A [Claude Code plugin](https://code.claude.com/docs/en/plugins) that lets
Claude answer economic and financial data questions using FactIQ's data —
catalog search, read-only SQL, series lookup, market data, earnings-call
search — plus shareable chart/report publishing and bespoke local HTML
visualizations. Claude orchestrates the whole analysis itself; no codebase or
database access is required, only a FactIQ account.

The data tools run on the **FactIQ MCP server** (bundled in `.mcp.json`), which
Claude Code talks to natively. Publishing a chart or report, and building local
visualizations, go through a small bundled CLI — the two things the read-only
MCP deliberately does not do.

## Install

Inside Claude Code:

```
/plugin marketplace add defog-ai/factiq-claude-code-plugin
/plugin install factiq@factiq
```

This adds the skill (Claude invokes it automatically for economic/financial
data questions), the bundled FactIQ MCP server, and three slash commands:

| Command | Purpose |
|---|---|
| `/factiq:set-key` | Store your FactIQ API key for publishing (guides you through getting one) |
| `/factiq:status` | Check the publishing key, plan, and monthly usage |
| `/factiq:ask <question>` | Run a full analysis and get a shareable chart or report |

After installing, run **`/mcp`**, pick **factiq**, and complete the
browser-based Connect flow once to authorize the data tools (see below).

<details>
<summary>Alternative: install as a plain skill (no slash commands / no MCP)</summary>

```bash
git clone git@github.com:defog-ai/factiq-claude-code-plugin.git ~/.claude/skills/factiq
```

The skill auto-invokes the same way. As a plain skill the bundled `.mcp.json`
is not loaded automatically — add the MCP server yourself with
`claude mcp add --transport http factiq https://api.worlddb.ai/mcp`, then
authorize it with `/mcp`. Store your publishing key with
`python3 ~/.claude/skills/factiq/scripts/factiq.py set-key`.
</details>

## Authentication

There are two independent credentials, because data and publishing go through
different surfaces.

### Data tools — OAuth (no key to copy)

The data tools live on the FactIQ MCP server. Run **`/mcp`** in Claude Code,
pick **factiq**, and complete the browser sign-in (the same FactIQ login:
email, Google, or passkey). Claude Code stores and refreshes the token; there
is nothing to paste. If the `mcp__plugin_factiq_*` tools ever return an auth
error, re-run `/mcp` to reconnect.

### Publishing — a `fiq_` API key

`share-chart` and `share-report` use a per-user API key:

1. Sign in at [factiq.com](https://factiq.com) and open
   **[Settings → Security](https://factiq.com/settings/security)**.
2. In the **API key** section, click **Generate API key** (or **Regenerate**
   if one already exists — this revokes the old key).
3. Copy the `fiq_...` key immediately — it is shown only once and cannot be
   retrieved later (the server stores only a hash).

Then run `/factiq:set-key` in Claude Code and follow the instructions. The key
is verified against the API and cached in `~/.factiq/config.json` (chmod 600) —
never stored in this folder. Alternatively, set the `FACTIQ_API_KEY` env var,
which overrides the config. You only need this key when publishing; pure data
analysis works with just the MCP connection.

## Contents

- `.mcp.json` — declares the bundled FactIQ MCP server (Streamable HTTP,
  OAuth)
- `SKILL.md` — the skill definition Claude loads (setup, workflow, limits)
- `commands/` — the `/factiq:*` slash commands
- `scripts/factiq.py` — self-contained stdlib-only CLI for the FactIQ
  publishing endpoints and key management — `set-key`, `whoami`,
  `share-chart`, `share-report` (Python 3.10+, no dependencies)
- `scripts/build_viz.py` — local-only tool to assemble fetched data into a
  self-contained HTML viz and screenshot it headless for iteration. `assemble`
  is stdlib-only; `render` installs Playwright + Chromium into
  `~/.factiq/viz-venv` on first use (no effect on your system Python)
- `assets/viz-shell.html` — starting-point shell for bespoke visualizations
- `references/` — SQL idioms, ChartSpec/report formats, the bespoke-viz guide,
  and dataset schema overview
- `.claude-plugin/` — plugin + marketplace manifests

## Configuration

The MCP server defaults to `https://api.worlddb.ai/mcp`. For local development
against a local backend, set `FACTIQ_MCP_URL=http://localhost:8000/mcp` before
starting Claude Code (it expands in `.mcp.json`).

The publishing CLI targets `https://api.worlddb.ai` (API) and
`https://www.factiq.com` (share links) by default. Override with
`FACTIQ_API_URL` / `FACTIQ_WEB_URL` env vars or `--base-url` / `--web-url`
flags — e.g. `http://localhost:8000` and `http://localhost:3000`.

`set-key` remembers the URL it verified the key against in the config file. If
that remembered URL later stops working (say, a local dev server that is no
longer running), the next `set-key` run falls back to verifying against the
default API and saves that instead — explicit `--base-url` / `FACTIQ_API_URL`
overrides are always honored as given, with no fallback.

## Security

No secrets belong in this repo. Data-tool access uses the MCP server's OAuth
flow — Claude Code holds the token, nothing is written here. Publishing uses a
per-user API key (`set-key` prompts via getpass; `FACTIQ_API_KEY` env var also
works); the key lives only in `~/.factiq/config.json`. The backend stores keys
hashed, and enforces a 1 request/second rate limit and a monthly tool-call
quota per plan.
