# Domain Report Patterns — and the Method Behind Them

Each file in this folder is a **domain playbook** for answering a whole class
of broad questions as a complete report. But the folder's real content is a
single method of analysis that every playbook instantiates. Read the method
once; use the routing table to pick a playbook; when no playbook covers the
domain, apply the method directly — it is the playbook generator.

**When to consult this folder:** the question is broad and analytical (a
"discuss / compare / explain / what's driving" question). Read the matching
pattern file **before fetching data** — the method changes what you fetch,
not just how you write it up.

**When to skip it:** quick-chart questions ("plot the fed funds rate") and
single-value lookups. Then follow the normal workflow in SKILL.md.

## The method: dialectical analysis

Economic facts are produced by opposing forces. A price is a standoff between
buyer and seller; a policy rate is a wager against market expectations; a
trade statistic is one side's account of a two-sided transaction; a tax
receipt is the residue of a fight between a statute and the taxpayers
arranging their affairs around it. A report that presents only the headline
reading is not neutral — it has silently taken one side of a live argument.

So every report in a covered domain moves through three passes, in the schema
popularly credited to Hegel (his own term for the resolution, *Aufhebung* —
sublation — is the useful one: preserve what is true in each side, cancel
what is naive, lift the claim to the level where the tension resolves):

### 1. Thesis — the strongest surface reading

Fetch the headline series and state what it appears to say, at full strength.
Steelman it — a weak thesis makes the whole exercise theater. This is the
official narrative, the consensus view, the number a wire story would lead
with. In investment terms: what is already priced in.

### 2. Antithesis — the strongest contradiction, fetched, not footnoted

Now build the best case *against* the thesis from the data. This is the pass
most analysis skips, and it is the pass that produces every finding worth
publishing. The antithesis must be **fetched** — it changes the SQL you run —
not gestured at in a caveats paragraph. The recurring moves:

