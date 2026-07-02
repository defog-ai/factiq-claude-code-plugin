---
name: factiq
description: >
  Answer economic and financial data questions with real data from FactIQ
  (worlddb): US indicators (BLS employment/CPI, BEA GDP, Census trade, EIA
  energy, USDA ERS, BTS transport), international data (China NBS, China
  customs, India MOSPI/RBI/trade, Singapore, IMF, World Bank), stock quotes
  and fundamentals, commodities/forex, and earnings-call intelligence. Use
  when the user asks about unemployment, inflation, GDP, trade flows, energy,
  wages, markets,
  or wants a shareable economic chart or map (country choropleths,
  state/province choropleths, coordinate bubble maps), a terminal chart preview,
  a full multi-section research report, or a bespoke custom visualization or
  dashboard saved as a local HTML file. You orchestrate the whole analysis
  yourself — discover series, query SQL, compute, then publish a single chart or
  a fully formed report as a share link, render a terminal chart, or build a
  custom local HTML visualization.
allowed-tools: >
  mcp__plugin_factiq_factiq__*,
  mcp__factiq__*,
  mcp__claude_ai_FactIQ__*,
  Bash(python3:*), Bash(python:*), Read, Write, Agent
---

# FactIQ Data Tools

You are the analyst. FactIQ provides authenticated **MCP tools** for the whole
loop — discover the data (catalog, dataset/series search, read-only SQL, series
lookup, market data, earnings search), then publish the result (`share_chart`,
`share_report`). There is no server-side agent: you decompose the question, find
the data with the MCP tools, do the math with your own tokens, author the
output, and publish it with a tool call.

Four output modes:

- **Quick chart** (`share_chart` tool + `term_chart.py`) — one focused chart
  published to FactIQ as a share link, plus an inline terminal preview rendered
  from the same ChartSpec. Default for questions about a single metric or
  comparison. When geography is the finding this includes **maps**:
  choropleths by country or state/province and coordinate bubbles — see
  `references/chart-spec.md` (**Maps**) for the format and region-name rules
  (the terminal preview degrades to a ranked table).
- **Terminal chart** (`term_chart.py`) — an ANSI/ASCII preview without a share
  link. Use only when the user explicitly asks for terminal-only, ASCII-only, or
  local text output. See **Terminal charts** below.
- **Detailed report** (`share_report` tool) — summary + sections of narrative
  and charts + methodology, rendered on FactIQ's share-report page exactly like
  the in-house agent's reports, plus inline terminal previews of its charts. For
  broad or analytical questions. See **Detailed reports** below. Broad
  bilateral trade questions such as "latest trend in trade between A and B",
  broad bilateral economic-policy comparisons such as "compare A and B trade
  policy", broad monetary-policy questions such as "explain the Fed's current
  monetary policy stance", and broad fiscal-policy revenue questions default
  here unless the user explicitly asks for only a quick chart.
- **Bespoke local viz** (`build_viz.py`) — a self-contained HTML file you
  author freely and save locally, not published to FactIQ. Use when the answer
  needs something the ChartSpec can't express: a custom layout, a multi-panel
  dashboard, a force/flow/chord diagram, a novel encoding, or fine-grained
  visual control. See **Bespoke local visualizations** below.

**Data in, output out:**

- All discovery, fetching, **and publishing** go through the FactIQ **MCP
  tools** (`factiq MCP`). No codebase, database, or API key is
  needed — the coding agent calls them directly over one authenticated connection.
- The local scripts never touch the API:

  ```bash
  python3 scripts/term_chart.py render ... # terminal ChartSpec preview
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

**Local development.** The bundled MCP URL is
`https://api.factiq.com/mcp`. For a local backend, edit `.mcp.json` in your
development checkout or configure a standalone `factiq` MCP server in Codex or
Claude Code that points at the local URL.

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

### Terminal charts — `term_chart.py`

`term_chart.py` prints local ANSI/ASCII previews from normal FactIQ chart
objects. It never calls FactIQ. For `share_chart`, build the ChartSpec from data
you already fetched, save it to JSON, publish it, then render it:

```bash
python3 scripts/term_chart.py render --spec /tmp/factiq-chart.json --width 80 --charset ascii --color auto
```

For `share_report`, save the report object or the full `share_report` argument
object (`{"question": "...", "report": {...}}`) to JSON, publish it, then
render the report's charts:

```bash
python3 scripts/term_chart.py report --report /tmp/factiq-report.json --width 80 --charset ascii --color auto
```

