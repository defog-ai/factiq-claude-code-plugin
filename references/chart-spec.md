# ChartSpec and share-chart

`share-chart --spec chart.json` POSTs the spec to the FactIQ backend
(API-key auth) and returns `{shareId, shareUrl}` — a live, rendered chart
page. The chart is owned by your API key's user, so you can edit it in place
and restore earlier versions from the UI on `/share-chart/<id>`. The CLI
accepts either a bare ChartSpec or a `{chart: {...}, question: "..."}`
envelope.

## Minimal valid spec

Required: `id`, `title`, `type`, `xField` (object with `key`), `series`
(array), `data` (wide-format rows — one object per x value, one key per
series).

```json
{
  "id": "us-unemployment-2019-2025",
  "title": "US unemployment spiked to 14.8% in April 2020, then recovered to 4.1% by mid-2025",
  "type": "line",
  "xField": { "key": "time", "label": "Date", "format": "date", "scale": "time" },
  "series": [
    { "key": "unemployment_rate", "label": "Unemployment rate" }
  ],
  "yAxisLabel": "Percent",
  "data": [
    { "time": "2019-01-01", "unemployment_rate": 4.0 },
    { "time": "2019-02-01", "unemployment_rate": 3.8 }
  ],
  "sources": [
    {
      "name": "Bureau of Labor Statistics",
      "program": "Current Population Survey (LNS14000000)",
      "url": "",
      "type": "database"
    }
  ],
  "annotations": [
    { "date": "2020-04-01", "text": "Pandemic peak" }
  ]
}
```

## Titles make a claim

The title is the chart's headline insight, not a description. It must name
the entity, the metric, and the claim with numbers, self-contained:

- Bad: "Employment Trends" (descriptive)
- Bad: "Healthcare added 2.8M jobs since 2020" (which country?)
- Good: "US healthcare added 2.8M jobs since 2020 while retail shed 340K"

If the claim depends on a time window, keep the range in the title.

## Chart types

| `type` | Use when |
|---|---|
| `line` | Trends over time (default for timeseries) |
| `area` | Single magnitude over time |
| `bar` | Discrete comparisons or short categorical time spans |
| `stacked_area` | Composition of a total over time |
| `pie` | Single-period composition, few categories |
| `scatter` | Two metrics correlated; needs `yField` |
| `bubble` | Scatter + a size dimension; needs `yField` + `sizeField`; no date x-axis |
| `small_multiples` | Same metric across many entities; set `facetField` |
| `map` | Geographic distribution; needs `mapConfig` `{visualizationType, mapId, geoKey, valueKey}` |

## Field reference

- `xField` / `yField` / `sizeField`: `{key, label?, format?, scale?}`.
  `format`: `date | number | currency | percent | text`. For time x-axes use
  `format: "date", scale: "time"` with ISO date strings.
- `series[]`: `{key, label?, type?, color?, stacked?, dashed?}` — `key` must
  match a key in each `data` row. Omit `color` unless you have a reason; the
  renderer assigns a palette.
- `data`: array of flat objects, `string | number | null` values. Use `null`
  for gaps, don't drop rows.
- `sources[]`: `{name, program, url, type}` where `type` is
  `database | web | derived`. Pull `name`/`program` from the
  `constituent_series` metadata the `run_sql` / `get_series` responses include.
  Use `derived` for computed metrics (YoY, indexed, ratios).
- `annotations[]`: `{date: "2020-04-01", text: "..."}` — use sparingly to
  mark events the narrative references.
- `subtitle`, `description`, `notes[]`, `footnote` — optional supporting
  text.

## Data lineage (`lineage`)

Always include a `lineage` DAG in the spec. The share page renders it as a
"How we built this" panel; without it the chart shows only the one-line
Data Source citation. It records the steps you actually took — searches,
SQL, computations — ending in a single `output` node:

```json
"lineage": {
  "root_id": "out",
  "nodes": [
    {
      "id": "sql1", "type": "sql", "inputs": [],
      "title": "BLS unemployment rates",
      "summary": "Monthly U-3 and U-6 from bls.data_points, 2019–2025",
      "detail": "",
      "code": "SELECT date, series_id, value\nFROM data_points\nWHERE series_id IN ('LNS14000000', 'LNS13327709')\n  AND date >= '2019-01-01'\nORDER BY date",
      "code_language": "sql",
      "series_refs": [
        { "schema_name": "bls", "series_id": "LNS14000000", "title": "Unemployment Rate (U-3)" },
        { "schema_name": "bls", "series_id": "LNS13327709", "title": "Total unemployed plus marginally attached (U-6)" }
      ]
    },
    {
      "id": "calc", "type": "code", "inputs": ["sql1"],
      "title": "Computed YoY change",
      "summary": "12-month difference on the monthly rate",
      "detail": "", "code": "yoy = rate - rate.shift(12)", "code_language": "python"
    },
    {
      "id": "out", "type": "output", "inputs": ["calc"],
      "title": "US unemployment rate, 2019–2025",
      "summary": "Line chart of U-3 and U-6 with YoY overlay",
      "detail": ""
    }
  ]
}
```

Node fields: `id`, `type` (`sql | series | code | web | market | output`),
`title`, `summary`, `detail`, `inputs` (upstream node ids — `[]` for leaves).
Optional per type: `code` + `code_language` (shown as a code block — put the
exact SQL or Python you ran here), `series_refs[]`
(`{schema_name, series_id, title}`, rendered as links to the series pages),
`web_sources[]` (`{url, title}`) for `web` nodes, and `market_ticker` for
`market` nodes. One node per real step; exactly one `output` node, referenced
by `root_id`.

Two rules the panel depends on:

- **`code` is formatted, multi-line code.** It renders verbatim in a code
  block — a query collapsed onto one line shows up as one unreadable line.
  Embed real newlines (`\n` in the JSON string) exactly as you would
  present the SQL or Python to a reader. The same goes for `code` on
  `code`-type nodes: include the actual script lines you ran, not a
  one-line paraphrase.
- **`series_refs` is the complete list.** Include every series the step
  actually used — every id in the query's `IN (...)` list or filter, with
  its real title — not one representative example. Each ref becomes a link
  on the share page; readers use them to audit the chart. If a query
  aggregates a very large set (say 40+ series), list the largest
  contributors and state the full count in `summary`.

## Workflow

1. Fetch the data with the MCP tools — `run_sql` (a CASE-WHEN pivot for
   several series) or `get_series` (one series). Results cap at 50 rows, so
   aggregate to chart granularity in SQL (`GROUP BY date_trunc(...)`) or window
   a series with `from_year` / `to_year`; a line chart wants a few hundred
   points at most.
2. Build the wide-format `data` array from the fetched values — compute any
   derived metrics (YoY, indexing, ratios) yourself, and emit the full spec to
   `chart.json` (write it with the Write tool, or a small local Python script).
   Sort rows by the x value first — some series come back reverse-chronological,
   which would render a backwards x-axis.
3. Validate locally that every `series[].key` and `xField.key` exists in the
   `data` rows, and that the spec carries both `sources[]` and a `lineage`
   DAG (see above) — they are what the share page shows as the Data Source
   line and the "How we built this" panel.
4. `python3 scripts/factiq.py share-chart --spec chart.json --question "..."`
5. Return the `shareUrl`.
