---
name: factiq
description: >
  Answer economic and financial data questions with real data from FactIQ
  (worlddb): US indicators (BLS employment/CPI, BEA GDP, Census trade, EIA
  energy, USDA ERS, BTS transport), international data (China NBS, China
  customs, India MOSPI/RBI/trade, Singapore, IMF, World Bank), stock quotes
  and fundamentals, commodities/forex, and earnings-call intelligence. Use
  when the user asks about unemployment, inflation, GDP, trade flows, energy,
  wages, markets, or wants a shareable economic chart. You orchestrate the
  whole analysis yourself — discover series, query SQL, compute, build the
  chart spec, publish a share link.
allowed-tools: Bash(python3:*), Bash(python:*), Read, Write
---

# FactIQ Data Tools

You are the analyst. FactIQ provides authenticated HTTP data tools (catalog
search, read-only SQL, series lookup, market data, earnings search) and a
chart-publishing endpoint. There is no server-side agent in this loop: you
decompose the question, find the data, do the math with your own tokens, and
build the chart.

All access goes through the bundled CLI — no codebase or database access is
needed:

```bash
python3 scripts/factiq.py <subcommand> ...   # path relative to this skill dir
```

Shell working directory resets between calls — resolve the script's absolute
path once (from this skill's directory) and use it in every invocation.

Every subcommand prints JSON to stdout. Errors go to stderr with a non-zero
exit code (2 = HTTP error, 3 = rate limit / quota).

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
   else. `search` is substring matching, not semantic — exploration SQL on
   the `series` and `dimensions` tables is the primary discovery tool. For
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
6. **Build the chart.** Write a ChartSpec JSON (see
   `references/chart-spec.md`) with wide-format data rows, then
   `share-chart --spec chart.json`. Return the `shareUrl` to the user.

## Context budget — sampled previews and `--out`

Default output for `sql`, `series`, and `market` is the same down-sampled
preview the production agent sees: enough to verify shape and values, not the
full result. For chart building you need full rows — but never dump them into
your own context:

```bash
python3 scripts/factiq.py sql --schema bls --query "..." --full --out /tmp/unemp.json
```

`--out` writes the complete JSON to disk and prints only a stub
(`{out, columns, row_count, ...}`). Then build the chart's `data` array from
the file with a local Python script. SQL `--full` is capped at 5,000 rows
server-side (`truncated: true` flags the cut) — narrow the date range or
series list to fetch the rest.

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
  (syntax errors, timeouts, bad column names) — the CLI exits 0, so check
  for an `error` key before trusting a result. Revise the query and rerun.
- **Zero rows** — your filter was too narrow. Broaden it yourself (see
  `references/sql-guide.md`). `--auto-retry` opts into a server-side LLM
  reviser, but you can usually revise better and cheaper yourself.
- **SQL timeout** — statements are capped at 30s. Filter on indexed columns
  (`series_id`, `dataset_code`) instead of scanning titles across the table.

## References

- `references/sql-guide.md` — table structure, query idioms, pitfalls
  (frequency literals, national vs sub-national, pivots, tabular data).
- `references/chart-spec.md` — ChartSpec format, chart-type selection, a
  worked share-chart example.
- `references/schemas.md` — what lives in each schema. The `context`
  subcommand is the live, authoritative version.