Any time you create a shared chart or shared report, return both the share link
and the terminal preview. After `term_chart.py` renders, paste the preview
verbatim into your reply inside a triple-backtick code block; leaving it only in
the tool result hides it behind a collapsed block in Claude Code. Use
terminal-only output only when the user explicitly asks for no share link.

Supported terminal renderers:

| Renderer | Use when |
|---|---|
| `bar` | Categorical comparisons and short ranked lists |
| `line` | Time-series trends (one or more series) |
| `table` | Fallback for unsupported chart types or dense data |

Useful options:

| Option | Purpose |
|---|---|
| `--type auto\|bar\|line\|table` | Pick the terminal renderer; `auto` maps from `ChartSpec.type` |
| `--width 80` / `--width auto` | Fixed width by default; `auto` reads the terminal size |
| `--height N` | Line-chart plot height |
| `--charset ascii\|unicode-block` | Strict ASCII or denser Unicode block glyphs |
| `--color auto\|always\|never` | ANSI color control; `auto` respects TTY, `NO_COLOR`, and `TERM=dumb` |
| `--max-charts N` | Report previews only: cap the number of rendered charts; `0` means all |
| `--out FILE` | Also save the rendered text |

Because agents often capture command output instead of streaming it directly to
the user's terminal, use `--charset ascii --color never` for previews you paste
into the final answer. Use ANSI color for real terminal stdout or saved `.ansi`
previews.

### Local viz — `build_viz.py`

`build_viz.py save … / assemble … / render …` saves raw tool results to disk
(no retyping), builds, and screenshots a bespoke local HTML viz (see **Bespoke
local visualizations**). Local-only; never calls the API.

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

   For broad monetary-policy questions, read `references/monetary-policy.md`
   before fetching; those questions need policy stance, administered rates,
   implementation tools such as OMO and standing facilities, liquidity and
   balance-sheet context, transmission channels, FX intervention and
   sterilization checks, and explicit data-gap notes. For broad bilateral
   merchandise-trade questions, read `references/bilateral-trade.md` before
   fetching; those questions need trend comparisons, YTD/annual context,
   product-driver tables, source caveats, and current policy context. For
   bilateral economic-policy or trade-policy comparisons, read
   `references/bilateral-economic-policy.md` first so the report covers the
   whole concept, including services, FDI/investment, policy talks, barriers,
   and relevant third-country pressure. For fiscal-policy revenue questions,
   read `references/fiscal-policy-revenue.md` before fetching; those questions
   need aggregate receipts, tax-source composition, distributional tax detail
   where available, non-tax component detail, policy-promise context, and
   explicit data-gap notes. For Census Business Formation Statistics questions
   about applications by industry/NAICS, read
   `references/business-formation-statistics.md` before fetching; those
   reports need ranked application facts, likely economic drivers, entry
   barriers, concentration checks where available, microeconomic and policy
   implications, and explicit caveats.

   For report-mode questions covering multiple topics, companies, or data
   sources, consider decomposing the research into parallel subagents — see
   **Subagent orchestration** below.

3. **Fetch in batches.** Once you know which series you need, issue the fetch
   calls together (multiple tool calls in one turn). Use `get_series` for 1–2
   known ids; `run_sql` with a CASE-WHEN pivot for 3+ series or joins. Keep
   results inside the 50-row cap — aggregate in SQL to the granularity a chart
   actually needs. For report tables, choose row granularity by context:
   monthly rows can work for shorter multi-year windows, roughly up to 3-5
   years, when timing, seasonality, or turning points matter; for longer
   windows, especially 5+ years, usually summarize with annual totals, YTD
   comparisons, latest/prior snapshots, or selected turning points. Do not
   default categorically to monthly or yearly rows.
4. **Compute yourself.** YoY growth, rebasing to an index, per-capita, ratios —
   write your own Python locally on the fetched values. There is no server-side
   code interpreter in this loop.
5. **Recent market data.** The DB lags for very recent market/price data — use
   `get_market_data` for current quotes, commodities, and FX.
