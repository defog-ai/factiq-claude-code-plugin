# Fiscal Policy and Revenue Reports

Use this guide for questions about government revenue, fiscal policy, tax
receipts, non-tax receipts, revenue by taxpayer group, or whether an
administration's tax and fiscal policy matched its campaign promises.

This guide is for the full fiscal-policy concept. Do not reduce a broad
revenue or fiscal-policy question to one aggregate tax-versus-non-tax split
unless the user explicitly asks for only that split.

## Trigger Examples

- "Compare tax revenue and non-tax revenue now versus the Biden administration."
- "How much revenue came from different income brackets?"
- "Break down corporate taxes by company size."
- "What are the biggest non-tax revenue sources?"
- "Did the administration's tax policy match what it promised?"
- "Compare fiscal policy under government A and government B."

## Required Coverage

A good fiscal-policy revenue report should include:

- Aggregate receipts over the requested period: total receipts, tax receipts,
  non-tax receipts, and the tax/non-tax shares of total receipts.
- Tax composition: individual income, corporate income, payroll/social
  insurance, excise, estate/gift, customs duties, and any country-specific
  revenue categories available in the source data.
- Individual-tax distribution: income brackets, AGI bands, tax-year detail, or
  the closest official distributional series available. If the data lag the
  current period, state the latest tax year plainly.
- Corporate-tax distribution: corporate size, assets, receipts, business-size
  class, or the closest official segmentation available. If no official
  corporate-size split is available in FactIQ, say so instead of implying the
  aggregate corporation-income-tax line answers the question.
- Non-tax revenue detail: the largest available components beneath the non-tax
  total, not just one "miscellaneous receipts" line.
- Policy-credibility note: whether the administration's enacted or pursued tax
  and fiscal policy aligned with major campaign promises, kept separate from
  the receipt-data analysis.
- Methodology notes that explain timing mismatches among monthly budget
  receipts, annual budget actuals, tax-return distribution data, projections,
  and campaign-policy sources.

## Data Source Ladder

Start with the most direct official source for each layer:

1. **Current aggregate receipts.** Use Treasury Monthly Treasury Statement
   detail when available. For US reports, `treasury` MTS Table 1 is useful for
   totals, and MTS Table 4 or equivalent source data is needed for receipt
   categories and non-tax components.
2. **Historical annual budget context.** Use CBO historical budget data for
   annual federal revenues, outlays, deficits, and category context. Do not use
   projections as actuals.
3. **Individual-income distribution.** Use IRS Statistics of Income or another
   official tax-return distribution source for income brackets/AGI bands. Label
   tax year, fiscal year, and calendar year explicitly.
4. **Corporate-size distribution.** Search IRS SOI, national tax authority
   tables, or other official corporate tax datasets for size-class detail. Use
   firm assets, receipts, income, or return-size classes only when the source
   defines them. If unavailable, include a data-gap note.
5. **Policy and promise context.** Use official campaign, transition,
   legislative, budget, treasury/finance-ministry, CBO/JCT, or equivalent
   sources. For current or political claims, verify with current official or
   primary sources before writing the note.

For non-US reports, translate this ladder to the country's official treasury,
finance ministry, revenue authority, budget office, and tax-statistics agency.

## Report Shape

Use 3-5 sections for broad prompts:

1. **Headline receipts.** Show total, tax, and non-tax revenue for the latest
   period and comparison period. A bar chart usually works best.
2. **Tax composition.** Break tax revenue into the major statutory sources. Use
   shares and dollar amounts; show the biggest mix changes.
3. **Who paid the tax.** Add income-bracket and corporate-size views when
   available. If these data lag, label the latest available year and do not
   compare them as if they were current-month data.
4. **Non-tax sources.** Break non-tax revenue into named components. For US MTS
   reports, split miscellaneous receipts into components such as Federal
   Reserve earnings deposits, Universal Service Fund, and All Other when Table
   4 exposes them.
5. **Policy promises and credibility.** Summarize whether enacted or proposed
   tax/fiscal policy matched campaign promises. Keep this concise, sourced, and
   separate from the measured receipt charts.

## Guardrails

- Do not present a single aggregate tax-receipts line as a full tax-revenue
  analysis when the user asks who paid or asks for brackets, sectors, or
  company size.
- Do not label all miscellaneous receipts as "non-tax revenue" without
  explaining the largest components available in the source.
- Do not silently mix monthly MTS data with annual IRS SOI data. The units and
  timing differ; state the reporting lag.
- Do not fill distributional gaps with guesses, public-company financials, or
  one-off examples. If official size-class data is unavailable, say so.
- Do not treat campaign-promise analysis as a numerical conclusion from receipt
  data. It requires separate policy sources and should be framed as policy
  alignment, not proof of intent.
- If the report uses projections, budget estimates, or current-year partial
  totals, label them as projections or partial totals in every relevant chart.

## Useful Discovery Queries

Use these as starting points, then inspect the returned datasets and dimensions:

```text
search_datasets(query="Monthly Treasury Statement receipts tax non-tax")
search_datasets(query="historical budget revenues tax receipts")
search_datasets(query="IRS Statistics of Income income tax brackets")
search_datasets(query="IRS corporate income tax size assets receipts")
search_series(schema="treasury", terms=["receipts"])
search_series(schema="cbo", terms=["rev"])
search_series(schema="irs_soi", terms=["income", "tax"])
```

For SQL exploration, start broad:

```sql
SELECT series_id, series_title, dataset_code, frequency, measurement_units
FROM series
WHERE series_title ILIKE '%tax%'
   OR series_title ILIKE '%revenue%'
   OR series_title ILIKE '%receipt%'
LIMIT 50;
```

For dimensioned datasets, inspect available bracket or size dimensions before
fetching data:

```sql
SELECT dimension_type, dimension_code, dimension_name, COUNT(*) AS series_count
FROM dimensions
WHERE dimension_type ILIKE '%income%'
   OR dimension_type ILIKE '%bracket%'
   OR dimension_type ILIKE '%size%'
   OR dimension_type ILIKE '%asset%'
GROUP BY 1, 2, 3
ORDER BY 1, 2
LIMIT 50;
```

## Methodology Language To Include

When distributional data lag the current receipt period, say this plainly:

"Current aggregate receipts come from monthly Treasury budget data. Income-
bracket and corporate-size detail come from annual tax-return datasets, which
lag the budget data and are not available for the current month. The report
therefore uses the latest official distributional year for who-paid analysis
and the latest monthly budget data for current totals."

When non-tax detail is limited, say:

"Non-tax revenue is not one economic source. It is a budget classification
covering named miscellaneous receipt lines where available. Components are
shown separately when the source reports them; otherwise the unresolved
remainder is labeled as other miscellaneous receipts."
