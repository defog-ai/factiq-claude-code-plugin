# Business Formation Statistics Industry Reports

Use this guide for reports about Census Business Formation Statistics (BFS),
new business applications, high-propensity applications, likely-employer
applications, or industry/NAICS rankings of applications.

BFS reports should explain what the rankings may mean economically. Do not
stop at a ranked table or restate the largest and smallest values.

## Trigger Examples

- "Which industries have the most new business applications?"
- "Analyze business formation by NAICS."
- "Why are applications high in one industry and low in another?"
- "What do BFS applications imply for competition or policy?"

## Required Coverage

A good BFS industry report should include:

- The measured application facts: latest level, growth, share, rank, and
  comparison period for the requested industries or NAICS groups.
- Likely economic drivers for high and low applications: demand shifts, input
  costs, labor availability, remote/digital distribution, supply-chain changes,
  credit conditions, technology, and cyclicality where relevant.
- Microeconomic implications: entry pressure, expected churn, pricing power,
  productivity, margins, substitution, and whether applications suggest new
  competition or mostly small-scale experimentation.
- Policy implications: licensing, zoning, procurement, tax incentives,
  financing access, workforce constraints, consumer protection, and sector
  regulation when they plausibly affect entry.
- Entry structure: barriers to entry, capital intensity, regulation,
  incumbents, network effects, permits, and minimum efficient scale.
- Concentration checks where available: CR4, CR8, HHI, concentration ratios,
  or market-share measures. Establishment shares, employer-firm counts, and
  firm-size distributions are useful market-structure proxies, but do not call
  them concentration metrics. If concentration data are unavailable in FactIQ,
  state the gap rather than implying BFS alone measures concentration.
- Clear separation between data-backed findings and inferred explanations.
  Label drivers as "likely", "consistent with", or "may reflect" unless the
  report directly fetched evidence for them.

## Report Shape

Use 3-5 sections for broad BFS industry prompts:

1. **Application leaders and laggards.** Show ranks, latest values, shares,
   and changes over the requested period.
2. **Momentum and timing.** Show whether application growth is broad, recent,
   seasonal, or concentrated in a few NAICS groups.
3. **Economic drivers.** Explain likely demand, cost, technology, labor, and
   credit drivers for the highest and lowest industries. Use supporting data
   where available; otherwise mark the explanation as inference.
4. **Entry barriers and concentration.** Discuss regulation, capital intensity,
   incumbents, and concentration metrics such as CR4/CR8/HHI where available.
5. **Implications and caveats.** State what the pattern means for competition,
   policy, jobs, and local economic development, then list the BFS caveats.

## Guardrails

- Do not call applications "firm births", "new businesses", or "startups"
  without qualification. BFS measures applications; not every application
  becomes an employer firm or operating business.
- Do not treat high applications as proof of low entry barriers. Some sectors
  have many exploratory applications despite high failure rates, licensing
  hurdles, or small average scale.
- Do not infer market concentration from BFS ranks. Check CR4, CR8, HHI, firm
  counts, establishment counts, or revenue/sales shares where available.
- Do not overread industry detail. NAICS classification may be missing,
  provisional, self-reported, or incomplete, especially for applications that
  have not yet become operating firms.
- Do not mix monthly, quarterly, and annual application series without labeling
  timing and seasonality.
- Keep explanations separate from measurements: "Applications rose 18%" is a
  data finding; "lower capital needs likely helped entry" is an inference
  unless supported by separate data.

## Useful Discovery Queries

Use these as starting points, then inspect returned datasets and dimensions:

```text
search_datasets(query="Business Formation Statistics industry NAICS applications")
search_datasets(query="business applications high propensity industry")
search_datasets(query="market concentration CR4 HHI industry")
search_series(schema="census", terms=["business", "application"])
search_series(schema="census", terms=["BFS", "NAICS"])
```

For dimensioned datasets, inspect NAICS and geography dimensions before
fetching data:

```sql
SELECT dimension_type, dimension_code, dimension_name, COUNT(*) AS series_count
FROM dimensions
WHERE dimension_type ILIKE '%naics%'
   OR dimension_type ILIKE '%industry%'
   OR dimension_type ILIKE '%geo%'
GROUP BY 1, 2, 3
ORDER BY 1, 2
LIMIT 50;
```

If concentration data are needed, search separately and say when no suitable
FactIQ dataset is available. Do this across plausible schemas/datasets rather
than only inside the BFS dataset, because concentration data may come from
Economic Census, industry structure, or other market-share sources:

```sql
SELECT series_id, series_title, dataset_code, frequency, measurement_units
FROM series
WHERE series_title ILIKE '%concentration%'
   OR series_title ILIKE '%HHI%'
   OR series_title ILIKE '%CR4%'
   OR series_title ILIKE '%CR8%'
LIMIT 50;
```
