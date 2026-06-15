---
name: factiq
description: >
  Answer economic and financial data questions with real data from FactIQ
  (worlddb): US indicators (BLS employment/CPI, BEA GDP, Census trade, EIA
  energy, USDA ERS, BTS transport), international data (China NBS, China
  customs, India MOSPI/RBI/trade, Singapore, IMF, World Bank), stock quotes
  and fundamentals, commodities/forex, and earnings-call intelligence. Use
  when the user asks about unemployment, inflation, GDP, trade flows, energy,
  wages, markets, or wants a shareable economic chart or a full multi-section
  research report. You orchestrate the whole analysis yourself — discover
  series, query SQL, compute, then publish either a single chart or a
  fully formed report as a share link.
allowed-tools: Bash(python3:*), Bash(python:*), Read, Write
---

# FactIQ Data Tools

You are the analyst. FactIQ provides authenticated HTTP data tools (catalog
search, read-only SQL, series lookup, market data, earnings search) and two
publishing endpoints — a single shareable chart, or a fully formed
multi-section report. There is no server-side agent in this loop: you
decompose the question, find the data, do the math with your own tokens, and
author the output.

Two output modes:

- **Quick chart** (`share-chart`) — one focused chart. Default for questions
  about a single metric or comparison.
- **Detailed report** (`share-report`) — summary + sections of narrative and
  charts + methodology, rendered on FactIQ's share-report page exactly like
  the in-house agent's reports. For broad or analytical questions. See
  **Detailed reports** below.

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
| `context [--schemas bls,bea]` | Dataset catalog, per-dataset descriptions, and the shared table DDL. **Call once per session before anything else.** |
| `search --schema bls --terms "unemployment rate"` | Title-substring catalog search (repeat `--schema`/`--terms` pairs for several schemas in one call). Includes `COMPOUND::` series. |
| `sql --schema bls --query "..." [--explore] [--full] [--max-rows N] [--out f.json]` | Read-only SELECT against one schema. Default output is a sampled preview. |
| `series SCHEMA SERIES_ID [--from-year Y] [--to-year Y] [--full] [--out f.json]` | Fetch one series — timeseries, tabular, or `COMPOUND::` ids all work. |
| `market FUNCTION [--symbol AAPL] [--interval] [--outputsize full]` | Quotes, daily/weekly/monthly series, fundamentals (OVERVIEW, INCOME_STATEMENT, EARNINGS), FX, commodities (WTI, BRENT, GOLD), SYMBOL_SEARCH. |
| `earnings "QUERY" [--target sections\|themes\|qa_exchanges] [--companies AAPL,MSFT] [--quarter 2025Q4]` | Full-text search over earnings-call intelligence. |
| `share-chart --spec chart.json [--question "..."]` | Publish a ChartSpec, returns `{shareUrl}`. |
| `share-report --report report.json [--question "..."] [--model "..."]` | Publish a multi-section report as a public shared run, returns `{shareUrl, ...}`. |

## Orchestration workflow

1. **Context first.** Run `context` (optionally `--schemas` once you know
   which are relevant) to get dataset descriptions and the table DDL. If the
   unfiltered call times out, retry with `--schemas` — the full schema list
   is included either way. Schemas listed under `schemas_without_data` have
   no rows loaded; skip them.
2. **Discover broadly.** Survey every schema that could be relevant before
   deep-diving into one — for India check both `mospi` and `rbi`; for the US
   check `bls`, `bea`, `census`; energy means `eia`. Use `search` for
   obvious title matches and exploration SQL (`sql --explore`) for everything
   else. `search` is substring matching, not semantic — prefer short stems
   (`rare`, not `rare earth`: BLS titles its rare-earth import price index
   "precious, rare-earth, or radioactive"), and use exploration SQL on
   the `series` and `dimensions` tables as the primary discovery tool. For
   multi-source stories, actually fetch data from 2+ schemas, don't just
   survey them.
3. **Fetch in batches.** Once you know which series you need, issue all
   fetch calls together (multiple Bash calls in one turn). Use `series` for
   1–2 known ids; `sql` with a CASE-WHEN pivot for 3+ series or joins.
4. **Compute yourself.** YoY growth, rebasing to an index, per-capita,
   ratios — write your own Python locally on the `--out` file. Do not look
   for a server-side code interpreter; there is none in this loop.
5. **Recent market data.** The DB lags for very recent market/price data —
   use `market` for current quotes, commodities, and FX.
6. **Publish.** Quick-chart mode: write a ChartSpec JSON (see
   `references/chart-spec.md`) with wide-format data rows, then
   `share-chart --spec chart.json`. Report mode: write a report JSON (see
   `references/report-spec.md` and **Detailed reports** below), then
   `share-report --report report.json`. Either way, return the `shareUrl`
   to the user.

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
- `references/schemas.md` — what lives in each schema. The `context`
  subcommand is the live, authoritative version.
