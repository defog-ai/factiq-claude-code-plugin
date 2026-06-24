# FactIQ Claude Code Plugin

A [Claude Code plugin](https://code.claude.com/docs/en/plugins) that lets
Claude answer economic and financial data questions using FactIQ's data —
catalog search, read-only SQL, series lookup, market data, earnings-call
search — and publish the result as a shareable FactIQ chart or report, or as a
bespoke local HTML visualization. Claude orchestrates the whole analysis
itself; no codebase or database access is required, only a FactIQ account.

Everything runs through the **FactIQ MCP server** (bundled in `.mcp.json`),
which Claude Code talks to natively over a single OAuth connection — discovery,
fetching, and publishing alike. There is no API key to manage. The one bundled
script, `build_viz.py`, is local-only (it builds HTML visualizations and never
touches the network).

## Install

Inside Claude Code:

```
/plugin marketplace add defog-ai/factiq-claude-code-plugin
/plugin install factiq@factiq
```

This adds the skill (Claude invokes it automatically for economic/financial
data questions), the bundled FactIQ MCP server, and the `/factiq:ask` command:

| Command | Purpose |
|---|---|
| `/factiq:ask <question>` | Run a full analysis and get a shareable chart or report |

Then run **`/mcp`** once, pick **factiq**, and complete the browser-based
Connect flow to authorize the tools (see below). That single connection covers
both fetching data and publishing.

<details>
<summary>Alternative: install as a plain skill (no slash command / no MCP)</summary>

```bash
git clone git@github.com:defog-ai/factiq-claude-code-plugin.git ~/.claude/skills/factiq
```

The skill auto-invokes the same way. As a plain skill the bundled `.mcp.json`
is not loaded automatically — add the MCP server yourself with
`claude mcp add --transport http factiq https://api.worlddb.ai/mcp`, then
authorize it with `/mcp`.
</details>

## Authentication

One credential, no keys. The tools live on the FactIQ MCP server; Claude Code
authorizes them over OAuth. Run **`/mcp`**, pick **factiq**, and complete the
browser sign-in (the same FactIQ login: email, Google, or passkey). Claude Code
stores and refreshes the token; there is nothing to paste. If the
`mcp__plugin_factiq_*` tools ever return an auth error, re-run `/mcp` to
reconnect — the same connection authorizes publishing, so this fixes publish
failures too.

## Contents

- `.mcp.json` — declares the bundled FactIQ MCP server (Streamable HTTP,
  OAuth)
- `SKILL.md` — the skill definition Claude loads (setup, workflow, limits)
- `commands/ask.md` — the `/factiq:ask` slash command
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

## Security

No secrets belong in this repo, and the plugin holds none — all access goes
through the MCP server's OAuth flow, so Claude Code holds the token and nothing
is written here. The backend enforces a 1 request/second rate limit and a
monthly tool-call quota per plan (publishing counts against the same quota as
the data tools).
