---
name: factiq
description: >
  Answer economic and financial data questions with real data from FactIQ
  (worlddb): US indicators (BLS employment/CPI, BEA GDP, Census trade, EIA
  energy, USDA ERS, BTS transport), international data (China NBS, China
  customs, India MOSPI/RBI/trade, Singapore, IMF, World Bank), stock quotes
  and fundamentals, commodities/forex, and earnings-call intelligence. Use
  when the user asks about unemployment, inflation, GDP, trade flows, energy,
  wages, markets, or wants a shareable economic chart, a full multi-section
  research report, or a bespoke custom visualization or dashboard saved as a
  local HTML file. You orchestrate the whole analysis yourself — discover
  series, query SQL, compute, then publish a single chart or a fully formed
  report as a share link, or build a custom local HTML visualization.
allowed-tools: >
  mcp__plugin_factiq_factiq__get_data_catalog,
  mcp__plugin_factiq_factiq__search_datasets,
  mcp__plugin_factiq_factiq__describe_dataset,
  mcp__plugin_factiq_factiq__search_series,
  mcp__plugin_factiq_factiq__get_series,
  mcp__plugin_factiq_factiq__run_sql,
  mcp__plugin_factiq_factiq__get_market_data,
  mcp__plugin_factiq_factiq__search_earnings,
  mcp__plugin_factiq_factiq__get_style_guides,
  mcp__plugin_factiq_factiq__share_chart,
  mcp__plugin_factiq_factiq__share_report,
  mcp__factiq__get_data_catalog,
  mcp__factiq__search_datasets,
  mcp__factiq__describe_dataset,
  mcp__factiq__search_series,
  mcp__factiq__get_series,
  mcp__factiq__run_sql,
  mcp__factiq__get_market_data,
  mcp__factiq__search_earnings,
  mcp__factiq__get_style_guides,
  mcp__factiq__share_chart,
  mcp__factiq__share_report,
  Bash(python3:*), Bash(python:*), Read, Write, Agent
---

# FactIQ Data Tools

You are the analyst. FactIQ provides authenticated **MCP tools** for the whole
loop — discover the data (catalog, dataset/series search, read-only SQL, series
lookup, market data, earnings search), then publish the result (`share_chart`,
`share_report`). There is no server-side agent: you decompose the question, find
the data with the MCP tools, do the math with your own tokens, author the
output, and publish it with a tool call.

Three output modes:

- **Quick chart** (`share_chart` tool) — one focused chart published to FactIQ
  as a share link. Default for questions about a single metric or comparison.
- **Detailed report** (`share_report` tool) — summary + sections of narrative
  and charts + methodology, rendered on FactIQ's share-report page exactly like
  the in-house agent's reports. For broad or analytical questions. See
  **Detailed reports** below.
- **Bespoke local viz** (`build_viz.py`) — a self-contained HTML file you
  author freely and save locally, not published to FactIQ. Use when the answer
  needs something the ChartSpec can't express: a custom layout, a multi-panel
  dashboard, a force/flow/chord diagram, a novel encoding, or fine-grained
  visual control. See **Bespoke local visualizations** below.

**Data in, output out:**

- All discovery, fetching, **and publishing** go through the FactIQ **MCP
  tools** (`factiq MCP`). No codebase, database, or API key is
  needed — the coding agent calls them directly over one authenticated connection.
