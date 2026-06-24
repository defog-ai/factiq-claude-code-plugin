# Report JSON and share_report

The `share_report` MCP tool (`question`, `report`, optional `model`) publishes
the report and returns the server response plus a `share_url`. The server stores
it as a completed, publicly shared FactIQ run, so the link renders on the
standard share-report page: bulleted summary, sections of narrative + charts,
per-chart Data Source line and "How we built this" lineage panel, methodology
notes. The run also appears in your FactIQ history, and anyone opening the link
can fork it into their own account.

The tool arguments are:

```
question: "How has US unemployment evolved since 2022?"
report:   { summary, sections, methodology_notes? }   # the report object below
model:    "claude-opus-4-8 (factiq-skill)"             # optional
```

`model` is a free-text label for who authored the report — pass your own
model name.

## Report structure

```json
{
  "summary": "2–4 crisp sentences. Each sentence renders as its own summary bullet.",
  "sections": [
    {
      "heading": "Section title",
      "narrative": "Plain-text paragraph(s) shown beside the section's charts.",
      "charts": [ { ...chart... } ]
    }
  ],
  "methodology_notes": "Optional caveats: adjustments, survey vintages, definitions."
}
```

- `summary` — required, ≤5,000 chars. Rendered as bullets, one per sentence.
- `sections` — 1–12 (2–5 is the sweet spot). Each needs a `heading`;
  `narrative` and `charts` are optional per section, but the report as a
  whole needs **at least one chart** and at most **16 charts total**.
- `narrative` — **plain text, no markdown**: the report page renders it
  verbatim, so `**bold**` shows literal asterisks. ≤30,000 chars.

## Charts

`chart_type`: `line | bar | table | bubble | small_multiples | stacked_area
| map | heatmap`. **Stick to `line`, `bar`, and `table`** — they take the
simple tabular format below. The other types pass through with the in-house
agent's full hydrated config structure, which is not documented here.

Tabular chart fields:

| Field | Required | Notes |
|---|---|---|
| `chart_type` | yes | `line`, `bar`, or `table` |
| `title` | yes | The finding, with numbers — same rules as ChartSpec titles |
| `columns` | yes | Column names, ≤40 |
| `data` | yes | Rows, ≤1,200: arrays matching `columns` **or** objects keyed by column name |
| `x_column` | line/bar | One of `columns` (tables default to the first column) |
| `y_columns` | line/bar | Subset of `columns` (tables default to the rest) |
| `units` | no | Y-axis label, e.g. `"Percent"` |
| `subtitle` | no | E.g. `"Seasonally adjusted, monthly"` |
| `annotations` | no | `[{"date": "<x value>", "text": "..."}]`, used sparingly |
| `sources` | recommended | See below |
| `lineage` | recommended | See below |
| `generation_methodology` | no | One sentence on how the data was assembled |

For time series, `x_column` values should be ISO date strings sorted
ascending — some endpoints return reverse-chronological rows, which would
render a backwards x-axis. Use `null` for gaps; don't drop rows. More than
~300 points per line renders slowly — thin to monthly/quarterly first.

### Sources

```json
"sources": [
  {
    "name": "Bureau of Labor Statistics",
    "program": "Current Population Survey",
    "type": "database",
    "urls": ["/series/bls::LNS14000000"],
    "titles": ["Unemployment Rate (LNS14000000)"]
  }
]
```

`name` is required; `type` is `database | web | derived` (default
`database`). For `database` sources, `urls` are site-relative series links
(`/series/{schema}::{series_id}`) with matching `titles`. Use `derived` for
metrics you computed (YoY, indexed, ratios) and `web` for web research.

### Lineage

Same DAG format as ChartSpec lineage (see `references/chart-spec.md` —
nodes with `id`, `type`, `title`, `summary`, `detail`, `inputs`, optional
`code`/`code_language`/`series_refs`, exactly one `output` node referenced
by `root_id`). Record the SQL and computations you actually ran. A chart
uploaded without `lineage` gets a one-node "uploaded chart data" stub, so
the panel still renders — but says nothing useful.

Two rules carry over from chart-spec lineage and are worth repeating
because reports get them wrong most often:

- `code` renders verbatim in a code block — write it as **formatted,
  multi-line** SQL/Python with real newlines (`\n` in the JSON string),
  never collapsed onto one line. For `code`-type nodes include the actual
  script lines you ran, not a one-line paraphrase.
