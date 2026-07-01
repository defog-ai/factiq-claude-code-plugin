# Bilateral Trade Report Pattern

Use this guide for broad country-pair merchandise trade questions, especially
phrases like "latest trend in trade between A and B", "what is driving trade",
"trade balance between A and B", or "compare exports and imports between A and
B". Unless the user explicitly asks for only a quick chart, treat these as
report-style requests and publish a compact `share_report`.

Do not use this file alone for broad "trade policy" or "economic policy"
questions. Those questions need the wider concept checklist in
`bilateral-economic-policy.md`, including services trade, FDI/investment,
tariff and non-tariff barriers, bilateral talks, sector strategy, and
third-country policy pressure. Use this file only for the merchandise-goods
portion of those reports.

Read `report-spec.md` before authoring the report object. This file covers the
extra data work and caveats that bilateral trade reports need.

## Minimum answer

A good bilateral trade report should include:

- Latest available month for each source, with exact month and coverage.
- Latest month versus the same month one year earlier.
- Year-to-date (YTD) totals through the latest common month versus prior-year
  YTD.
- Previous full-year context, usually the prior 2-3 years.
- Exports, imports, total trade, and trade balance. State the reporter view:
  reporter exports minus reporter imports.
- Product or industry driver tables for both directions of trade, at one HS
  level, with HS code, product label, current value, prior-year value, change,
  and contribution to the net change.
- A policy-context section based on current official sources when policy could
  affect the trend.
- Source caveats, especially when using mirror statistics from both reporters.

The default report shape is 3-4 sections:

1. **Headline trend and source coverage.** Latest common month, YTD read, and
   whether both reporters agree on the direction.
2. **Trend versus prior years.** One line chart of monthly exports/imports plus
   a table of annual and YTD totals, growth rates, and balance.
3. **Product drivers.** Two compact tables: A exports to B / B imports from A,
   and B exports to A / A imports from B. Prefer YTD drivers over latest-month
   drivers unless the latest-month move is the point of the question.
4. **Policy context and caveats.** Current trade agreement status, tariff and
   non-tariff issues, industrial/supply-chain policies, and source asymmetry.

## Data workflow

1. Call `get_data_catalog` first and skip schemas listed under
   `schemas_without_data`.
2. Use `search_datasets` for both country names plus `trade`, `customs`, and
   `HS`; then `describe_dataset` for each candidate trade dataset.
3. Query each reporter schema separately. `run_sql` operates inside one schema,
   so do not try to join India and Korea, China and US, etc. in one SQL call.
   Fetch comparable aggregates from each reporter, then normalize units and
   compare locally.
4. Use the `dimensions` table to filter partner, flow, commodity, and HS level.
   Do not parse series IDs unless dimension filters are unavailable.
5. Use exactly one HS level per table. Use HS-6 for cross-country comparison.
   Use national 8/10-digit detail only for within-reporter detail, and never
   sum national-detail rows together with HS-6 rows.
6. Filter value series separately from quantity/weight series. Korea KCS, China
   GACC, Japan Customs, and US Census 10-digit series can include physical
   quantities. A value report should exclude `kg`, quantity, or `_qty` series.
7. Normalize units before comparing reporters. For example, India DGCI&S is
   `US$ Million`; Korea KCS value series are `US$ Thousand`, so divide Korea
   values by 1,000 before comparing them to India values in US$ millions.
8. State reporter/source differences. Mirror statistics often differ because
   of FOB/CIF valuation, timing, exchange-rate conversion, re-exports,
   confidentiality suppressions, revisions, and reporter-specific definitions.
   Do not average reporters by default.

Useful India-South Korea substitutions:

| Reporter view | Schema | Partner filter | HS level | Value units |
|---|---|---|---|---|
| India-reported trade with South Korea | `india_trade` | `partner.dimension_code = '217'` (`KOREA RP`) | `hs_level.dimension_code = '6'` | `US$ Million` |
| Korea-reported trade with India | `korea_trade` | `partner.dimension_code = 'IN'` (`India`) | `hs_level.dimension_code = '6'` | `US$ Thousand`; divide by 1,000 |

