# Monetary-Policy Report Pattern

Use this guide for broad questions about monetary policy, central-bank policy
stance, policy implementation, transmission, liquidity operations, interest
rate corridors, FX intervention, or cross-country monetary-policy comparisons.

This guide is for the full policy concept. Do not reduce monetary policy to
only the policy rate, inflation, unemployment, or GDP unless the user explicitly
asks for that narrow slice.

## Trigger Phrases

Default to this pattern for prompts like:

- "Explain the Fed's current monetary policy stance."
- "Create a report on U.S. monetary policy over the past year."
- "How is the central bank implementing policy?"
- "What are current open market operations doing?"
- "Are FX interventions sterilized?"
- "Compare monetary policy transmission across countries."
- "How are interest rates, reserves, and exchange rates shaping policy?"

If the prompt is ambiguous, decide from wording:

- **Rate-only wording**: "fed funds", "policy rate", "repo rate",
  "bank rate", or "yield curve" can be a quick chart if the user asks only for
  the rate path.
- **Broad policy wording**: "monetary policy", "central-bank stance",
  "implementation", "liquidity", "OMO", "reserve balances", "IORB",
  "FX intervention", "sterilized", "transmission", or "financial conditions"
  means this guide.

## Minimum Coverage

A good monetary-policy report should include:

- The stated policy stance: target rate/range, market overnight rate, and
  policy-meeting decisions over the requested period.
- The operating framework: corridor, floor, reserve requirement, quantity
  targets, exchange-rate regime, or other country-specific implementation
  mechanism.
- Administered rates and facilities: reserve remuneration, IORB or equivalent,
  overnight reverse repo, standing lending/deposit facilities, discount window,
  marginal lending/deposit rates, reserve requirements, and other tools used by
  the central bank.
- Open market operations and liquidity implementation: repo, reverse repo,
  securities purchases or sales, balance-sheet runoff, bill issuance, central
  bank deposits, reserve-draining operations, and standing facilities.
- Balance-sheet and money-market conditions: reserves, monetary base, central
  bank assets, ON RRP or similar facility usage, short-term money-market rates,
  and liquidity stress indicators where available.
- Communications and forward guidance: statements, minutes, speeches, dots or
  projections when available, and FactIQ policy-stance series where supported.
- Transmission and financial conditions: government yields, credit spreads,
  lending rates, bank credit, mortgage rates, exchange rates, equity/credit
  conditions, and inflation expectations where relevant.
- Macro backdrop: inflation, labor market, growth, output gap, wages, or other
  mandate-relevant indicators.
- FX channel and intervention: exchange-rate moves, reserve changes, official
  FX operations, intervention objectives, and whether intervention is
  sterilized, unsterilized, unavailable, or not material for the country.

## U.S. Checklist

For Federal Reserve reports, do not stop at effective fed funds and Treasury
yields. Check and discuss:

1. **Policy target and market overnight rate.** Federal funds target range and
   effective federal funds rate.
2. **Administered rates.** IORB, ON RRP offering rate, discount/window rate,
   and any relevant standing facility rates.
3. **Open market operations.** Treasury/MBS holdings, balance-sheet runoff,
   repo and reverse repo operations, ON RRP usage, standing repo facility, and
   reserve-management operations where current data are available.
4. **Liquidity conditions.** Reserve balances, monetary base, central-bank
   assets, ON RRP balances, repo market rates, and short-term funding stress.
5. **Communications.** FOMC statements, minutes, projections, speeches, and
   FactIQ FOMC stance scores if available.
6. **Transmission.** Treasury yields, mortgage/lending rates, credit spreads,
   bank credit, dollar/FX conditions, and broader financial conditions.
7. **Macro backdrop.** PCE/CPI inflation, unemployment, payrolls, wages, and
   GDP/growth indicators.
8. **FX intervention.** State whether official U.S. FX intervention is present
   or material in the period. If not material or not observed, say so rather
   than omitting the FX channel.

## FX Intervention And Sterilization

For countries where FX intervention is relevant, include this analysis:

- Identify whether the central bank or government conducted or announced FX
  intervention, reserve sales/purchases, swap operations, or exchange-rate
  smoothing.
- Distinguish direct spot intervention from forwards, swaps, derivative
  positions, capital-flow measures, and verbal intervention.
- Explain whether the operation was likely sterilized or unsterilized:
  - **Sterilized intervention** offsets the domestic-liquidity effect through
    domestic securities, central-bank bills, repos/reverse repos, deposits,
    reserve requirements, or other liquidity-absorbing/injecting tools.
  - **Unsterilized intervention** lets the FX operation change the monetary
    base or reserve money.
- Use official balance-sheet, reserve-money, OMO, and reserve-assets data where
  available. If sterilization cannot be observed from the data, state the gap.
- Avoid implying causality from timing alone. Say "consistent with", "could
  have offset", or "the data do not prove sterilization" when evidence is
  indirect.

## Data Source Ladder

Start with the most direct official or FactIQ source for each layer:

