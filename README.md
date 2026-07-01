# FactIQ Plugin

A plugin for [Claude Code](https://code.claude.com/docs/en/plugins) and
[Codex](https://github.com/openai/codex) that lets your coding agent answer
economic and financial data questions using FactIQ's data — catalog search,
read-only SQL, series lookup, market data, earnings-call search — and publish
the result as a shareable FactIQ chart or report with terminal previews, or
build a bespoke local HTML visualization. The agent orchestrates the whole
analysis itself; no codebase or database access is required, only a FactIQ
account.

Everything runs through the **FactIQ MCP server** (bundled in `.mcp.json`),
which both Claude Code and Codex talk to natively over a single OAuth
connection — discovery, fetching, and publishing alike. There is no API key to
manage. The bundled local scripts, `term_chart.py` and `build_viz.py`, never
touch the network.

## Install

### Claude Code

```
/plugin marketplace add defog-ai/factiq-plugin
/plugin install factiq@factiq
```

This adds the skill (Claude invokes it automatically for economic/financial
data questions), the bundled FactIQ MCP server, and the `/factiq:ask` command:

| Command | Purpose |
|---|---|
| `/factiq:ask <question>` | Run a full analysis and get a shareable chart, terminal chart, or report |

Then run **`/mcp`** once, pick **factiq**, and complete the browser-based
Connect flow to authorize the tools (see below).

#### Enable auto-updates

So you always get the latest skill, MCP tools, and commands without
reinstalling, turn on auto-updates for the marketplace:

1. Run **`/plugin`**.
2. Select **Marketplaces**.
3. Select **factiq**.
4. Toggle **auto-updates** on.

Claude Code will then refresh the plugin automatically whenever this
marketplace changes.

### Codex

```bash
codex plugin marketplace add defog-ai/factiq-plugin
codex plugin add factiq@factiq
```

Then authorize the MCP server:

```bash
codex mcp login factiq
```

Complete the browser sign-in (the same FactIQ login: email, Google, or
passkey). Start a new Codex thread after installation; the skill auto-invokes
for economic/financial data questions.

To update an existing Codex install after this marketplace changes, refresh the
configured marketplace name (`factiq`), then reinstall the plugin:

```bash
codex plugin marketplace upgrade factiq
codex plugin add factiq@factiq
```

<details>
<summary>Alternative: install as a standalone MCP server (no plugin)</summary>

Add the MCP server directly to your Codex config (`~/.codex/config.toml`):

```toml
[mcp_servers.factiq]
url = "https://api.factiq.com/mcp"
```

Then `codex mcp login factiq`. The skill won't auto-invoke without the plugin,
but the MCP tools are available for manual use.

For Claude Code without the plugin:

```bash
claude mcp add --transport http factiq https://api.factiq.com/mcp
```

Then authorize with `/mcp`.
</details>

## Authentication

One credential, no keys. The tools live on the FactIQ MCP server, authorized
over OAuth:

- **Claude Code**: run **`/mcp`**, pick **factiq**, and complete the browser
  sign-in.
- **Codex**: run **`codex mcp login factiq`** and complete the browser sign-in.

The same FactIQ login works everywhere (email, Google, or passkey). The agent
stores and refreshes the token; there is nothing to paste. If the FactIQ tools
ever return an auth error, re-authorize to reconnect — the same connection
covers both data fetching and publishing.

## Contents

- `.mcp.json` — declares the bundled FactIQ MCP server (Streamable HTTP,
  OAuth). Read by both Claude Code and Codex plugin loaders.
- `skills/factiq/SKILL.md` — the skill definition and single source of truth for
  the workflow. Auto-discovered by both Claude Code and Codex from the `skills/`
  directory
- `AGENTS.md` — Codex project-level instructions (points to
  `skills/factiq/SKILL.md`)
- `commands/ask.md` — the `/factiq:ask` slash command (Claude Code)
- `.agents/plugins/marketplace.json` — Codex marketplace entry for
  `codex plugin marketplace add defog-ai/factiq-plugin`
- `scripts/term_chart.py` — stdlib-only renderer that prints ANSI/ASCII
  terminal previews from normal FactIQ ChartSpec JSON and `share_report` report
  objects. It supports bar, simple line, and table fallback renderers.
- `scripts/build_viz.py` — local-only tool to assemble fetched data into a
  self-contained HTML viz and screenshot it headless for iteration. `save`
  copies a tool result's raw JSON out of the harness transcript to disk (no
  retyping) and `assemble` are stdlib-only; `render` installs Playwright +
  Chromium into `~/.factiq/viz-venv` on first use (no effect on your system
  Python)
- `assets/viz-shell.html` — starting-point shell for bespoke visualizations
- `references/` — SQL idioms, ChartSpec/report formats, monetary policy,
  bilateral trade, bilateral economic-policy, and fiscal-policy revenue report
  patterns, the bespoke-viz guide, and dataset schema overview
- `.claude-plugin/` — Claude Code plugin + marketplace manifests
- `.codex-plugin/` — Codex plugin manifest

## Configuration

The bundled MCP server points at `https://api.factiq.com/mcp`. For local
development against a local backend, edit `.mcp.json` in your development
checkout or configure a standalone `factiq` MCP server in Codex or Claude Code
that points at the local URL.

## Security

No secrets belong in this repo, and the plugin holds none — all access goes
through the MCP server's OAuth flow, so the coding agent holds the token and
nothing is written here. The backend enforces a 1 request/second rate limit and
a monthly tool-call quota per plan (publishing counts against the same quota as
the data tools).