- `series_refs` lists **every** series the step used (each id in the
  query's `IN (...)` list or filter, with its real title), not a single
  representative one. Each ref renders as a clickable series link. For
  very large aggregates (40+ series), list the largest contributors and
  state the full count in `summary`.

## Validation and limits

The `share_report` tool validates the report against the real chart schemas and
returns a tool error naming the failing field paths (e.g.
`sections[1].charts[0].x_column: Field required`). Fix and call it again —
nothing is published until it validates. Server caps: 12 sections, 16 charts,
1,200 rows and 40 columns per chart, 30k chars per narrative, 5k for the
summary.

## Worked example

```json
{
  "question": "How has US unemployment evolved since 2022?",
  "model": "claude-sonnet-4-6 (factiq-skill)",
  "report": {
    "summary": "US unemployment climbed from a 54-year low of 3.4% in April 2023 to 4.2% by late 2024, but the rise reflects labor-force re-entry rather than layoffs. Job openings cooled without a spike in claims.",
    "sections": [
      {
        "heading": "The headline rate bottomed in 2023",
        "narrative": "The unemployment rate's drift upward from mid-2023 came alongside rising participation, which is why economists read it as normalization rather than deterioration.",
        "charts": [
          {
            "chart_type": "line",
            "title": "US unemployment rose from 3.4% (Apr 2023) to 4.2% (Nov 2024)",
            "subtitle": "Seasonally adjusted, monthly",
            "x_column": "date",
            "y_columns": ["unemployment_rate"],
            "columns": ["date", "unemployment_rate"],
            "units": "Percent",
            "data": [
              ["2022-01-01", 4.0],
              ["2023-04-01", 3.4],
              ["2024-11-01", 4.2]
            ],
            "annotations": [{ "date": "2023-04-01", "text": "54-year low of 3.4%" }],
            "sources": [
              {
                "name": "Bureau of Labor Statistics",
                "program": "Current Population Survey",
                "type": "database",
                "urls": ["/series/bls::LNS14000000"],
                "titles": ["Unemployment Rate (LNS14000000)"]
              }
            ],
            "generation_methodology": "Headline U-3 rate, seasonally adjusted.",
            "lineage": {
              "root_id": "output",
              "nodes": [
                {
                  "id": "sql_1",
                  "type": "sql",
                  "title": "Query unemployment series",
                  "summary": "Pulled the monthly U-3 unemployment rate from the BLS schema.",
                  "detail": "",
                  "inputs": [],
                  "code": "SELECT date, value\nFROM data_points\nWHERE series_id = 'LNS14000000'\nORDER BY date",
                  "code_language": "sql",
                  "series_refs": [
                    { "schema_name": "bls", "series_id": "LNS14000000", "title": "Unemployment Rate" }
                  ]
                },
                {
                  "id": "output",
                  "type": "output",
                  "title": "Plot headline rate",
                  "summary": "Single line with the April 2023 low annotated.",
                  "detail": "",
                  "inputs": ["sql_1"]
                }
              ]
            }
          }
        ]
      },
      {
        "heading": "Sector contributions",
        "narrative": "Health care and government did the heavy lifting on payrolls through 2024 while tech shed jobs.",
        "charts": [
          {
            "chart_type": "bar",
            "title": "Health care added 652k jobs in 2024 — triple tech's losses",
            "x_column": "sector",
            "y_columns": ["jobs_added_thousands"],
            "columns": ["sector", "jobs_added_thousands"],
            "units": "Thousands of jobs",
            "data": [
              { "sector": "Health care", "jobs_added_thousands": 652 },
              { "sector": "Information (tech)", "jobs_added_thousands": -98 }
            ],
            "sources": [
              {
                "name": "Bureau of Labor Statistics",
                "program": "Current Employment Statistics (CES)",
                "type": "database"
              }
            ],
            "generation_methodology": "Year-over-year change in payroll employment by supersector."
          }
        ]
      }
    ],
    "methodology_notes": "All figures seasonally adjusted. Sector payrolls from the establishment survey; the headline rate from the household survey — the two can diverge month to month."
  }
}
```

## Workflow

1. Do the full data work first with the MCP tools (`get_data_catalog` →
   `search_datasets` / `describe_dataset` → `run_sql` / `get_series` → compute
   locally). Every number in the report must come from data you fetched this
   session. Results cap at 50 rows — aggregate in SQL to the granularity each
   chart needs (a report chart wants ≤300 points anyway).
2. Outline: 2–5 section claims, one or two charts each that prove the claim.
3. Build the report object from the fetched values — assemble it in context, or
   write the data arrays with the Write tool / a small local Python script;
   don't hand-type data rows.
4. Call `share_report` with `question`, `report` (the object), and optional
   `model`.
5. Return the `share_url` and the report's key findings.