- The only local script is the bespoke-viz builder (it never touches the API):

  ```bash
  python3 scripts/build_viz.py  ...   # path relative to this skill dir
  ```

  Shell working directory resets between calls — resolve the script's absolute
  path once (from this skill's directory) and reuse it.

## Setup

One connection covers everything: the FactIQ **MCP server** bundled with this
plugin (`.mcp.json`), authorized over OAuth. On first use the coding agent runs
FactIQ's browser-based **Connect** flow. If the FactIQ tools are missing or
return an auth error, the connection isn't set up yet — tell the user to
authorize the MCP server:

- **Claude Code**: run **`/mcp`**, pick **factiq**, and complete the sign-in.
- **Codex**: run **`codex mcp login factiq`** and complete the sign-in.

The same FactIQ login works everywhere (email, Google, or passkey). Nothing to
copy or paste, and no separate key for publishing — the same connection
authorizes `share_chart` / `share_report`.

**Local development.** The MCP URL defaults to `https://api.factiq.com/mcp`;
override it for a local backend by setting
`FACTIQ_MCP_URL=http://localhost:8000/mcp` before the coding agent starts (it
expands in `.mcp.json`).

## Tools

All FactIQ tools are MCP tools provided by the `factiq` MCP server.

### Data

| Tool | Purpose |
|---|---|
| `get_data_catalog` (`schemas?`, `full?`) | Per-schema index + the shared table DDL. **Call once per session before anything else.** `full=true` returns the heavy per-dataset dump (rarely needed — use `describe_dataset`). Schemas listed under `schemas_without_data` have no rows — skip them. |
| `search_datasets` (`query`, `schemas?`, `limit?`) | Keyword (not semantic) ranking of datasets across all schemas. **The first discovery step** — find the right `schema` + `dataset_code`. |
| `describe_dataset` (`schema`, `dataset_code`) | Full metadata for one dataset: topic, methodology, release dates, base-change notice, dimensions, example series. Call after `search_datasets`. |
| `search_series` (`schema`, `terms`, `limit?`, `include_compound?`) | Series-level title-substring search within one schema (`terms` is a list — prefer short stems). Includes `COMPOUND::` series. |
| `run_sql` (`schema`, `sql`, `question?`, `explore?`, `auto_retry?`) | Read-only SELECT against one schema. The power tool for joins, pivots, aggregation. |
| `get_series` (`schema`, `series_id`, `from_year?`, `to_year?`) | Fetch one series — timeseries, tabular, or `COMPOUND::` ids all work. |
| `get_market_data` (`function`, `symbol?`, `interval?`, `outputsize?`) | Quotes, daily/weekly/monthly series, fundamentals (OVERVIEW, INCOME_STATEMENT, EARNINGS), FX, commodities (WTI, BRENT, GOLD), SYMBOL_SEARCH. |
| `search_earnings` (`query`, `search_target?`, `company_filter?`, `quarter_filter?`, `limit?`) | Full-text search over earnings-call intelligence. |
| `get_style_guides` (`guides`) | FactIQ's house-style chart/report/SQL guides (`"chart"`, `"report"`, `"sql"`, or `"all"`). Optional; this skill's `references/` already cover the **publishing** JSON formats — use these guides for extra house-style detail. |

Every row-returning tool (`run_sql`, `get_series`) returns **at most 50 rows**.
When a result comes back `"truncated": true` there is more data — your move is
to **aggregate or compute in SQL** (a `GROUP BY date_trunc(...)`, a
SUM/AVG/rank/ratio) and fetch that, or window a single series with
`from_year` / `to_year`. There is no "give me everything" option, by design —
see **Context budget** below.

### Publishing

| Tool | Purpose |
|---|---|
| `share_chart` (`chart`, `question?`) | Publish a ChartSpec object (owned by your account, editable from the UI). Returns `{share_id, share_url}`. |
| `share_report` (`question`, `report`, `model?`) | Publish a multi-section report (`{summary, sections, …}`) as a public shared run. Returns the publish result incl. `share_url`. |

Pass the spec/report as the tool argument directly — build the object in your
context (or with the Write tool / local Python for large data arrays) and hand
it to the tool. A validation failure comes back as a tool error naming the bad
field; nothing is published until it validates.

### Local viz — `build_viz.py`

`build_viz.py assemble … / render …` builds + screenshots a bespoke local HTML
viz (see **Bespoke local visualizations**). Local-only; never calls the API.

## Orchestration workflow

1. **Catalog first.** Call `get_data_catalog` once to get the compact
   per-schema index and the table DDL. It tells you what each schema covers,
   not every dataset. Skip schemas under `schemas_without_data`. (You rarely
   need `full=true`; use `describe_dataset` for detail on one dataset.)
2. **Find datasets, then drill in.** Call `search_datasets` to rank datasets
   across all schemas by keyword — the primary discovery step. Survey every
   schema that could be relevant before committing: for India check both
   `mospi` and `rbi`; for the US check `bls`, `bea`, `census`; energy means
   `eia`. Once a dataset looks right, `describe_dataset` for its dimensions and
   example series, then find the exact series with `search_series` (substring —
   prefer short stems like `rare`, not `rare earth`) or exploration SQL
   (`run_sql` with `explore=true`) on the `series` and `dimensions` tables.
   For multi-source stories, actually fetch data from 2+ schemas.

   For report-mode questions covering multiple topics, companies, or data
   sources, consider decomposing the research into parallel subagents — see
   **Subagent orchestration** below.

3. **Fetch in batches.** Once you know which series you need, issue the fetch
   calls together (multiple tool calls in one turn). Use `get_series` for 1–2
   known ids; `run_sql` with a CASE-WHEN pivot for 3+ series or joins. Keep
   results inside the 50-row cap — aggregate in SQL to the granularity a chart
   actually needs.
4. **Compute yourself.** YoY growth, rebasing to an index, per-capita, ratios —
   write your own Python locally on the fetched values. There is no server-side
   code interpreter in this loop.
5. **Recent market data.** The DB lags for very recent market/price data — use
   `get_market_data` for current quotes, commodities, and FX.
6. **Publish or build.** Quick-chart mode: build a ChartSpec object (see
   `references/chart-spec.md`) with wide-format data rows and call
   `share_chart`; return the `share_url`. Report mode: build a report object
   (see `references/report-spec.md` and **Detailed reports** below) and call
   `share_report`; return the `share_url`. Bespoke-viz mode: write the fetched
   data to JSON files, author an HTML file, `build_viz.py assemble`,
   `build_viz.py render` to screenshot and iterate, then give the user the local
   file path (see **Bespoke local visualizations**).

## Subagent orchestration

For report-mode questions that span multiple distinct topics, companies, or data
sources, decompose the work into parallel subagents. This does two things:
each research thread gets a full, focused context instead of competing for
attention in one serial pass, and the report-assembly step gets the spec
loaded directly in its prompt so it never guesses at field names.

**Do NOT use subagents** for quick-chart mode or single-topic questions — the
overhead is not worth it. The decision point is right after step 2 of the
orchestration workflow: once you have done the catalog lookup and initial
dataset discovery, you know whether the question decomposes into 2+ independent
research threads. If it does, fan out.

### Research subagents

Spawn one Agent call per research thread. Each agent inherits the skill's
FactIQ MCP tools, so it can discover, fetch, and compute on its own. Give each
agent a tightly scoped prompt and tell it to return structured findings — not
prose, not a published artifact.

Agent prompt template (adapt the specifics per thread):

```
You are a FactIQ research agent. Your job is to answer ONE sub-question and
return structured findings. Do NOT call share_chart or share_report — just
research and return data.

Sub-question: {sub_question}

Relevant schemas/datasets (from the parent's catalog step): {hints}

Steps:
1. search_datasets / describe_dataset / search_series to find the right series.
2. Fetch data with get_series or run_sql. Aggregate in SQL to stay under the
   50-row cap.
3. Compute derived metrics (YoY, ratios, indices) yourself.
4. Return your findings as a structured block:

FINDINGS:
- sub_question: (echo it back)
- series_used: [{schema, series_id, title}, ...]
- sql_queries: [the exact SQL you ran, formatted multi-line]
- data: [{columns: [...], rows: [...]}, ...] — the actual fetched/computed values
- key_insights: [1-3 sentences stating what the data shows, with numbers]
- chart_suggestion: {chart_type, title, x_column, y_columns, units}
```

Launch the agents in parallel — multiple Agent tool calls in one turn:

```
Agent(prompt="<research prompt for thread 1>", label="research-supply-chain")
Agent(prompt="<research prompt for thread 2>", label="research-pricing")
Agent(prompt="<research prompt for thread 3>", label="research-demand")
```

Each agent runs independently and returns its findings block. Wait for all of
them before proceeding to assembly.

### Report assembler subagent

After all research is complete, spawn a single report-assembler agent. Its
prompt must contain two things: (1) the full content of `references/report-spec.md`
so the spec is in context, not behind a file read that might be skipped, and
(2) all the research findings from the previous step.

Before spawning the assembler, read `references/report-spec.md` yourself with
the Read tool. Then embed its entire content in the assembler's prompt.

Agent prompt template:

```
You are a FactIQ report assembler. Build a complete report object and publish
it with share_report. Do NOT do any data discovery or fetching — all data is
provided below.

USER QUESTION: {original_question}

=== REPORT SPEC (from references/report-spec.md) ===
{paste the full content of references/report-spec.md here}
=== END REPORT SPEC ===

=== RESEARCH FINDINGS ===
{paste all findings blocks from the research agents, labeled by thread}
=== END RESEARCH FINDINGS ===

Instructions:
1. Design 2-5 sections. Each section makes one claim its chart(s) prove.
2. Chart titles state the finding with numbers, not the topic.
3. Narratives are plain text — no markdown formatting.
4. Every chart must have columns, data (from the findings above), x_column,
   y_columns (for line/bar), sources, and lineage.
5. Lineage code must be formatted multi-line SQL/Python with real newlines.
   series_refs must list every series the step used.
6. Call share_report with question, report, and model. Return the share_url.
```

Launch the assembler:

```
Agent(prompt="<assembler prompt with spec + findings>", label="report-assembler")
```

The assembler has the full spec in context, so it builds the report object
correctly on the first attempt. It calls `share_report` itself and returns
the `share_url`, which you relay to the user.

### Example decomposition

Question: "How is the US EV market evolving — supply chain, pricing, and demand?"

After step 2 (catalog + discovery), you identify three independent threads:

| Thread | Sub-question | Schemas |
|---|---|---|
| Supply chain | What does US EV battery/component production look like? | `census`, `bea` |
| Pricing | How have EV prices and average selling prices changed? | `bls` (CPI), market data |
| Consumer demand | What are EV sales and registration trends? | `bts`, `bea`, market data |

Spawn three research agents in parallel. When all return, spawn one assembler
agent with the spec and all three findings blocks. The assembler builds a
3-section report (one per thread), calls `share_report`, and returns the URL.

### When NOT to use subagents

- Quick-chart mode (single metric, single chart).
- Single-topic questions even in report mode ("How has US unemployment evolved
  since 2020?" — one thread, no decomposition needed).
- Bespoke local visualizations — the build_viz loop is inherently iterative and
  does not benefit from fan-out.

For these cases, do the research and publishing in the main context as usual.

## Detailed reports

A report is a public, fully rendered FactIQ research page: a bulleted summary
up top, then sections that pair narrative with charts, then methodology notes.
You author the whole thing — every chart's data rows, every narrative claim —
from data you actually fetched in this session. The JSON format, per-chart
fields, and a worked example live in `references/report-spec.md`. For reliable publishing, use a dedicated report-assembler subagent with the spec loaded in its prompt — see **Subagent orchestration**.

Ground rules:

- **2–5 sections, 1–2 charts each** is the sweet spot (server caps: 12
  sections, 16 charts). Each section should make one claim its charts prove.
- **Chart titles state the finding** ("Health care added 652k jobs in 2024 —
  triple tech's losses"), not the topic ("Jobs by sector").
- **Narratives are plain text** — markdown is not rendered on the report page,
  so `**bold**` shows up as literal asterisks.
- **Cite sources and lineage.** Every chart should carry `sources` (the
  datasets behind it) and `lineage` (the SQL/computation steps you actually
  ran). Charts without lineage get a generic "uploaded data" stub — fine, but
  real lineage makes the "How we built this" panel meaningful. Lineage `code`
  renders verbatim in a code block, so write it as formatted multi-line
  SQL/Python — never collapsed onto one line — and list **every** series the
  step touched in `series_refs`, not a single representative one.
- **Don't pad.** If the data only supports one chart, publish a quick chart
  instead of inflating a report.

The `share_report` tool validates the report against FactIQ's real chart
schemas server-side, stores it as a completed public run, and returns the
`share_url`. The report appears in your FactIQ history and can be forked by
anyone who opens the share link.

## Bespoke local visualizations

When the answer wants something the published ChartSpec can't express — a
custom layout, a dashboard of several panels, a force/flow/chord diagram, an
annotated narrative, a novel encoding, or just fine visual control — build it
yourself as a self-contained local HTML file. There is no spec and no fixed
chart-type list: you author the HTML/JS (ECharts, D3, Canvas, SVG, WebGL),
inject the data you already fetched, then render and iterate. Read
`references/viz-guide.md` before starting — it covers technique selection, the
data contract, and the legibility checklist.

The tool is `scripts/build_viz.py` (local-only — it never calls the API):

| Command | Purpose |
|---|---|
| `assemble --template T.html --data k1=f1.json k2=f2.json … --out O.html [--open]` | Inject on-disk JSON into your HTML at the `__FACTIQ_DATA__` marker; write one portable, self-contained file. Stdlib only. List **all** key=path pairs after the one `--data` flag. |
| `render O.html [--out P.png] [--width N] [--height N] [--full-page] [--selector CSS] [--wait MS]` | Screenshot the file in headless Chromium and report JS/console errors + failed asset loads. Installs Playwright + Chromium into `~/.factiq/viz-venv` on first run (uses `uv` if available, else a stdlib venv). |

The loop that makes this work — **fetch → save → author → assemble → render →
look → fix**:

1. Fetch the data with the MCP tools, then **write each result to a JSON file**
   with the Write tool (the file holds the tool's own `{columns, results, …}`
   payload — see `references/viz-guide.md` for the exact shape build_viz reads
   back). Because the MCP caps results at 50 rows, this is context-cheap;
   aggregate or window in SQL to get exactly the rows the viz needs.
2. Copy `assets/viz-shell.html`, add any CDN library you need, and author the
   viz. Keep the `__FACTIQ_DATA__` marker inside its
   `<script id="factiq-data" type="application/json">` tag — that exact element
   is where the data lands and how the page reads it back. After assembly the
   page exposes a `DATA` global; rows are at `DATA.<key>.results`.
3. `assemble` the self-contained file, then `render` it and **actually read the
   screenshot**. `render` exits **5** when the page logged a JS error or a
   failed request — that usually means a blank page; fix it before judging the
   visual. One render pass is never enough; budget two or three.
4. Hand the user the local file path; offer `--open` to open it in a browser.

## Context budget — the 50-row cap

Every row-returning MCP tool (`run_sql`, `get_series`) returns **at most 50
rows**, and there is no "give me everything" option — by design. The cap keeps
results context-sized, so you do **not** stage data to disk to protect your
context; you take the tool result directly.

When a result comes back `"truncated": true`, there is more data and your move
is to **aggregate or compute it in SQL**, not to try to fetch the raw rows:

- Roll a long daily/monthly series up with `GROUP BY date_trunc('month', time)`
  (or quarter/year) — a chart wants a few hundred points at most, and 50
  aggregated points usually says everything.
- Return a SUM / AVG / rank / ratio instead of the underlying rows.
- For one series, window it with `get_series(..., from_year=, to_year=)`, or
  make a few windowed calls and stitch them.

Whatever you chart or report has to be the aggregated result you bring back —
which is also all it needs. For `build_viz`, write that (already small) result
to a JSON file before assembling.

## Errors and limits

- **MCP tool unavailable / auth error** — the FactIQ MCP isn't connected. Tell
  the user to authorize it (Claude Code: `/mcp` → factiq; Codex:
  `codex mcp login factiq`). The same connection authorizes both the data tools
  and `share_chart` / `share_report`, so this fixes publishing failures too.
- **429** — either the 1 request/second rate limit or the monthly tool-call
  quota (the error says when it resets). Note that publishing counts against the
  same monthly tool quota as the data tools. Don't burn calls re-fetching data
  you already have.
- **403** — that schema is admin-restricted for this account; drop it.
- **SQL errors** come back in the tool result as an `error` (syntax errors,
  timeouts, bad column names). Revise the query and rerun.
- **Zero rows** — your filter was too narrow. Broaden it yourself (see
  `references/sql-guide.md`). `auto_retry=true` opts into a server-side LLM
  reviser, but you can usually revise better and cheaper yourself.
- **SQL timeout** — statements are capped at 30s. Filter on indexed columns
  (`series_id`, `dataset_code`) instead of scanning titles, and never
  pattern-match `series_id` on `data_points` — resolve ids from `series` first
  (see the pitfall in `references/sql-guide.md`).
- **Publishing validation error** — `share_chart` / `share_report` validate the
  payload against FactIQ's real chart schemas and return a tool error naming the
  failing field paths (e.g. `sections[1].charts[0].x_column`). Fix the named
  fields and call the tool again; nothing is published until it validates.

## References

- `references/sql-guide.md` — table structure, query idioms, pitfalls
  (frequency literals, national vs sub-national, pivots, tabular data).
- `references/chart-spec.md` — ChartSpec format, chart-type selection, a
  worked `share_chart` example.
- `references/report-spec.md` — report JSON format for `share_report`:
  sections, per-chart fields, sources/lineage authoring, limits, a worked
  example.
- `references/viz-guide.md` — bespoke local HTML visualizations with
  `build_viz.py`: the assemble/render loop, the `DATA` contract, technique
  selection (ECharts/D3/Canvas/WebGL), a legibility checklist, starter recipes.
- `references/schemas.md` — what lives in each schema. The `get_data_catalog`
  tool is the live, authoritative version; `search_datasets` / `describe_dataset`
  drill into individual datasets on demand.
