# Bespoke local visualizations

This is the third FactIQ output mode, alongside the `share_chart` and
`share_report` tools. Those publish to factiq.com against fixed schemas; this one
produces a **self-contained local HTML file** you author freely. There is no
spec to satisfy and no fixed chart-type list — you write whatever HTML/JS the
question calls for, render it, look at it, and fix what's wrong. That last
loop is the method; everything else is plumbing.

Use it when the answer wants something the ChartSpec can't express: a custom
layout, a multi-panel dashboard, a force/flow/chord diagram, an annotated
narrative, a novel encoding, an interactive cross-filtered view, or just
fine-grained control over a chart's look.

## The two commands

`scripts/build_viz.py` is local-only (it never calls the FactIQ API):

| Command | Purpose |
|---|---|
| `assemble --template T --data k1=f1.json k2=f2.json … --out O.html [--open]` | Inject on-disk JSON into your HTML at the `__FACTIQ_DATA__` marker; write one portable file. Stdlib only. Pass **all** key=path pairs after the single `--data` flag (or repeat the flag — both work). |
| `render H.html [--out P.png] [--width] [--height] [--full-page] [--selector CSS] [--wait MS]` | Screenshot the file in headless Chromium and report JS/console errors + failed requests. Installs Playwright + Chromium into `~/.factiq/viz-venv` on first run. |

`render` exits **5** when the page logged a JS error, an uncaught exception,
or a failed asset request — treat a non-zero exit as "the viz is broken, read
stderr," not "minor warning."

## The workflow

1. **Fetch the data with the MCP tools, then save each result to disk.** Call
   `run_sql` / `get_series`, then write the tool's result to a JSON file with
   the Write tool — `build_viz` reads its data from files, not from your
   context. Results cap at 50 rows, so aggregate in SQL (`GROUP BY
   date_trunc(...)`) or window a series to exactly the rows the viz needs. Save
   the whole tool result (it carries `columns` + `results`), e.g. to
   `/tmp/jobs.json`.
2. **Copy the shell and author the viz.** Start from `assets/viz-shell.html`
   (or write your own). Add any CDN `<script>` you need, then write the
   visualization. Keep the `__FACTIQ_DATA__` marker — that is where the data
   lands. Do **not** paste data rows into the HTML; that defeats the point.
3. **Assemble** the self-contained file. Bespoke vizzes usually combine
   several series, so list every file after one `--data` flag:
   ```bash
   python3 scripts/build_viz.py assemble \
     --template my_viz.html \
     --data jobs=/tmp/jobs.json gdp=/tmp/gdp.json vac=/tmp/vac.json \
     --out /tmp/out.html
   ```
   `--data` takes **all** the `key=path` pairs that follow it; don't repeat the
   flag once per file expecting each to stick. (Repeating it does now work too,
   but the single-flag form above is canonical.) Each file lands at its key, so
   above you get `DATA.jobs`, `DATA.gdp`, and `DATA.vac`.
4. **Render and look.** Screenshot it, then actually read the image:
   ```bash
   python3 scripts/build_viz.py render /tmp/out.html --out /tmp/out.png
   ```
   If exit code is 5, read the errors on stderr and fix them first — a JS
   error usually means a blank page. Then inspect the screenshot against the
   legibility checklist below and iterate: edit → assemble → render → look,
   until it is actually right. **One render pass is never enough** for bespoke
   work; budget at least two or three.

   **Caveat for tall pages:** headless Chromium lazy-paints off-screen
   canvases, so on a long page a `--full-page` shot can show every
   below-the-fold ECharts/Canvas/WebGL chart as blank even though it renders
   fine in a real browser. Don't conclude those charts are broken — verify a
   suspect one with `render … --selector "#chart-id"`, which scrolls that
   element into view before shooting it.
5. **Deliver.** Tell the user the file path; offer `assemble … --open` (or
   `open /tmp/out.html`) to open it in their browser. The file is portable and
   needs only internet for its CDN libraries.

## The data contract

The `__FACTIQ_DATA__` marker only works inside this exact element:

```html
<script id="factiq-data" type="application/json">
__FACTIQ_DATA__
</script>
```

`assemble` substitutes the marker wherever it sits, but the page reads the
data back by `id`, so the marker **must** live inside a
`<script id="factiq-data" type="application/json">` tag. If you author a
template from scratch, reproduce that element verbatim. Drop the bare marker
anywhere else — an HTML comment, a `<div>`, the wrong id — and
`getElementById("factiq-data")` returns `null`, giving
`Cannot read properties of null (reading 'textContent')` and a blank page.
(Starting from `assets/viz-shell.html` gives you the element for free.)

After `assemble`, the page exposes one global:

```js
const DATA = JSON.parse(document.getElementById("factiq-data").textContent);
```

`DATA[key]` is the **full FactIQ payload** for the file you passed as
`--data key=file.json` — i.e. exactly the `run_sql` / `get_series` tool result
you saved to that file:

- `run_sql` results: `DATA.key.results` is an array of **positional arrays**
  aligned to `DATA.key.columns` (e.g. `["DC", 5.5, "2026-04-01"]`), *not* an
  array of objects. Objectify them once at the top:
  ```js
  const cols = DATA.key.columns;
  const rows = DATA.key.results.map((r) =>
    Object.fromEntries(cols.map((c, i) => [c, r[i]]))
  );
  ```
- `get_series` and `get_market_data` payloads keep their own shape — eyeball
  the tool result (or `console.log(DATA.key)` once) before assuming a layout.

Sort by your x value in JS before plotting — some endpoints return data
reverse-chronological, which renders a backwards axis. Use `null` for gaps;
don't drop rows.