## SQL templates

The templates below assume a trade schema with dimensions named `partner`,
`flow`, `commodity`, `hs_level`, and `reporter` (the structure used by
`india_trade`, `korea_trade`, `china_customs`, and similar customs schemas).
Replace:

- `<dataset>` with the dataset code, often the same as the schema.
- `<partner_code>` with the code discovered from `dimensions`.
- `<hs_level_code>` with the selected level, usually `6`.
- `<value_units>` with the value unit to keep, such as `US$ Million` or
  `US$ Thousand`.
- `<unit_divisor_to_usd_mn>` with `1` for US$ millions, `1000` for US$
  thousands, and `1000000` for raw US dollars.

### Discover partner, flow, HS, and units

Run this before aggregating so the filters are explicit and auditable:

```sql
SELECT d.dimension_type, d.dimension_code, d.dimension_name, COUNT(*) AS n
FROM dimensions d
JOIN series s USING (series_id)
WHERE s.dataset_code ILIKE '<dataset>'
  AND d.dimension_type IN ('partner', 'flow', 'hs_level', 'reporter')
GROUP BY d.dimension_type, d.dimension_code, d.dimension_name
ORDER BY d.dimension_type, n DESC
LIMIT 50;
```

Then verify value units:

```sql
SELECT measurement_units, COUNT(*) AS n
FROM series
WHERE dataset_code ILIKE '<dataset>'
GROUP BY measurement_units
ORDER BY n DESC;
```

### Monthly totals by flow

This is the base query for line charts, latest-month comparisons, balances, and
annual/YTD tables. The final SELECT returns the latest 24 months so the result
stays under the row cap for two flows; use the aggregate templates below for
longer annual history.

```sql
WITH bilateral_series AS (
  SELECT s.series_id,
         f.dimension_code AS flow_code,
         f.dimension_name AS flow
  FROM series s
  JOIN dimensions p ON p.series_id = s.series_id
      AND p.dimension_type = 'partner'
      AND p.dimension_code = '<partner_code>'
  JOIN dimensions f ON f.series_id = s.series_id
      AND f.dimension_type = 'flow'
  JOIN dimensions h ON h.series_id = s.series_id
      AND h.dimension_type = 'hs_level'
      AND h.dimension_code = '<hs_level_code>'
  WHERE s.dataset_code ILIKE '<dataset>'
    AND s.measurement_units = '<value_units>'
),
monthly AS (
  SELECT date_trunc('month', dp.time)::date AS month,
         bs.flow_code,
         bs.flow,
         SUM(dp.value) / <unit_divisor_to_usd_mn> AS value_usd_mn
  FROM data_points dp
  JOIN bilateral_series bs USING (series_id)
  GROUP BY 1, 2, 3
)
SELECT month, flow_code, flow, value_usd_mn
FROM monthly
WHERE month >= (SELECT MAX(month) FROM monthly) - INTERVAL '24 months'
ORDER BY month, flow_code;
```

Use this output to compute `total_trade = exports + imports` and
`balance = exports - imports` from the reporter's perspective. If exports and
imports have different latest months, use the latest common month for total
trade and balance, then state any source lag.

### Latest common month versus one year earlier

