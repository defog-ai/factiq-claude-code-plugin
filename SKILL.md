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
allowed-tools: Bash(python3:*), Bash(python:*), Read, Write
---

# FactIQ Data Tools

You are the analyst. FactIQ provides authenticated HTTP data tools (catalog
search, read-only SQL, series lookup, market data, earnings search) and two
publishing endpoints — a single shareable chart, or a fully formed
multi-section report. There is no server-side agent in this loop: you
decompose the question, find the data, do the math with your own tokens, and
author the output.

Three output modes:

- **Quick chart** (`share-chart`) — one focused chart published to FactIQ as a
  share link. Default for questions about a single metric or comparison.
- **Detailed report** (`share-report`) — summary + sections of narrative and
  charts + methodology, rendered on FactIQ's share-report page exactly like
  the in-house agent's reports. For broad or analytical questions. See
  **Detailed reports** below.
- **Bespoke local viz** (`build_viz.py`) — a self-contained HTML file you
  author freely and save locally, not published to FactIQ. Use when the answer
  needs something the ChartSpec can't express: a custom layout, a multi-panel
  dashboard, a force/flow/chord diagram, a novel encoding, or fine-grained
  visual control. See **Bespoke local visualizations** below.

All access goes through the bundled CLI — no codebase or database access is
needed:

```bash
python3 scripts/factiq.py <subcommand> ...   # path relative to this skill dir
```

