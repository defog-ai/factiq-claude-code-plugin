# Bilateral Economic-Policy Report Pattern

Use this guide for country-pair questions about joint economic policy,
bilateral policy comparisons, or broad policy areas such as trade policy,
investment policy, industrial strategy, supply-chain cooperation, energy
security, digital policy, or financial-market cooperation.

This guide is for the full economic concept. Do not reduce a broad policy
question to the easiest database slice. If the user asks specifically for
merchandise trade, customs flows, HS product drivers, exports, imports, or
trade balances, use `bilateral-trade.md`. If the user asks for trade policy or
economic policy more broadly, use this guide and pull in `bilateral-trade.md`
only for the merchandise-goods portion.

## Trigger phrases

Default to this pattern for prompts like:

- "Compare A and B trade policy."
- "What is the joint economic policy between A and B?"
- "How are A and B coordinating on investment, trade, or supply chains?"
- "Discuss A and B's economic relationship and policy direction."
- "How are global policy changes affecting A and B's bilateral relationship?"

If the prompt is ambiguous, decide from wording:

- **Merchandise-trade wording**: "goods trade", "exports/imports",
  "trade balance", "HS", "customs", or "product drivers" means
  `bilateral-trade.md`.
- **Policy wording**: "trade policy", "economic policy", "joint policy",
  "negotiations", "barriers", "investment", "services", "FDI", "supply
  chains", "industrial policy", or "third-country impact" means this guide.

## Minimum answer

A good bilateral economic-policy report should include:

- The policy concept being compared, with its important dimensions named up
  front.
- Database-backed indicators for every dimension FactIQ can support in the
  current session.
- Current official-source context for bilateral talks, agreements, stated
  policy goals, market-access issues, and sector priorities.
- Third-country policy context when a large economy plausibly affects either
  country's incentives or negotiating position.
- Explicit gaps for dimensions that matter but cannot be quantified from
  available FactIQ data or current sources.
- Clear separation between measured data, official policy statements, and the
  analyst's inference.

## Trade-policy checklist

For broad bilateral trade-policy reports, do not stop at goods trade. Cover the
following dimensions unless the user narrows the question:

1. **Goods trade.** Merchandise exports, imports, balance, product drivers, and
   reporter/source caveats. Use `bilateral-trade.md` for the HS/customs data
   workflow.
2. **Services trade.** Search FactIQ and current official sources for bilateral
   services data or services-policy priorities. If bilateral services data is
   unavailable, state the gap and use country-level context only when it is
   relevant and clearly labeled.
3. **FDI and investment.** Look for bilateral FDI stocks/flows, investment
   approvals, sectoral investment announcements, investment-promotion
   programs, and investment-screening rules.
4. **Tariff barriers.** Cover applied tariffs, FTA/CEPA tariff schedules,
   safeguard measures, anti-dumping or countervailing duties, and rules of
   origin where relevant.
5. **Non-tariff barriers.** Cover standards, certification, sanitary or
   phytosanitary rules, customs procedures, localization rules, data rules,
   licensing, procurement access, and conformity assessment.
6. **Bilateral talks and joint agenda.** Check official FTA/CEPA review pages,
   joint statements, trade-ministry releases, summit communiques, MoUs, sector
   working groups, and regulatory-cooperation announcements.
7. **Sector strategy.** Identify industries the countries are encouraging or
   protecting, such as electronics, semiconductors, autos, steel, chemicals,
   batteries, critical minerals, energy, agriculture, digital services, health,
   finance, or defense supply chains.
8. **Third-country pressure.** Check whether US, China, EU, Japan, Gulf, ASEAN,
   or other major-economy policies are changing incentives through tariffs,
   subsidies, export controls, sanctions, de-risking, friend-shoring,
   investment screening, carbon border measures, or supply-chain programs.

## Data workflow

1. Call `get_data_catalog` first and skip schemas listed under
   `schemas_without_data`.
2. Search broadly before fetching. Use dataset searches for the country names
   plus the concept terms: `trade`, `services`, `FDI`, `investment`, `balance
   of payments`, `tariff`, `industry`, `energy`, `digital`, or the sector the
   user named.
3. For goods trade, follow `bilateral-trade.md` and reuse its lineage rules.
4. For services and FDI, prefer bilateral series when available. If only
   country-level aggregates are available, use them as context rather than as
   proof of the bilateral relationship.
5. For policy details, use current official sources where possible: trade and
   industry ministries, investment-promotion agencies, central banks,
   statistical agencies, customs authorities, WTO/UNCTAD/OECD/World Bank/IMF
   pages, official FTA/CEPA pages, and government press releases.
6. For third-country context, use current official sources from the relevant
   third country or multilateral institution first. Use news or private
   analysis only when official sources do not cover the issue, and label the
   source type clearly.
7. Do local computation for ratios, growth rates, shares, and comparisons from
   fetched data. Do not infer causality from timing alone.

## Default report shape

Use 3-5 sections depending on data availability:

1. **Policy map.** Define the concept, identify the active policy dimensions,
   and state which dimensions have data versus source-only context.
2. **Measured bilateral relationship.** Show goods, services, FDI, or sector
   indicators that can be fetched. For goods, include the main merchandise
   trend and balance rather than every product-driver table unless product
   composition is central to the policy story.
3. **Negotiation agenda and barriers.** Summarize active bilateral talks,
   agreements under review, market-access goals, tariff and non-tariff
   barriers, investment initiatives, and regulatory-cooperation items.
4. **Third-country pressure.** Explain major external policies that could be
   changing either country's posture, and identify whether the pressure is
   likely to amplify, dampen, or redirect bilateral cooperation.
5. **Caveats and open gaps.** State data lags, missing bilateral services or
   FDI data, source asymmetries, and where policy inference is not proved by
   the measured data.

## Common concept checklists

Use these as starting points. Add or remove dimensions to fit the user's
specific question.

| Concept | Dimensions to check |
|---|---|
| Trade policy | Goods, services, FDI/investment, tariffs, non-tariff barriers, rules of origin, standards, customs, digital trade, supply chains, bilateral talks, third-country pressure |
| Investment policy | FDI stocks/flows, sector restrictions, screening rules, incentives, tax treaties, investment-promotion agreements, dispute mechanisms, strategic sectors, third-country capital controls or sanctions |
| Industrial policy | Target sectors, subsidies/incentives, local-content rules, procurement, technology transfer, supply-chain resilience, export controls, critical minerals, energy inputs, third-country subsidy or tariff programs |
| Energy policy | Fuel trade, electricity or grid cooperation, LNG/oil/coal exposure, renewables, critical minerals, climate rules, energy security agreements, carbon border measures, third-country sanctions or supply disruptions |
| Digital/services policy | Services trade, data localization, cross-border data rules, payments, fintech, telecom, AI/cloud policy, professional services access, visa/labor mobility, cybersecurity rules, major-platform regulation |

## Reporting rules

- Do not imply that merchandise trade explains all trade policy unless the
  prompt asks only for goods.
- Do not silently omit services, FDI, or investment from a trade-policy report.
  If the data is unavailable, say so and explain how that limits the answer.
- Keep official policy statements separate from measured economic outcomes.
  Use cautious language such as "could support", "could weigh on", or "is
  consistent with" unless the data and sources directly prove causality.
- Every numeric claim must come from fetched data in the current session.
- Every chart/table should carry database sources and lineage. Policy sections
  should cite current source URLs in report sources or methodology notes.
- When third-country policy context is included, explain why it matters for the
  two-country relationship rather than listing unrelated global developments.