```sql
WITH bilateral_series AS (
  SELECT s.series_id,
         f.dimension_code AS flow_code,
         f.dimension_name AS flow
  FROM series s
  JOIN dimensions p ON p.series_id = s.series_id
      AND p.dimension_type = 'partner'
      AND p.dimension_code = '<partner_code>'
  JOIN dimensions f ON f.series_id = s.series_id
      AND f.dimension_type = 'flow'
  JOIN dimensions h ON h.series_id = s.series_id
      AND h.dimension_type = 'hs_level'
      AND h.dimension_code = '<hs_level_code>'
  WHERE s.dataset_code ILIKE '<dataset>'
    AND s.measurement_units = '<value_units>'
),
monthly AS (
  SELECT date_trunc('month', dp.time)::date AS month,
         bs.flow_code,
         bs.flow,
         SUM(dp.value) / <unit_divisor_to_usd_mn> AS value_usd_mn
  FROM data_points dp
  JOIN bilateral_series bs USING (series_id)
  GROUP BY 1, 2, 3
),
common_latest AS (
  SELECT month AS latest_month
  FROM monthly
  GROUP BY month
  HAVING COUNT(DISTINCT flow_code) = 2
  ORDER BY month DESC
  LIMIT 1
),
paired AS (
  SELECT m.flow_code,
         m.flow,
         cl.latest_month,
         SUM(m.value_usd_mn) FILTER (
           WHERE m.month = cl.latest_month
         ) AS latest_value_usd_mn,
         SUM(m.value_usd_mn) FILTER (
           WHERE m.month = cl.latest_month - INTERVAL '1 year'
         ) AS prior_year_value_usd_mn
  FROM monthly m
  CROSS JOIN common_latest cl
  WHERE m.month IN (cl.latest_month, cl.latest_month - INTERVAL '1 year')
  GROUP BY m.flow_code, m.flow, cl.latest_month
)
SELECT flow_code,
       flow,
       latest_month,
       latest_value_usd_mn,
       prior_year_value_usd_mn,
       latest_value_usd_mn - prior_year_value_usd_mn AS change_usd_mn,
       (latest_value_usd_mn / NULLIF(prior_year_value_usd_mn, 0) - 1) * 100
         AS yoy_percent
FROM paired
ORDER BY flow_code;
```

### YTD versus prior-year YTD

```sql
WITH bilateral_series AS (
  SELECT s.series_id,
         f.dimension_code AS flow_code,
         f.dimension_name AS flow
  FROM series s
  JOIN dimensions p ON p.series_id = s.series_id
      AND p.dimension_type = 'partner'
      AND p.dimension_code = '<partner_code>'
  JOIN dimensions f ON f.series_id = s.series_id
      AND f.dimension_type = 'flow'
  JOIN dimensions h ON h.series_id = s.series_id
      AND h.dimension_type = 'hs_level'
      AND h.dimension_code = '<hs_level_code>'
  WHERE s.dataset_code ILIKE '<dataset>'
    AND s.measurement_units = '<value_units>'
),
monthly AS (
  SELECT date_trunc('month', dp.time)::date AS month,
         bs.flow_code,
         bs.flow,
         SUM(dp.value) / <unit_divisor_to_usd_mn> AS value_usd_mn
  FROM data_points dp
  JOIN bilateral_series bs USING (series_id)
  GROUP BY 1, 2, 3
),
common_latest AS (
  SELECT month AS latest_month
  FROM monthly
  GROUP BY month
  HAVING COUNT(DISTINCT flow_code) = 2
  ORDER BY month DESC
  LIMIT 1
),
ytd AS (
  SELECT m.flow_code,
         m.flow,
         EXTRACT(YEAR FROM m.month)::int AS year,
         SUM(m.value_usd_mn) AS value_usd_mn
  FROM monthly m
  CROSS JOIN common_latest cl
  WHERE EXTRACT(MONTH FROM m.month) <= EXTRACT(MONTH FROM cl.latest_month)
    AND EXTRACT(YEAR FROM m.month) IN (
      EXTRACT(YEAR FROM cl.latest_month),
      EXTRACT(YEAR FROM cl.latest_month) - 1
    )
  GROUP BY m.flow_code, m.flow, EXTRACT(YEAR FROM m.month)
),
paired AS (
  SELECT y.flow_code,
         y.flow,
         MAX(y.value_usd_mn) FILTER (
           WHERE y.year = EXTRACT(YEAR FROM cl.latest_month)
         ) AS current_ytd_usd_mn,
         MAX(y.value_usd_mn) FILTER (
           WHERE y.year = EXTRACT(YEAR FROM cl.latest_month) - 1
         ) AS prior_ytd_usd_mn
  FROM ytd y
  CROSS JOIN common_latest cl
  GROUP BY y.flow_code, y.flow
)
SELECT flow_code,
       flow,
       current_ytd_usd_mn,
       prior_ytd_usd_mn,
       current_ytd_usd_mn - prior_ytd_usd_mn AS change_usd_mn,
       (current_ytd_usd_mn / NULLIF(prior_ytd_usd_mn, 0) - 1) * 100
         AS yoy_percent
FROM paired
ORDER BY flow_code;
```