1. **Central-bank policy and administered rates.** Search central-bank schemas
   first (`frb` for the U.S.) for policy rates, administered rates, reserve
   remuneration, corridor rates, and standing-facility rates. Use official
   central-bank webpages or releases for live rates if database coverage lags.
2. **OMO and balance sheet.** Search for central-bank assets, securities
   holdings, reserve balances, monetary base, repo/reverse repo, ON RRP,
   standing facilities, reserve requirements, and liquidity auctions. Use
   current official sources when FactIQ lacks the operation-level data.
3. **Policy communications.** Use `policy` FOMC/central-bank stance series and
   documents when available. State coverage dates and do not generalize beyond
   the corpus.
4. **Financial conditions and transmission.** Use government yields, money
   market rates, FX, credit, bank lending, mortgages, equities, and spreads
   where available.
5. **Macro backdrop.** Use inflation, labor, growth, and wage indicators from
   the relevant statistical agencies.
6. **FX intervention and reserves.** Use central-bank reserve assets, official
   intervention releases, balance-of-payments/reserve data, and exchange-rate
   series. For live FX rates, use market-data tools; for intervention claims,
   prefer official sources.

For non-U.S. reports, translate this ladder to the country's operating
framework. A corridor system, exchange-rate peg, inflation-targeting regime, or
managed float can require different charts and caveats.

## Default Report Shape

Use 3-5 sections depending on data availability:

1. **Stance and decisions.** Show the policy target/range, market overnight
   rate, and meeting decisions over the requested period.
2. **Implementation tools.** Show administered rates and open market
   operations/facilities. For the U.S., include IORB and OMO/ON RRP context.
3. **Liquidity and balance sheet.** Show reserves, monetary base, central-bank
   assets, securities holdings, or facility usage.
4. **Transmission and FX.** Show yields, money-market rates, exchange rate, and
   FX intervention/sterilization assessment where relevant.
5. **Macro backdrop and communication.** Show inflation, labor/growth data, and
   central-bank communications or stance scores that explain why policy moved.

## Useful Discovery Queries

Use these as starting points, then inspect returned datasets and dimensions:

```text
search_datasets(query="Federal Reserve interest rates IORB ON RRP OMO")
search_datasets(query="central bank open market operations repo reverse repo")
search_datasets(query="foreign exchange reserves intervention sterilized")
search_series(schema="frb", terms=["federal", "funds"])
search_series(schema="frb", terms=["interest", "reserve", "balances"])
search_series(schema="frb", terms=["reverse", "repo"])
search_series(schema="frb", terms=["monetary", "base"])
search_series(schema="policy", terms=["fomc", "stance"])
```

For broad SQL exploration:

```sql
SELECT series_id, series_title, dataset_code, frequency, measurement_units
FROM series
WHERE series_title ILIKE '%IORB%'
   OR series_title ILIKE '%interest on reserve%'
   OR series_title ILIKE '%reverse repo%'
   OR series_title ILIKE '%open market%'
   OR series_title ILIKE '%reserve balance%'
   OR series_title ILIKE '%monetary base%'
LIMIT 50;
```

For FX intervention checks:

```sql
SELECT series_id, series_title, dataset_code, frequency, measurement_units
FROM series
WHERE series_title ILIKE '%foreign exchange%'
   OR series_title ILIKE '%fx%'
   OR series_title ILIKE '%reserve assets%'
   OR series_title ILIKE '%intervention%'
LIMIT 50;
```

## Guardrails

- Do not imply that fed funds, long yields, inflation, and unemployment alone
  are a complete monetary-policy report.
- Do not silently omit IORB, reserve remuneration, standing facilities, OMO, or
  FX intervention when the prompt asks for broad monetary policy.
- Distinguish policy instruments from market outcomes and macro backdrop.
- State whether each current operational detail came from FactIQ data, an
  official source, or is unavailable.
- Use current official central-bank or treasury sources for live OMO,
  administered-rate, and FX-intervention details when database coverage lags.
- Keep measured data, official policy statements, and analyst inference
  separate. Do not infer intervention or sterilization solely from exchange-rate
  movement.
- If operation-level or intervention data are unavailable, opaque, delayed, or
  inferred from reserves, say so plainly and explain how that limits the report.
- For cross-country comparisons, compare operating frameworks before comparing
  rate levels; a floor system, corridor system, peg, or managed float changes
  which tools matter.

## Methodology Language To Include

When operational data are incomplete:

"The report separates policy stance from policy implementation. Policy-rate and
market-rate data are available in FactIQ; some current open market operations,
administered rates, and FX-intervention details may require official
central-bank sources. Where operation-level data are unavailable, the report
labels the gap rather than treating rates and macro indicators as the full
monetary-policy toolkit."

When FX intervention cannot be confirmed:

"Exchange-rate data alone do not prove intervention. The report checks official
reserve, balance-sheet, and intervention sources where available. If
sterilization cannot be observed, the report states that the evidence is
insufficient rather than classifying the operation."
