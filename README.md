# FactIQ - a realtime updated finance and economy database for AI Agents

Turn your agent into an finance and economy analyst. This plugin for
[Claude Code](https://code.claude.com/docs/en/plugins) and
[Codex](https://github.com/openai/codex) gives the agent direct access to
FactIQ's warehouse of official statistics — SEC filings, US, China, India, Korea, IMF,
World Bank, and more — plus live market data and earnings-call intelligence.
The agent discovers series, runs read-only SQL on FactIQ's database, computes 
derived metrics, and publishes the result as a shareable FactIQ chart or report, 
a terminal preview, or a bespoke local HTML visualization.

No codebase or hosted database is required — only a free FactIQ account. You can easily combine
FactIQ with other skills in your codebase.

## Install

### Claude Code

```
/plugin marketplace add defog-ai/factiq-plugin
/plugin install factiq@factiq
/reload-plugins
```

Run **`/reload-plugins`** after installing so Claude Code picks up the new
skill, MCP server, and command in the current session (otherwise they only
appear the next time you start Claude Code).

This adds the skill (Claude invokes it automatically for economic/financial
data questions), the bundled FactIQ MCP server, and the `/factiq:ask` command:

| Command | Purpose |
|---|---|
| `/factiq:ask <question>` | Run a full analysis and get a shareable chart, terminal chart, or report |

Finally, authenticate the MCP server:

1. Run **`/mcp`**.
2. Select **factiq** from the list of servers.
3. Choose **Authenticate** (or **Connect**) to open the browser sign-in.
4. Complete the FactIQ login (email, Google, or passkey) and return to Claude
   Code — the FactIQ tools are now authorized.

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


## How it works

**Your coding agent is the analyst**: it decomposes the question, finds the data, does 
the math, authors the output, and publishes it - all through tool calls to
the **FactIQ MCP server** (bundled in `.mcp.json`), which Claude Code and
Codex talk to natively over a single OAuth connection.

```
┌─────────────────────────────┐
│  Claude Code / Codex        │
│  + factiq skill (SKILL.md)  │      the agent orchestrates everything
└──────────────┬──────────────┘
               │  MCP over HTTP (one OAuth connection)
┌──────────────▼──────────────┐
│  FactIQ MCP server          │
│                             │
│  discover   search_datasets, describe_dataset, search_series,
│             get_data_catalog
│  fetch      run_sql (read-only), get_series, get_market_data,
│             search_earnings
│  publish    share_chart, share_report
└──────────────┬──────────────┘
               │
┌──────────────▼──────────────┐
│  FactIQ data warehouse      │      25+ official sources, one schema
│  + factiq.com share pages   │      published charts/reports render here
└─────────────────────────────┘
```

## Under the hood

The reason a single skill can query BLS unemployment, Chinese customs flows,
RBI monetary data, and World Bank indicators with the same SQL idioms: **every
data source in the backend is normalized into the same three core tables**,
identical in every schema:

| Table | What it holds |
|---|---|
| `series` | The catalog — one row per series: id, title, description, dataset, frequency, units, seasonality, geography, time coverage |
| `data_points` | The values — `(series_id, time, value)`, indexed for fast retrieval |
| `dimensions` | Faceted metadata — `(series_id, dimension_type, dimension_code, dimension_name)`, e.g. `partner`, `flow`, `commodity`, `hs_level` for trade data |

Our ingestion pipelines do the hard work of flattening each source's bespoke
format — BLS flat files, BEA APIs, customs records, RBI releases — into this
shape, so the agent learns the model once and it works everywhere. Discovery,
pivoting, and filtering follow the same patterns across all ~20 schemas; the
recipes live in [`references/sql-guide.md`](references/sql-guide.md).

### What's in the warehouse

| Region | Schemas |
|---|---|
| United States | SEC filings data, BLS (employment, CPI, JOLTS, OEWS), Census (trade incl. HS-level, retail, housing), BEA (GDP, income), EIA (energy), USDA ERS, BTS (transportation), earnings-call intelligence |
| China | NBS macro indicators, GACC customs (HS-level trade) |
| India | MOSPI (CPI, WPI, IIP, GDP), RBI (banking, rates, forex), DGCI&S trade (HS-level), city traffic |
| South Korea | KCS customs (HS-level trade) |
| Global | IMF, World Bank, Singapore SingStat, live market data (quotes, fundamentals, FX, commodities) |

`references/schemas.md` has the static overview; the `get_data_catalog` tool
returns the live, authoritative version.

## Contents

- `.mcp.json` — declares the bundled FactIQ MCP server (Streamable HTTP,
  OAuth). Read by both Claude Code and Codex plugin loaders.
- `skills/factiq/SKILL.md` — the skill definition and single source of truth for
  the workflow. Auto-discovered by both Claude Code and Codex from the `skills/`
  directory
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
- `references/` — SQL idioms, ChartSpec/report formats, domain playbooks
  (monetary policy, bilateral trade, bilateral economic policy, fiscal-policy
  revenue), the bespoke-viz guide, and dataset schema overview
- `.claude-plugin/` — Claude Code plugin + marketplace manifests
- `.codex-plugin/` — Codex plugin manifest

## Contributing

Contributions are welcome — this plugin is meant to grow with its community.
Open an issue or a pull request.

### Bespoke skills (domain playbooks) — the highest-leverage contribution

The most valuable thing you can add is a **domain playbook**: a reference file
that teaches the agent how to answer a whole class of questions well. The
existing ones live in `references/` and are the pattern to follow:

- [`references/monetary-policy.md`](references/monetary-policy.md) — central
  bank policy stance, administered rates, OMO, balance-sheet context
- [`references/bilateral-trade.md`](references/bilateral-trade.md) —
  country-pair trade trends, product drivers, mirror-statistics caveats
- [`references/fiscal-policy-revenue.md`](references/fiscal-policy-revenue.md)
  — government receipts, tax composition, distributional detail

A good playbook contains:

1. **A trigger** — which question shapes it covers ("latest trend in trade
   between A and B", "explain the Fed's stance"), wired into `SKILL.md` so the
   agent reads the playbook *before* fetching.
2. **Required coverage** — the dimensions a complete answer must address, so
   the agent doesn't stop at the first obvious chart.
3. **Ready SQL templates** — tested queries against the three-table schema for
   the key computations (latest-month YoY, YTD comparisons, top-N drivers).
4. **Caveats and guardrails** — unit normalization, base-year changes,
   national-vs-subnational traps, data gaps to disclose explicitly.

Ideas we'd love to see: labor-market health, inflation decomposition, energy
markets, housing, sovereign debt, sector earnings analysis, country
macro-risk snapshots.

### Other welcome contributions

- **Terminal renderers** — new chart types or better ASCII/ANSI output in
  `scripts/term_chart.py` (keep it stdlib-only).
- **Viz recipes** — reusable patterns for `build_viz.py` and
  `references/viz-guide.md`.
- **SQL idioms and pitfalls** — additions to `references/sql-guide.md` from
  real usage.
- **Docs and fixes** — anything that makes the agent's first attempt land.

Test a playbook by running the questions it targets end-to-end through the
skill and checking the published output; a PR description that shows a
before/after share link is the most convincing review material.

## Security

No secrets belong in this repo, and the plugin holds none — all access goes
through the MCP server's OAuth flow, so the coding agent holds the token and
nothing is written here. All SQL runs read-only against FactIQ's data warehouse.

## License

[MIT](LICENSE)