### Previous full-year totals

```sql
WITH bilateral_series AS (
  SELECT s.series_id,
         f.dimension_code AS flow_code,
         f.dimension_name AS flow
  FROM series s
  JOIN dimensions p ON p.series_id = s.series_id
      AND p.dimension_type = 'partner'
      AND p.dimension_code = '<partner_code>'
  JOIN dimensions f ON f.series_id = s.series_id
      AND f.dimension_type = 'flow'
  JOIN dimensions h ON h.series_id = s.series_id
      AND h.dimension_type = 'hs_level'
      AND h.dimension_code = '<hs_level_code>'
  WHERE s.dataset_code ILIKE '<dataset>'
    AND s.measurement_units = '<value_units>'
),
monthly AS (
  SELECT date_trunc('month', dp.time)::date AS month,
         bs.flow_code,
         bs.flow,
         SUM(dp.value) / <unit_divisor_to_usd_mn> AS value_usd_mn
  FROM data_points dp
  JOIN bilateral_series bs USING (series_id)
  GROUP BY 1, 2, 3
),
latest AS (
  SELECT MAX(month) AS latest_month FROM monthly
)
SELECT EXTRACT(YEAR FROM m.month)::int AS year,
       m.flow_code,
       m.flow,
       SUM(m.value_usd_mn) AS value_usd_mn
FROM monthly m
CROSS JOIN latest l
WHERE m.month < date_trunc('year', l.latest_month)
  AND m.month >= date_trunc('year', l.latest_month) - INTERVAL '3 years'
GROUP BY EXTRACT(YEAR FROM m.month), m.flow_code, m.flow
ORDER BY year, flow_code;
```

### YTD product drivers by flow

Use this for the driver table. It ranks the largest absolute HS-6 changes
within each flow. Keep both positive and negative changes if they explain the
trend.