The assembler escapes the data so a literal `</script>`, `<`, `&`, or a
Unicode line separator inside a value can't break out of the page —
`JSON.parse` restores the original text, so values are unchanged.

## Choosing the technique

Match the tool to the shape of the visualization, not habit:

- **ECharts** (`echarts@5`) — the path of least resistance for anything
  chart-shaped: lines, bars, areas, scatter, candlestick, heatmaps, sankey,
  graphs, radar. Great defaults, theming, dark mode, handles tens of
  thousands of points. Reach for this first unless the layout is the point.
- **D3** (`d3@7`) — when you need a custom layout or scale: force-directed
  graphs, hierarchies (treemap/sunburst/pack), chord, arbitrary SVG with
  hand-placed marks and annotations. More code, more control.
- **Raw SVG / Canvas** — hand-drawn diagrams, small bespoke marks, or
  high-cardinality scatter where SVG nodes get heavy (Canvas past ~10k marks).
- **WebGL / Three.js / regl** — only past ~100k marks or for genuine 3D.
- **Plotly** (`plotly@2`) — when you want scientific zoom/hover interactivity
  out of the box and don't need custom layout.

A "dashboard" is just a CSS grid of several of the above in one file — not a
separate technique. Lay panels out with CSS grid/flex inside `#root`.

## Legibility checklist (what to look for in the screenshot)

- Axis/tick/legend labels don't overlap, clip, or run off the edge.
- Scales make sense: no flat line because an outlier blew out the domain; log
  scale where the data spans orders of magnitude; y-axis baseline honest.
- Time axes are chronological and use real date formatting.
- The title states the **finding with numbers**, not the topic — same bar as
  `share_chart` (see `chart-spec.md`). Carry a source line at the bottom.
- Color: enough contrast on the dark background; a sane categorical palette;
  not red/green-only for accessibility. In ECharts the legend swatch takes its
  color from `series.itemStyle.color`, not `series.lineStyle.color` — a line
  with a custom `lineStyle.color` but no `itemStyle.color` gets a mismatched
  default-palette legend dot. Set both (or just `color` on the series).
- Nothing is blank or half-rendered — if it is, check stderr for a JS error
  and raise `--wait` if an animation/CDN load needed more time. But a blank
  canvas chart *below the fold* in a `--full-page` shot is usually just
  headless lazy-painting, not a real failure — re-check it with `--selector`
  before debugging (see the render caveat above).
- Multi-panel: panels align, share scales where comparison is intended, and
  each panel is individually readable at the chosen viewport size.

## Starter recipes

These are starting points to adapt, not templates to fill in. Each assumes
the shell's `DATA` global and a CDN `<script>` added in `<head>`.

### ECharts line chart
```html
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
```
```js
const cols = DATA.jobs.columns;
const rows = DATA.jobs.results
  .map((r) => Object.fromEntries(cols.map((c, i) => [c, r[i]])))
  .sort((a, b) => String(a.date).localeCompare(String(b.date)));
const root = document.getElementById("root");
const el = document.createElement("div");
el.style.cssText = "width:100%;height:480px";
root.appendChild(el);
echarts.init(el, "dark").setOption({
  backgroundColor: "transparent",
  title: { text: "US payrolls grew 2.1% in 2024" },
  tooltip: { trigger: "axis" },
  xAxis: { type: "category", data: rows.map((r) => r.date) },
  yAxis: { type: "value" },
  series: [{ type: "line", smooth: true, data: rows.map((r) => r.value) }],
});
```

### D3 force-directed graph (custom layout)
```html
<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
```
```js
// DATA.edges columns: [source, target, weight]; objectify, then build nodes.
const ec = DATA.edges.columns;
const links = DATA.edges.results.map((r) =>
  Object.fromEntries(ec.map((c, i) => [c, r[i]]))
);
const ids = [...new Set(links.flatMap((l) => [l.source, l.target]))];
const nodes = ids.map((id) => ({ id }));
const W = 1200, H = 760;
const svg = d3.select("#root").append("svg").attr("viewBox", `0 0 ${W} ${H}`);
const sim = d3
  .forceSimulation(nodes)
  .force("link", d3.forceLink(links).id((d) => d.id).distance(80))
  .force("charge", d3.forceManyBody().strength(-220))
  .force("center", d3.forceCenter(W / 2, H / 2));
const link = svg.append("g").attr("stroke", "#3a3f4b").selectAll("line")
  .data(links).join("line").attr("stroke-width", (d) => Math.sqrt(d.weight));
const node = svg.append("g").selectAll("circle")
  .data(nodes).join("circle").attr("r", 6).attr("fill", "#4f8cff");
sim.on("tick", () => {
  link.attr("x1", (d) => d.source.x).attr("y1", (d) => d.source.y)
      .attr("x2", (d) => d.target.x).attr("y2", (d) => d.target.y);
  node.attr("cx", (d) => d.x).attr("cy", (d) => d.y);
});
```
Force layouts settle over time — give `render` a larger `--wait` (e.g.
`--wait 2500`) so the screenshot catches the relaxed graph, or call
`sim.tick()` in a loop and render statically.

### Dashboard grid (multiple panels)
```css
#root { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
.panel { min-height: 360px; }
.kpis { grid-column: 1 / -1; display: flex; gap: 24px; }
.kpi { font-size: 13px; color: var(--muted); }
.kpi b { display: block; font-size: 30px; color: var(--fg); }
```
Append a `.panel` div per chart, init one ECharts instance into each, and put
headline numbers in a full-width `.kpis` row on top. Render with a taller
viewport (`--height 1200 --full-page`) and check every panel is readable.
