# FactIQ SQL Guide

SQL runs read-only against one schema per call — the `run_sql` MCP tool, with
`schema="bls"` and `sql="..."`. The server sets `search_path` to that schema,
so reference tables bare (`series`, not `bls.series`). Statements are capped at
30 seconds, and **every result is capped at 50 rows** — aggregate in SQL to the
granularity you actually need rather than pulling raw rows (see "Pivoting" and
"Efficiency" below).

## Table structure (identical in every schema)

- **`series`** — the catalog. Key columns: `series_id`, `series_title`,
  `human_friendly_title`, `human_friendly_description`, `dataset_code`,
  `frequency`, `measurement_units`, `adjusted_for_seasonality`, `state`,
  `county_or_metro_area`, `begin_time`, `end_time`, `data_type`
  (`timeseries` or `tabular`), `tabular_columns`.
- **`data_points`** — `series_id`, `time` (date), `value` (numeric).
- **`dimensions`** — `series_id`, `dimension_type`, `dimension_code`,
  `dimension_name`. Useful for discovery when titles are uninformative.
- **`tabular_data`** — JSONB `row_data` per row, for `data_type = 'tabular'`
  series only.
- **`compound_series`** — curated derived series with ids like
  `COMPOUND::...`. Fetch them with the `get_series` tool, not raw SQL.

The `get_data_catalog` tool returns the full DDL.

## Always-true conventions

- **`frequency` values are lowercase**: `'monthly'`, `'quarterly'`,
  `'annual'`, `'weekly'`, `'semiannual'`. `frequency = 'Monthly'` matches
  nothing.
- **`dataset_code` is lowercase** — use ILIKE or lowercase literals.
- The server rewrites `series_title` to
  `COALESCE(human_friendly_title, series_title)` automatically, normalizes
  frequency filters, and turns `data_points.series_id` pattern filters into
  semi-joins on `series`; the response's `transformed_query` shows what
  actually ran.
- Results come back enriched with `constituent_series` metadata
  (titles, units, source) for every series_id touched — use it for chart
  source attribution.

## Exploratory queries first

Before fetching from a dataset you haven't touched, look at 5 rows of its
catalog to learn naming conventions and units:

```sql
SELECT series_id, series_title, dataset_code, frequency,
       adjusted_for_seasonality, measurement_units
FROM series WHERE dataset_code ILIKE '<dataset>' LIMIT 5
```

Run these with `explore=true` so the server treats them as exploration.

## Keep SQL simple and broad

Don't stack ILIKE conditions — you'll miss valid rows and get zero results.
A broad query returning 50 rows beats a narrow one returning 0 (results are
capped at 50 rows either way).

```sql
-- Bad: over-filtered, likely 0 rows
SELECT series_id, series_title FROM series
WHERE dataset_code ILIKE 'jt' AND series_title ILIKE '%job openings%total nonfarm%'
  AND series_title ILIKE '%level%' AND measurement_units ILIKE '%level%'

-- Good: broad, let the results guide you
SELECT series_id, series_title, measurement_units FROM series
WHERE dataset_code ILIKE 'jt' AND series_title ILIKE '%job openings%'
  AND adjusted_for_seasonality = true
LIMIT 20
```

Prefer filtering on indexed columns (`series_id`, `dataset_code`) over text
scans. For text searches use two steps: find series_ids first, then fetch
their data.

## Never pattern-match `series_id` on `data_points`

`data_points` is enormous and its index does not serve LIKE/ILIKE — even an
anchored pattern (`series_id LIKE 'us\_census\_hs\_M\_10d\_280530%'`) scans
the whole table and dies at the 30s timeout. The same pattern against the
small `series` catalog is fast.