| Move | Question it asks | Typical fetch |
|---|---|---|
| **Measurement** | What does this statistic fail to see? | Alternative measures (U-6 beside U-3), mirror statistics, revision history, coverage notes |
| **Composition** | Does the aggregate hide divergence? | Disaggregate — by sector, income bracket, HS chapter, firm size, region |
| **Deflation** | Is this quantity or just price? Nominal or real? | Real/volume series, deflators, value-vs-quantity splits |
| **Counterparty** | What does the other side's ledger say? | Partner-reported flows, the borrower's balance sheet to the lender's, the market's pricing of the policymaker's promise |
| **Reaction** | What counter-move has measurement or policy provoked? (Goodhart's law; the Lucas critique) | Rerouted trade after tariffs, timing shifts after tax changes, financial conditions easing under "restrictive" rates |
| **Baseline** | Is the change real or an artifact of the comparison window? | Longer windows, pre-shock baselines, same-month rather than adjacent-month comparisons |

Each playbook in this folder is, concretely, a catalog of its domain's
canonical antitheses plus tested SQL to fetch them. That is what "required
coverage" means: the contradictions a competent skeptic would raise, gathered
in advance.

### 3. Synthesis — one claim that explains both sides

Juxtaposition is not synthesis. "On the one hand X, on the other hand Y" is
an unfinished report. The synthesis is a single, higher-order claim under
which the headline *and* its contradiction are both true and both explained:
not "trade fell, but rerouting complicates the picture" but "the supply chain
did not decouple — it lengthened, and the direct-flow decline measures the
detour, not the divorce."

The synthesis is what goes in the report summary and the chart titles. And it
is provisional — today's synthesis is tomorrow's thesis (stability breeds the
instability that ends it, as Minsky put it), so close with **what to watch**:
the one or two series that would falsify your reading and when they next
print.

**The test:** if deleting your antithesis fetches would leave your summary
unchanged, you did not do the method — you decorated the thesis.

## The dialectic by domain — routing table

| Domain (triggers) | Thesis — the headline says | Canonical antitheses | The synthesis names | Playbook |
|---|---|---|---|---|
| **Bilateral merchandise trade** — "trend in trade between A and B", trade balance, HS/customs drivers | Flows between A and B rose/fell X% | Mirror statistics disagree; price moves masquerading as demand (value vs volume); rerouting through third countries; one HS chapter carrying the aggregate | What the relationship is actually doing — decoupling, lengthening, or repricing | `bilateral-trade.md` |
| **Bilateral economic policy** — "compare A and B trade policy", joint economic policy, investment/supply-chain coordination | Stated policy: communiqués, announced tariffs, talks | Revealed behavior contradicts rhetoric (cooperation language beside tightening FDI screens); goods data standing in for services and investment; third-country pressure driving the pair | The actual policy equilibrium versus the stated one | `bilateral-economic-policy.md` |
| **Monetary policy** — central-bank stance, implementation, OMO, liquidity, transmission, FX intervention | The stance as announced: rate level, path, communication | Implementation diverges from announcement (reserves, corridor, standing facilities); transmission fails (financial conditions ease under high rates); the curve prices what the bank won't promise; FX intervention unsterilized against the stance | The *effective* stance — how tight policy is where it touches the economy | `monetary-policy.md` |
| **Fiscal policy / revenue** — tax vs non-tax receipts, revenue by bracket or firm size, promise-vs-outcome | Receipts are up/down; the policy worked/failed | Inflation did the taxing (bracket creep, nominal base growth); composition shifted — who actually paid; one-offs and timing pull-forwards; promises measured against outcomes | The structural revenue story beneath the cyclical one, and whose burden moved | `fiscal-policy-revenue.md` |
| **Business formation** (Census BFS) — applications by industry/NAICS, implications | An application boom signals dynamism | High-propensity share says how many are paper entities; necessity entrepreneurship (layoffs minting LLCs); growth pooled in low-barrier industries; churn offsets entry | What *kind* of dynamism, and whether it can become employers and competition | `business-formation-statistics.md` |

Disambiguation for country-pair questions: goods-specific wording ("goods
trade", "exports/imports", "trade balance", "HS", "customs", "product
drivers") routes to `bilateral-trade.md`; broad policy wording ("trade
policy", "economic policy", "joint policy") routes to
`bilateral-economic-policy.md`, which pulls in `bilateral-trade.md` for the
merchandise-goods portion only.

## Domains without a playbook

Apply the method directly — the table above shows the shape a domain
instantiation takes. Two frequent cases:

- **Investment and company analysis** (earnings intelligence, market data).
  Thesis: the consensus narrative and what the price implies — the multiple,
  the guidance, the story management tells on the call. Antithesis: the
  variant perception — where the fetched data diverges from the narrative
  (unit economics vs the growth story, segment disclosure vs the headline
  beat, what management stopped mentioning quarter over quarter, what the
  commodity or FX inputs did to the cost base). Synthesis: the mispricing
  claim — what the market has wrong, what catalyst resolves it, and what
  evidence would kill the idea. A thesis without a named kill condition is a
  mood, not an analysis.
- **Macro questions generally** (labor, inflation, housing, energy). Thesis:
  the headline print. Antithesis: run the six moves in the table — measure,
  compose, deflate, cross-check the counterparty, look for the reaction,
  re-baseline. Synthesis: the claim that survives all six, plus what to
  watch.

## Rules the method implies

- **Report mode by default.** A question matching a pattern gets a compact
  `share_report`, not a single quick chart — a lone chart can state a thesis
  but cannot stage a dialectic. (Unless the user explicitly asks for only one
  chart.)
- **Cover the full concept.** Reducing a broad question to its easiest slice
  (monetary policy → just the rate path; trade policy → just goods flows) is
  skipping the antithesis pass by construction.
- **An antithesis you cannot fetch is disclosed, not dropped.** When the
  warehouse lacks a required counter-check (current OMO detail, services
  trade, distributional tax data), say so in the report — a named data gap is
  itself a finding about how confident the synthesis can be.
- **Measured vs inferred, always labeled.** Thesis and antithesis are fetched
  numbers; the synthesis is interpretation and must be presented as such,
  resting explicitly on the evidence from both passes.
- **Read `references/output/report-spec.md`** before authoring the report
  object — the patterns govern the data work and the argument; the spec
  governs the JSON format, sources, and lineage.

## Adding a new pattern

A playbook is a domain's dialectic written down in advance: a trigger section
(which question shapes it covers), the domain's canonical antitheses as
required coverage, tested SQL templates against the three-table schema to
fetch them, and the caveats/guardrails that keep the synthesis honest. Add
one row to the routing table above — SKILL.md points here and does not need
to change.