6. **Publish, render, or build.** Quick-chart mode: build a ChartSpec object
   (see `references/chart-spec.md`) with wide-format data rows, save it to JSON,
   call `share_chart`, then run `term_chart.py render`; return the `share_url`
   and paste the terminal preview into your reply inside a triple-backtick code
   block. Terminal-chart-only mode: build the same ChartSpec, save it to JSON,
   run `term_chart.py render`, and paste the terminal output into your reply
   without publishing only if the user explicitly requested no share link.
   Report mode: build a report object (see
   `references/report-spec.md` and **Detailed reports** below), save it to JSON,
   call `share_report`, then run `term_chart.py report`; return the `share_url`
   and paste the terminal previews into your reply inside a triple-backtick code
   block. If a publish validation error occurs, fix and republish before
   rendering the final terminal preview from the corrected object.
   Bespoke-viz mode: save each fetched result to a JSON file with
   `build_viz.py save` (no retyping), author an HTML file,
   `build_viz.py assemble`, `build_viz.py render` to screenshot and iterate,
   then give the user the local file path (see **Bespoke local
   visualizations**).

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
3. Save each fetched result to its own JSON file so a later charting step can
   load the exact numbers instead of re-querying FactIQ or retyping them.
   Right after each fetch, run (no retyping — it copies the payload from the
   transcript), giving each file a thread-unique name and a --match on a
   distinctive bit of your own SQL so a sibling agent's result can't be grabbed:
   `python3 {skill_dir}/scripts/build_viz.py save --tool run_sql --match "<distinctive SQL fragment>" --out /tmp/factiq-raw/{thread_label}-<name>.json`
4. Compute derived metrics (YoY, ratios, indices) yourself.
5. Return your findings as a structured block:

FINDINGS:
- sub_question: (echo it back)
- series_used: [{schema, series_id, title}, ...]
- sql_queries: [the exact SQL you ran, formatted multi-line]
- data: [{columns: [...], rows: [...]}, ...] — the actual fetched/computed values
- raw_data_files: [/tmp/factiq-raw/{thread_label}-*.json, ...] — the files you
  saved in step 3, so a downstream viz/report step loads exact data
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
You are a FactIQ report assembler. Build a complete report object, publish it
with share_report, and render terminal previews for its charts. Do NOT do any
data discovery or fetching — all data is provided below.

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
6. Call share_report with question, report, and model. After it succeeds, save
   the full share_report argument object to JSON and run:
   `python3 {skill_dir}/scripts/term_chart.py report --report <json-file> --charset ascii --color never`
7. Return the share_url and paste the terminal previews into the reply inside a
   triple-backtick code block.
