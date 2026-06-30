# FactIQ Plugin

This plugin gives you access to FactIQ's economic and financial data tools via
MCP. Read `SKILL.md` for the full workflow, tool reference, output modes, and
reference docs.

## Quick start

1. Authorize the MCP server: run `codex mcp login factiq` and complete the
   browser sign-in (email, Google, or passkey).
2. Ask any economic or financial data question — the skill activates
   automatically.

## What you can do

- **Quick chart** — one focused chart published to FactIQ as a share link.
- **Detailed report** — multi-section research report with narrative + charts.
- **Bespoke local viz** — a self-contained HTML file for custom dashboards,
  force graphs, chord diagrams, or anything the standard chart spec can't
  express.

All data discovery, fetching, and publishing goes through the FactIQ MCP tools.
The only local script is `scripts/build_viz.py` for bespoke HTML visualizations.

## Reference docs

- `references/sql-guide.md` — table structure, query idioms, pitfalls
- `references/chart-spec.md` — ChartSpec format for `share_chart`
- `references/report-spec.md` — report JSON format for `share_report`
- `references/viz-guide.md` — bespoke local HTML visualizations
- `references/schemas.md` — what lives in each data schema