Shell working directory resets between calls — resolve the script's absolute
path once (from this skill's directory) and use it in every invocation.

Every subcommand prints JSON to stdout. Errors go to stderr with a non-zero
exit code (2 = HTTP error, 3 = rate limit / quota, 4 = server-reported tool
error such as a SQL failure or statement timeout).

## Setup

Auth is API-key based (`fiq_...` keys). The CLI looks for `FACTIQ_API_KEY`
in the environment first, then `api_key` in `~/.factiq/config.json`.

1. Check whether auth works: `python3 scripts/factiq.py whoami`. If it fails,
   tell the user exactly how to get a key — sign in at https://factiq.com,
   open **Settings → Security** (https://factiq.com/settings/security), and
   click **Generate API key** (or **Regenerate**; keys are shown only once,
   so a key that was never copied can only be replaced). Then store it:

   ```bash
   # Prompts securely for the key, verifies it against the API, stores it:
   python3 scripts/factiq.py set-key
   # Non-interactive: --key fiq_... also works
   ```

   If this skill is installed as a plugin, `/factiq:set-key` walks the user
   through the same steps.

2. The API defaults to `https://api.worlddb.ai` and the web origin (for share
   links) to `https://www.factiq.com`. For local development override with
   `FACTIQ_API_URL=http://localhost:8000` and
   `FACTIQ_WEB_URL=http://localhost:3000` (or `--base-url` / `--web-url`,
   which work before or after the subcommand).

## Subcommands

| Command | Purpose |
|---|---|
| `context [--schemas bls,bea] [--full]` | Lean per-schema index + the shared table DDL. **Call once per session before anything else.** `--full` returns the heavy per-dataset description dump (rarely needed — use `describe` instead). |
| `search-datasets --query "rare earth imports" [--schemas mospi,rbi] [--limit N]` | Keyword (BM25, not semantic) ranking of datasets across all schemas. **The first discovery step** — find the right `schema`+`dataset_code`. |
| `describe SCHEMA DATASET_CODE` | Full metadata for one dataset: topic, methodology, release dates, base-change notice, available dimensions, example series. Call after `search-datasets`. |
| `search --schema bls --terms "unemployment rate"` | Series-level title-substring search within a schema (repeat `--schema`/`--terms` pairs). Includes `COMPOUND::` series. |
| `sql --schema bls --query "..." [--explore] [--full] [--max-rows N] [--out f.json]` | Read-only SELECT against one schema. Default output is a sampled preview. |
| `series SCHEMA SERIES_ID [--from-year Y] [--to-year Y] [--full] [--out f.json]` | Fetch one series — timeseries, tabular, or `COMPOUND::` ids all work. |
| `market FUNCTION [--symbol AAPL] [--interval] [--outputsize full]` | Quotes, daily/weekly/monthly series, fundamentals (OVERVIEW, INCOME_STATEMENT, EARNINGS), FX, commodities (WTI, BRENT, GOLD), SYMBOL_SEARCH. |
| `earnings "QUERY" [--target sections\|themes\|qa_exchanges] [--companies AAPL,MSFT] [--quarter 2025Q4]` | Full-text search over earnings-call intelligence. |
| `share-chart --spec chart.json [--question "..."]` | Publish a ChartSpec, returns `{shareUrl}`. |
| `share-report --report report.json [--question "..."] [--model "..."]` | Publish a multi-section report as a public shared run, returns `{shareUrl, ...}`. |

## Orchestration workflow

1. **Context first.** Run `context` once to get the compact per-schema index
   and the table DDL. This is lean by design — it tells you what each schema
   covers, not every dataset. Schemas listed under `schemas_without_data` have
   no rows loaded; skip them. (You rarely need `--full`; use `describe` for
   detail on a specific dataset.)
2. **Find datasets, then drill in.** Run `search-datasets --query "..."` to
   rank datasets across all schemas by keyword — this is the primary discovery
   step. Survey every schema that could be relevant before committing: for
   India check both `mospi` and `rbi` (pass `--schemas mospi,rbi`); for the US
   check `bls`, `bea`, `census`; energy means `eia`. Once a dataset looks
   right, `describe SCHEMA DATASET_CODE` for its dimensions and example
   series, then find the exact series with `search --schema ... --terms ...`
   (series-level, substring — prefer short stems like `rare`, not `rare
   earth`) or exploration SQL (`sql --explore`) on the `series` and
   `dimensions` tables. For multi-source stories, actually fetch data from 2+
   schemas, don't just survey them.
3. **Fetch in batches.** Once you know which series you need, issue all
   fetch calls together (multiple Bash calls in one turn). Use `series` for
   1–2 known ids; `sql` with a CASE-WHEN pivot for 3+ series or joins.
4. **Compute yourself.** YoY growth, rebasing to an index, per-capita,
   ratios — write your own Python locally on the `--out` file. Do not look
   for a server-side code interpreter; there is none in this loop.
5. **Recent market data.** The DB lags for very recent market/price data —
   use `market` for current quotes, commodities, and FX.
6. **Publish or build.** Quick-chart mode: write a ChartSpec JSON (see
   `references/chart-spec.md`) with wide-format data rows, then
   `share-chart --spec chart.json`; return the `shareUrl`. Report mode: write
   a report JSON (see `references/report-spec.md` and **Detailed reports**
   below), then `share-report --report report.json`; return the `shareUrl`.
   Bespoke-viz mode: author an HTML file, `build_viz.py assemble` the
   on-disk data into it, `build_viz.py render` to screenshot and iterate, then
   give the user the local file path (see **Bespoke local visualizations**).

## Detailed reports

A report is a public, fully rendered FactIQ research page: a bulleted
summary up top, then sections that pair narrative with charts, then
methodology notes. You author the whole thing — every chart's data rows,
every narrative claim — from data you actually fetched in this session.
The JSON format, per-chart fields, and a worked example live in
`references/report-spec.md`. Read that file before writing the report.

Ground rules:

- **2–5 sections, 1–2 charts each** is the sweet spot (server caps: 12
  sections, 16 charts). Each section should make one claim its charts prove.
- **Chart titles state the finding** ("Health care added 652k jobs in 2024 —
  triple tech's losses"), not the topic ("Jobs by sector").
- **Narratives are plain text** — markdown is not rendered on the report
  page, so `**bold**` shows up as literal asterisks.
- **Cite sources and lineage.** Every chart should carry `sources` (the
  datasets behind it) and `lineage` (the SQL/computation steps you actually
  ran). Charts without lineage get a generic "uploaded data" stub — fine,
  but real lineage makes the "How we built this" panel meaningful. Lineage
  `code` renders verbatim in a code block, so write it as formatted
  multi-line SQL/Python — never collapsed onto one line — and list **every**
  series the step touched in `series_refs`, not a single representative one.
- **Don't pad.** If the data only supports one chart, publish a quick chart
  instead of inflating a report.

`share-report` validates locally, POSTs to `/tools/report`, and prints the
server response plus a `shareUrl` composed from your configured web origin.
The report appears in your FactIQ history and can be forked by anyone who
opens the share link.

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

The loop that makes this work — **author → assemble → render → look → fix**:

1. Fetch full data to disk as usual (`sql … --full --out /tmp/x.json`). Never
   paste data rows into the HTML.
2. Copy `assets/viz-shell.html`, add any CDN library you need, and author the
   viz. Keep the `__FACTIQ_DATA__` marker inside its
   `<script id="factiq-data" type="application/json">` tag — that exact element
   is where the data lands and how the page reads it back. After assembly the
   page exposes a `DATA` global; rows are at `DATA.<key>.results`.
3. `assemble` the self-contained file, then `render` it and **actually read
   the screenshot**. `render` exits **5** when the page logged a JS error or a
   failed request — that usually means a blank page; fix it before judging the
   visual. One render pass is never enough; budget two or three.
4. Hand the user the local file path; offer `--open` to open it in a browser.

## Context budget — sampled previews and `--out`

Default output for `sql`, `series`, and `market` is the same down-sampled
preview the production agent sees: enough to verify shape and values, not the
full result. For chart building you need full rows — but never dump them into
your own context:

```bash
python3 scripts/factiq.py sql --schema bls --query "..." --full --out /tmp/unemp.json
```

`--out` writes the complete JSON to disk and prints only a stub
(`{out, columns, row_count, written_rows, ...}`). Then build the chart's
`data` array from the file with a local Python script. SQL `--full` returns up
to `--max-rows` rows (default **500**); raise it (e.g. `--max-rows 5000`) to
fetch more. When the result is cut, the response sets `truncated: true` plus a
`note`, both of which the stub now echoes — and `written_rows` (rows actually
on disk) will be below `row_count` (the server's pre-truncation total). If you
see truncation, narrow the query (date range, fewer series), aggregate
server-side, or raise `--max-rows`.

## Errors and limits

- **401** — the API key is missing or was regenerated elsewhere. Point the
  user at https://factiq.com/settings/security to regenerate, then re-run
  `set-key`.
- **429 (exit 3)** — either the 1 request/second rate limit or the monthly
  tool-call quota (50× the plan's question quota; the error says when it
  resets). The CLI absorbs transient rate-limit 429s itself (up to two
  retries with backoff), so multiple calls in one turn are safe; an exit-3
  failure that survives the retries means quota exhaustion or sustained
  limiting. Don't burn calls re-fetching data you have.
- **403** — schema is admin-restricted for this account; drop it.
- **SQL errors come back as HTTP 200** with an `{"error": "..."}` body
  (syntax errors, timeouts, bad column names). The CLI surfaces these on
  stderr with exit code 4 and never writes an `--out` file for them.
  Revise the query and rerun.
- **Zero rows** — your filter was too narrow. Broaden it yourself (see
  `references/sql-guide.md`). `--auto-retry` opts into a server-side LLM
  reviser, but you can usually revise better and cheaper yourself.
- **SQL timeout** — statements are capped at 30s. Filter on indexed columns
  (`series_id`, `dataset_code`) instead of scanning titles across the table,
  and never pattern-match `series_id` on `data_points` — resolve ids from
  `series` first (see the pitfall in `references/sql-guide.md`).
- **share-report 422** — the server re-validates the report against its real
  chart schemas and names the failing field paths (e.g.
  `sections[1].charts[0].x_column`). Fix the named fields in the JSON and
  re-run; nothing was published.

## References

- `references/sql-guide.md` — table structure, query idioms, pitfalls
  (frequency literals, national vs sub-national, pivots, tabular data).
- `references/chart-spec.md` — ChartSpec format, chart-type selection, a
  worked share-chart example.
- `references/report-spec.md` — report JSON format for `share-report`:
  sections, per-chart fields, sources/lineage authoring, limits, a worked
  example.
- `references/viz-guide.md` — bespoke local HTML visualizations with
  `build_viz.py`: the assemble/render loop, the `DATA` contract, technique
  selection (ECharts/D3/Canvas/WebGL), a legibility checklist, starter recipes.
- `references/schemas.md` — what lives in each schema. The `context`
  subcommand is the live, authoritative version; `search-datasets` /
  `describe` drill into individual datasets on demand.