```

Launch the assembler:

```
Agent(prompt="<assembler prompt with spec + findings>", label="report-assembler")
```

The assembler has the full spec in context, so it builds the report object
correctly on the first attempt. It calls `share_report` itself and returns
the `share_url` plus terminal previews, which you relay to the user by pasting
the previews inside a triple-backtick code block.

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
3-section report (one per thread), calls `share_report`, renders terminal
previews, and returns both.

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
- **Bilateral trade gets report structure.** Treat "latest trend in trade
  between A and B" as a compact report unless the user explicitly asks for only
  a quick chart. Follow `references/bilateral-trade.md`: latest month, YoY,
  YTD, annual context, balance, product drivers for both directions, policy
  context, and mirror-statistics caveats.
- **Bilateral policy gets concept coverage.** Treat questions like "compare A
  and B trade policy" or "discuss A and B's joint economic policy" as broad
  policy reports, not goods-only trade reports. Follow
  `references/bilateral-economic-policy.md`: define the economic concept, cover
  relevant dimensions such as goods, services, FDI/investment, tariff and
  non-tariff barriers, active bilateral talks, sector strategy, third-country
  pressure, and explicit data gaps.
- **Monetary policy gets implementation coverage.** Treat questions about a
  central bank's policy stance, monetary policy over time, OMO, reserve
  liquidity, policy corridors, transmission, or FX intervention as broad
  monetary-policy reports unless the user explicitly asks for one narrow rate
  chart. Follow `references/monetary-policy.md`: include the policy target and
  market rate, administered rates such as IORB where relevant, OMO and standing
  facilities, balance-sheet and reserve conditions, communications, macro
  backdrop, FX channel, intervention/sterilization checks, and data-gap notes.
- **Fiscal-policy revenue gets layered coverage.** Treat questions about tax
  receipts, non-tax revenue, revenue by payer group, or tax/fiscal policy under
  a government as broad fiscal-policy reports unless the user explicitly asks
  for one aggregate chart. Follow `references/fiscal-policy-revenue.md`: start
  with aggregate receipts, then add major tax sources, income-bracket and
  corporate-size detail where official data exist, named non-tax components,
  a sourced policy-promise alignment note when relevant, and explicit timing
  or availability caveats.
- **Business formation by industry gets interpretation.** Treat Census BFS
  questions about applications by industry/NAICS as industry-analysis reports,
  not ranked tables, unless the user explicitly asks for only a ranking.
  Follow `references/business-formation-statistics.md`: show application facts,
  explain likely drivers for high and low industries, discuss entry barriers,
  regulation, capital intensity, incumbents, concentration metrics where
  available, microeconomic and policy implications, and distinguish measured
  findings from inferred explanations.

The `share_report` tool validates the report against FactIQ's real chart
schemas server-side, stores it as a completed public run, and returns the
`share_url`. After it succeeds, render the report object with
`term_chart.py report`, then paste the previews into your reply so the user gets
both the link and visible terminal previews.
The report appears in your FactIQ history and can be forked by anyone who opens
the share link.

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
| `save --out F.json [--tool run_sql] [--match STR] [--index N] [--list]` | Copy a tool result's **raw JSON from the harness transcript** to `F.json` — the shell copies the bytes, you never retype the data. Feeds `assemble --data`. Stdlib only. |
| `assemble --template T.html --data k1=f1.json k2=f2.json … --out O.html [--open]` | Inject on-disk JSON into your HTML at the `__FACTIQ_DATA__` marker; write one portable, self-contained file. Stdlib only. List **all** key=path pairs after the one `--data` flag. |
| `render O.html [--out P.png] [--width N] [--height N] [--full-page] [--selector CSS] [--wait MS]` | Screenshot the file in headless Chromium and report JS/console errors + failed asset loads. Installs Playwright + Chromium into `~/.factiq/viz-venv` on first run (uses `uv` if available, else a stdlib venv). |

The loop that makes this work — **fetch → save → author → assemble → render →
look → fix**:

1. Fetch the data with the MCP tools, then **save each result to a JSON file
   with `build_viz.py save` — do not retype it via Write**. The MCP tools return
   their payload into your context, not to disk; `save` lifts that exact payload
   back out of the harness transcript so the shell copies the bytes (never
   re-emit a ~100-row result by hand — it double-pays the tokens and one
   mistyped digit ships a wrong chart with no error). Run one `save` per fetch,
   pinning the call with `--tool`/`--match`:
   ```bash
   python3 scripts/build_viz.py save --match "korea_customs" --out /tmp/korea.json
   ```
   The file holds the tool's own `{columns, results, …}` payload — see
   `references/viz-guide.md` (**Saving data without retyping**) for `--list`,
   `--index`, and the fallback when a transcript can't be found. Because the MCP
   caps results at 50 rows, this is context-cheap; aggregate or window in SQL to
   get exactly the rows the viz needs.
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
which is also all it needs. For `build_viz`, persist that (already small) result
to a JSON file with `build_viz.py save` before assembling — it copies the
payload from the transcript so you never retype the rows.

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
- `references/bilateral-trade.md` — report workflow and SQL templates for
  country-pair trade questions: monthly totals, latest/YTD/annual comparisons,
  HS product drivers, value-vs-quantity guardrails, source caveats, and policy
  context.
- `references/bilateral-economic-policy.md` — report pattern for broad
  country-pair economic-policy and trade-policy comparisons: concept coverage,
  services and FDI/investment checks, barriers, bilateral talks, sector
  strategy, third-country policy pressure, and data-gap disclosure.
- `references/monetary-policy.md` — report pattern for monetary-policy
  questions: policy stance, administered rates, OMO and standing facilities,
  balance-sheet and reserve liquidity, transmission channels, FX intervention
  and sterilization checks, and operating-framework caveats.
- `references/fiscal-policy-revenue.md` — report pattern for government
  revenue and fiscal-policy questions: aggregate tax/non-tax receipts, tax
  source composition, income-bracket and corporate-size distributional checks,
  non-tax component detail, campaign-promise alignment, and data-gap caveats.
- `references/business-formation-statistics.md` — report pattern for Census
  Business Formation Statistics and industry/NAICS application questions:
  application facts, likely economic drivers, entry barriers, concentration
  checks, microeconomic and policy implications, and BFS caveats.
- `references/viz-guide.md` — bespoke local HTML visualizations with
  `build_viz.py`: the assemble/render loop, the `DATA` contract, technique
  selection (ECharts/D3/Canvas/WebGL), a legibility checklist, starter recipes.
- `references/schemas.md` — what lives in each schema. The `get_data_catalog`
  tool is the live, authoritative version; `search_datasets` / `describe_dataset`
  drill into individual datasets on demand.