```sql
WITH hs_series AS (
  SELECT s.series_id,
         f.dimension_code AS flow_code,
         f.dimension_name AS flow,
         c.dimension_code AS hs_code,
         c.dimension_name AS product
  FROM series s
  JOIN dimensions p ON p.series_id = s.series_id
      AND p.dimension_type = 'partner'
      AND p.dimension_code = '<partner_code>'
  JOIN dimensions f ON f.series_id = s.series_id
      AND f.dimension_type = 'flow'
  JOIN dimensions h ON h.series_id = s.series_id
      AND h.dimension_type = 'hs_level'
      AND h.dimension_code = '<hs_level_code>'
  JOIN dimensions c ON c.series_id = s.series_id
      AND c.dimension_type = 'commodity'
  WHERE s.dataset_code ILIKE '<dataset>'
    AND s.measurement_units = '<value_units>'
),
monthly_hs AS (
  SELECT date_trunc('month', dp.time)::date AS month,
         hs.flow_code,
         hs.flow,
         hs.hs_code,
         hs.product,
         SUM(dp.value) / <unit_divisor_to_usd_mn> AS value_usd_mn
  FROM data_points dp
  JOIN hs_series hs USING (series_id)
  GROUP BY 1, 2, 3, 4, 5
),
common_latest AS (
  SELECT month AS latest_month
  FROM monthly_hs
  GROUP BY month
  HAVING COUNT(DISTINCT flow_code) = 2
  ORDER BY month DESC
  LIMIT 1
),
hs_ytd AS (
  SELECT hs.flow_code,
         hs.flow,
         hs.hs_code,
         hs.product,
         EXTRACT(YEAR FROM dp.time)::int AS year,
         SUM(dp.value) / <unit_divisor_to_usd_mn> AS value_usd_mn
  FROM data_points dp
  JOIN hs_series hs USING (series_id)
  CROSS JOIN common_latest cl
  WHERE dp.time >= date_trunc('year', cl.latest_month) - INTERVAL '1 year'
    AND dp.time < cl.latest_month + INTERVAL '1 month'
    AND EXTRACT(MONTH FROM dp.time) <= EXTRACT(MONTH FROM cl.latest_month)
    AND EXTRACT(YEAR FROM dp.time) IN (
      EXTRACT(YEAR FROM cl.latest_month),
      EXTRACT(YEAR FROM cl.latest_month) - 1
    )
  GROUP BY hs.flow_code, hs.flow, hs.hs_code, hs.product,
           EXTRACT(YEAR FROM dp.time)
),
paired AS (
  SELECT h.flow_code,
         h.flow,
         h.hs_code,
         h.product,
         MAX(h.value_usd_mn) FILTER (
           WHERE h.year = EXTRACT(YEAR FROM cl.latest_month)
         ) AS current_ytd_usd_mn,
         MAX(h.value_usd_mn) FILTER (
           WHERE h.year = EXTRACT(YEAR FROM cl.latest_month) - 1
         ) AS prior_ytd_usd_mn
  FROM hs_ytd h
  CROSS JOIN common_latest cl
  GROUP BY h.flow_code, h.flow, h.hs_code, h.product
),
changes AS (
  SELECT *,
         COALESCE(current_ytd_usd_mn, 0) - COALESCE(prior_ytd_usd_mn, 0)
           AS change_usd_mn
  FROM paired
),
ranked AS (
  SELECT *,
         change_usd_mn
           / NULLIF(SUM(change_usd_mn) OVER (PARTITION BY flow_code), 0)
           AS contribution_to_net_change,
         ROW_NUMBER() OVER (
           PARTITION BY flow_code
           ORDER BY ABS(change_usd_mn) DESC
         ) AS rn
  FROM changes
)
SELECT flow_code,
       flow,
       hs_code,
       product,
       current_ytd_usd_mn,
       prior_ytd_usd_mn,
       change_usd_mn,
       contribution_to_net_change
FROM ranked
WHERE rn <= 10
ORDER BY flow_code, ABS(change_usd_mn) DESC;
```

## Policy context

Trade-policy details change, so do current-source work for the policy section.
Use official sources where possible: trade ministries, customs authorities,
WTO, official FTA/CEPA pages, government press releases, and published tariff
or non-tariff measure notices. Cite those pages as `web` sources in the report
or lineage.

For broad trade-policy reports, read `bilateral-economic-policy.md` and expand
this policy section beyond goods. Cover services, FDI/investment, active
bilateral negotiations, standards/certification, sector investment priorities,
and relevant third-country policy pressure, or explicitly state which
dimensions are not available from current data and sources.

For India-South Korea, check current official information on:

- India-Korea CEPA status and any review or upgrade talks.
- Tariff reductions, rules of origin, safeguard measures, anti-dumping or
  countervailing duties, standards, certification, and other non-tariff
  barriers.
- Industrial and supply-chain policies that could affect electronics,
  semiconductors, autos, steel, petrochemicals, critical minerals, batteries,
  and intermediate inputs.
- Whether policy could amplify the observed trend, dampen it, or mainly shift
  product composition rather than total trade.

Keep policy inference separate from measured trade data: say "policy could
support" or "policy could weigh on" unless the data and sources directly prove
causality.

## Report and lineage requirements

- Every numeric claim in the report must come from fetched data in the current
  session.
- Every chart/table should carry database sources for the trade datasets and
  web sources for policy context.
- Lineage must include the actual SQL used for each reporter schema and the
  local computation used to normalize units, calculate YTD/YoY growth, and
  assemble balances.
- If only one reporter is available, still build the trend and driver sections
  from that source, then state that mirror-statistics comparison was not
  available from FactIQ for this pair.