The server rewrites WHERE-clause LIKE/ILIKE on `data_points.series_id` into
`series_id IN (SELECT series_id FROM series WHERE ...)` automatically (the
response's `transformed_query` shows it), so those queries now run via the
index. But the rewrite covers WHERE clauses only — a pattern inside a
projection (`SUM(CASE WHEN series_id LIKE '%\_5700' THEN value END)`) is
untouched, and is fine *only if* the WHERE clause already narrows the rows.
When in doubt, resolve ids explicitly first:

```sql
-- Step 1 (fast): resolve the id list on the catalog
SELECT series_id FROM series WHERE series_id LIKE 'us\_census\_hs\_M\_10d\_280530%'

-- Step 2 (fast): fetch with an explicit IN list — uses the index
SELECT series_id, time, value FROM data_points
WHERE series_id IN ('...', '...')
```

## National vs. sub-national series — the classic trap

Geographically decomposed datasets are dominated by state/region rows; the
single national aggregate is a needle. For a national question you must
filter for the national key, not just the metric.

Caveat: server-side dataset descriptions sometimes quote *raw* title
conventions (pipe-delimited keys like `State: All India` or prefixes like
`CPI 2024`). Because your filters run against the COALESCEd friendly titles,
those exact patterns often match nothing. Filter on the natural-language
fragment instead:

- MOSPI CPI national aggregate → `series_title ILIKE '%All India%'` (add
  `'%Combined%'` for the combined rural+urban sector), NOT
  `'%State: All India%'`.
- MOSPI WPI is national-only — no state key at all. Confirm a dataset is
  geographically split before forcing a geography filter.
- To identify a CPI base-year family when titles don't say: read the
  series description from a `series` fetch, or check the base-year
  calendar average ≈ 100 in the data itself.

Never chart a single state/region as if it were the national figure. If you
can't find the national aggregate, say so rather than substituting.

## HS trade datasets

For broad bilateral merchandise-trade questions, use
`references/report-patterns/bilateral-trade.md`; it has the report trigger and ready SQL
templates for monthly totals, latest-month YoY, YTD YoY, annual totals, and top
HS product drivers.

The core guardrails:

- Filter with `dimensions` (`partner`, `flow`, `commodity`, `hs_level`) instead
  of parsing series IDs.
- Use exactly one HS level in an aggregation. HS-6 is the default for
  cross-country comparison; national 8/10-digit lines are finer detail and must
  not be summed with HS-6 rows.
- Keep value and quantity/weight series separate. For example, Korea KCS has
  value in `US$ Thousand` and weight in `kg`; a value report should filter
  `measurement_units = 'US$ Thousand'`.
- Normalize units before comparing reporters. For example, India DGCI&S values
  are `US$ Million`, while Korea KCS values are `US$ Thousand`.
- Query each reporter schema separately, then compare in local computation.
  Mirror statistics differ because of timing, valuation, re-exports, and
  revisions; state the reporter view explicitly.

## Pivoting to wide format

Chart data wants one row per time period with one column per series. Use
CASE WHEN with **GROUP BY on time** (omitting GROUP BY fails or duplicates
rows):

```sql
SELECT time,
       MAX(CASE WHEN series_id = 'LNS14000000' THEN value END) AS unemployment_rate,
       MAX(CASE WHEN series_id = 'LNS11300000' THEN value END) AS participation_rate
FROM data_points
WHERE series_id IN ('LNS14000000', 'LNS11300000')
  AND time >= '2019-01-01'
GROUP BY time
ORDER BY time
```

## Tabular data

Series with `data_type = 'tabular'` store rows in `tabular_data.row_data`
(JSONB), described by `series.tabular_columns`. The `get_series` tool handles
them transparently (returns columns + results like a timeseries) — prefer it.
For direct SQL: `row_data->>'column_name'` extracts text; cast with `::numeric`
for math.

## Efficiency

- Most questions need 2–4 data calls. Batch independent fetches in one turn.
- Don't re-fetch via `get_series` what a `run_sql` call already returned — both
  are equally chartable.
- Use `get_series` for 1–2 known ids; `run_sql` for 3+ series, joins,
  aggregations.
- Results cap at 50 rows. If a fetch comes back `"truncated": true`, aggregate
  in SQL (`GROUP BY date_trunc(...)`, a SUM/AVG/rank) rather than trying to
  pull the rest — a chart needs the aggregated result anyway.
- Zero rows means your filter missed — broaden the term or drop a condition
  and rerun. You revise faster and cheaper than the server's `auto_retry`
  LLM reviser.
