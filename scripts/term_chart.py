#!/usr/bin/env python3
"""Render FactIQ charts as ANSI/ASCII terminal previews.

This is a local-only companion to share_chart: feed it the same ChartSpec object
you would publish, or a share_report report object, and it prints compact
terminal renderings. The renderer is stdlib-only and intentionally conservative:
v1 handles bars, simple line charts, and falls back to a table for anything
else.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import sys
import textwrap
from datetime import datetime
from typing import Any


ANSI_COLORS = [31, 34, 32, 35, 36, 33, 90]
ANSI_BOLD = 1
ANSI_DIM = 2


def fail(message: str, code: int = 1) -> None:
    print(json.dumps({"error": message}), file=sys.stderr)
    sys.exit(code)


def visible_len(text: str) -> int:
    # We only emit ANSI SGR sequences, so this small stripper is enough.
    out = 0
    i = 0
    while i < len(text):
        if text[i : i + 2] == "\033[":
            j = text.find("m", i + 2)
            if j == -1:
                break
            i = j + 1
        else:
            out += 1
            i += 1
    return out


def wrap_cell(text: object, width: int) -> list[str]:
    # Wrap text to `width` columns, breaking long words so nothing is ever
    # truncated — long content overflows onto continuation lines instead.
    value = str(text)
    if width <= 0:
        return [value]
    lines = textwrap.wrap(
        value,
        width=width,
        break_long_words=True,
        break_on_hyphens=False,
    )
    return lines or [""]


def pack_line(parts: list[str], sep: str, width: int) -> list[str]:
    # Greedily pack styled parts into lines no wider than `width` (measured by
    # visible length). A single part longer than `width` gets its own line and
    # is allowed to overflow rather than be truncated.
    out: list[str] = []
    current = ""
    for part in parts:
        if not current:
            current = part
            continue
        if visible_len(current) + len(sep) + visible_len(part) <= width:
            current += sep + part
        else:
            out.append(current)
            current = part
    if current:
        out.append(current)
    return out or [""]


def combine_columns(col_lines: list[list[str]], widths: list[int], sep: str = "  ") -> list[str]:
    # Stack pre-styled, per-column line lists into aligned rows. Cells that wrap
    # to more lines than their neighbours leave the shorter columns blank.
    height = max((len(c) for c in col_lines), default=0)
    out: list[str] = []
    for r in range(height):
        cells = []
        for i, lines_ in enumerate(col_lines):
            cell = lines_[r] if r < len(lines_) else ""
            cells.append(pad(cell, widths[i]))
        out.append(sep.join(cells))
    return out


def pad(text: str, width: int, align: str = "left") -> str:
    used = visible_len(text)
    if used >= width:
        return text
    spaces = " " * (width - used)
    return spaces + text if align == "right" else text + spaces


def number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(result):
        return None
    return result


def fmt_num(value: float | None) -> str:
    if value is None:
        return "n/a"
    av = abs(value)
    if av >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    if av >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if av >= 10_000:
        return f"{value:,.0f}"
    if av >= 100:
        return f"{value:,.1f}"
    if av >= 10:
        return f"{value:.2f}"
    if av >= 1:
        return f"{value:.3f}"
    if value == 0:
        return "0"
    return f"{value:.3g}"


def parse_dateish(value: object) -> str:
    text = str(value)
    if len(text) >= 10:
        try:
            dt = datetime.fromisoformat(text[:10])
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    return text


def color_enabled(mode: str) -> bool:
    if mode == "always":
        return True
    if mode == "never":
        return False
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    return sys.stdout.isatty()


def paint(text: str, index: int, enabled: bool) -> str:
    if not enabled:
        return text
    code = ANSI_COLORS[index % len(ANSI_COLORS)]
    return f"\033[{code}m{text}\033[0m"


def style(text: str, enabled: bool, *codes: int) -> str:
    if not enabled or not codes:
        return text
    joined = ";".join(str(code) for code in codes)
    return f"\033[{joined}m{text}\033[0m"


def load_spec(path: str) -> dict[str, Any]:
    try:
        if path == "-":
            data = json.load(sys.stdin)
        else:
            with open(path) as f:
                data = json.load(f)
    except OSError as exc:
        fail(f"Cannot read {path}: {exc}")
    except json.JSONDecodeError as exc:
        fail(f"{path} is not valid JSON: {exc}")
    if not isinstance(data, dict):
        fail("ChartSpec must be a JSON object.")
    return data


def load_json_object(path: str, label: str) -> dict[str, Any]:
    try:
        if path == "-":
            data = json.load(sys.stdin)
        else:
            with open(path) as f:
                data = json.load(f)
    except OSError as exc:
        fail(f"Cannot read {path}: {exc}")
    except json.JSONDecodeError as exc:
        fail(f"{path} is not valid JSON: {exc}")
    if not isinstance(data, dict):
        fail(f"{label} must be a JSON object.")
    return data


def chart_data(spec: dict[str, Any]) -> tuple[list[dict[str, Any]], str, list[dict[str, Any]]]:
    rows = spec.get("data")
    if not isinstance(rows, list):
        fail("ChartSpec must contain a data array.")
    x_field = spec.get("xField") or {}
    x_key = x_field.get("key") if isinstance(x_field, dict) else None
    if not x_key:
        fail("ChartSpec must contain xField.key.")
    series = spec.get("series")
    if not isinstance(series, list) or not series:
        fail("ChartSpec must contain at least one series entry.")
    clean_series = [s for s in series if isinstance(s, dict) and s.get("key")]
    if not clean_series:
        fail("ChartSpec series entries must contain key.")
    clean_rows = [r for r in rows if isinstance(r, dict)]
    return clean_rows, str(x_key), clean_series


def header(spec: dict[str, Any], width: int, colors: bool) -> list[str]:
    title = str(spec.get("title") or "FactIQ chart")
    title_lines = textwrap.wrap(title, width=max(1, width)) or [""]
    return [*(style(line, colors, ANSI_BOLD) for line in title_lines), ""]


def choose_type(spec: dict[str, Any], rows: list[dict[str, Any]], series: list[dict[str, Any]]) -> str:
    ctype = str(spec.get("type") or "").lower()
    if ctype == "bar":
        return "bar"
    if ctype in {"line", "area", "stacked_area"}:
        if len(rows) >= 3:
            return "line"
        return "table"
    return "table"


def render_bar(
    spec: dict[str, Any],
    rows: list[dict[str, Any]],
    x_key: str,
    series: list[dict[str, Any]],
    width: int,
    colors: bool,
    charset: str,
) -> str:
    lines = header(spec, width, colors)
    entries: list[tuple[str, str, float, int]] = []
    for row in rows:
        label = parse_dateish(row.get(x_key, ""))
        for si, s in enumerate(series):
            val = number(row.get(s["key"]))
            if val is None:
                continue
            s_label = str(s.get("label") or s["key"])
            full_label = label if len(series) == 1 else f"{label} / {s_label}"
            entries.append((full_label, s_label, val, si))

    if not entries:
        return "\n".join(lines + ["No numeric values to render."])

    max_label = min(28, max(10, min(max(len(e[0]) for e in entries), width // 3)))
    val_width = min(12, max(7, max(len(fmt_num(e[2])) for e in entries)))
    bar_width = max(8, width - max_label - val_width - 4)
    max_abs = max(abs(e[2]) for e in entries) or 1.0
    char = "#" if charset == "ascii" else "█"

    for label, _s_label, val, si in entries:
        count = max(1, round(abs(val) / max_abs * bar_width)) if val else 0
        bar = char * count
        if val < 0:
            bar = "-" + bar
        bar = paint(bar, si, colors)
        label_lines = wrap_cell(label, max_label)
        for prefix in label_lines[:-1]:
            lines.append(pad(prefix, max_label))
        lines.append(
            f"{pad(label_lines[-1], max_label)} "
            f"{pad(bar, bar_width + (1 if val < 0 else 0))} "
            f"{pad(fmt_num(val), val_width, 'right')}"
        )
    return "\n".join(lines)


def render_line(
    spec: dict[str, Any],
    rows: list[dict[str, Any]],
    x_key: str,
    series: list[dict[str, Any]],
    width: int,
    height: int,
    colors: bool,
    charset: str,
) -> str:
    lines = header(spec, width, colors)
    plot_width = max(12, width - 13)
    plot_height = max(4, height)
    vals_by_series = [[number(row.get(s["key"])) for row in rows] for s in series]
    numeric = [v for vals in vals_by_series for v in vals if v is not None]
    if not numeric:
        return "\n".join(lines + ["No numeric values to render."])
    low, high = min(numeric), max(numeric)
    if high == low:
        high += 1
        low -= 1

    canvas: list[list[list[int]]] = [[[] for _ in range(plot_width)] for _ in range(plot_height)]
    points = "*o" if charset == "ascii" else "•◆"

    for si, vals in enumerate(vals_by_series):
        last: tuple[int, int] | None = None
        for i, val in enumerate(vals):
            if val is None:
                last = None
                continue
            x = round(i * (plot_width - 1) / max(1, len(rows) - 1))
            y = plot_height - 1 - round((val - low) / (high - low) * (plot_height - 1))
            canvas[y][x].append(si)
            if last is not None:
                lx, ly = last
                steps = max(abs(x - lx), abs(y - ly))
                for step in range(1, steps):
                    ix = round(lx + (x - lx) * step / steps)
                    iy = round(ly + (y - ly) * step / steps)
                    canvas[iy][ix].append(si)
            last = (x, y)

    for yi, row in enumerate(canvas):
        y_val = high - (high - low) * yi / max(1, plot_height - 1)
        rendered = []
        for cell in row:
            if not cell:
                rendered.append(" ")
            elif len(set(cell)) > 1:
                rendered.append(paint("*", 6, colors))
            else:
                si = cell[-1]
                rendered.append(paint(points[si % len(points)], si, colors))
        lines.append(f"{pad(fmt_num(y_val), 10, 'right')} |{''.join(rendered)}")
    lines.append(f"{' ' * 10} +{'-' * plot_width}")
    if rows:
        start = parse_dateish(rows[0].get(x_key, ""))
        end = parse_dateish(rows[-1].get(x_key, ""))
        axis = f"{start} -> {end}"
        for chunk in wrap_cell(axis, plot_width):
            lines.append(f"{' ' * 12}{chunk}")
    legend_parts = []
    for i, s in enumerate(series):
        symbol = points[i % len(points)]
        label = str(s.get("label") or s["key"])
        legend_parts.append(paint(f"{symbol} {label}", i, colors))
    lines.extend(pack_line(legend_parts, "  ", width))
    return "\n".join(lines)


def render_table(
    spec: dict[str, Any],
    rows: list[dict[str, Any]],
    x_key: str,
    series: list[dict[str, Any]],
    width: int,
    colors: bool,
) -> str:
    lines = header(spec, width, colors)
    keys = [x_key] + [str(s["key"]) for s in series]
    labels = [x_key] + [str(s.get("label") or s["key"]) for s in series]
    col_count = len(keys)
    gap = 2 * (col_count - 1)
    col_width = max(6, (width - gap) // col_count)
    widths = [col_width] * col_count
    header_cols = []
    for i, label in enumerate(labels):
        wrapped = wrap_cell(label, widths[i])
        styled = [
            style(w, colors, ANSI_DIM) if i == 0 else paint(w, i - 1, colors)
            for w in wrapped
        ]
        header_cols.append(styled)
    lines.extend(combine_columns(header_cols, widths))
    lines.append(style("  ".join("-" * w for w in widths), colors, ANSI_DIM))
    for row in rows[: min(len(rows), 12)]:
        cols = []
        for i, key in enumerate(keys):
            val = row.get(key)
            num = number(val)
            text = fmt_num(num) if num is not None and key != x_key else parse_dateish(val)
            wrapped = wrap_cell(text, widths[i])
            if i > 0 and num is not None:
                wrapped = [paint(w, i - 1, colors) for w in wrapped]
            cols.append(wrapped)
        lines.extend(combine_columns(cols, widths))
    if len(rows) > 12:
        lines.append(style(f"... {len(rows) - 12} more rows", colors, ANSI_DIM))
    return "\n".join(lines)


def render(spec: dict[str, Any], args: argparse.Namespace) -> str:
    width = args.width
    if width == "auto":
        width = str(shutil.get_terminal_size((80, 24)).columns)
    try:
        width_int = max(40, int(width))
    except ValueError:
        fail("--width must be an integer or 'auto'.")

    rows, x_key, series = chart_data(spec)
    selected = args.type if args.type != "auto" else choose_type(spec, rows, series)
    colors = color_enabled(args.color)
    charset = args.charset

    if selected == "bar":
        return render_bar(spec, rows, x_key, series, width_int, colors, charset)
    if selected == "line":
        return render_line(spec, rows, x_key, series, width_int, args.height, colors, charset)
    if selected == "table":
        return render_table(spec, rows, x_key, series, width_int, colors)
    fail(f"Unsupported --type {selected!r}.")


def normalize_report_rows(chart: dict[str, Any]) -> list[dict[str, Any]]:
    columns = chart.get("columns")
    data = chart.get("data")
    if not isinstance(columns, list) or not isinstance(data, list):
        return []
    col_names = [str(c) for c in columns]
    rows: list[dict[str, Any]] = []
    for row in data:
        if isinstance(row, dict):
            rows.append(row)
        elif isinstance(row, list):
            rows.append(
                {col_names[i]: row[i] if i < len(row) else None for i in range(len(col_names))}
            )
    return rows


def report_chart_to_spec(chart: dict[str, Any], fallback_title: str) -> dict[str, Any] | None:
    rows = normalize_report_rows(chart)
    if not rows:
        return None
    chart_type = str(chart.get("chart_type") or "table")
    columns = [str(c) for c in chart.get("columns", [])]
    x_column = chart.get("x_column") or (columns[0] if columns else None)
    y_columns = chart.get("y_columns")
    if not isinstance(y_columns, list) or not y_columns:
        y_columns = [c for c in columns if c != x_column]
    if not x_column or not y_columns:
        return None
    spec_type = "line" if chart_type == "line" else "bar" if chart_type == "bar" else "table"
    return {
        "title": chart.get("title") or fallback_title,
        "type": spec_type,
        "xField": {"key": str(x_column)},
        "series": [{"key": str(c), "label": str(c)} for c in y_columns],
        "data": rows,
    }


def report_object(value: dict[str, Any]) -> dict[str, Any]:
    # Accept either the raw report object or a wrapper such as
    # {"question": "...", "report": {...}} used as share_report arguments.
    report = value.get("report")
    if isinstance(report, dict):
        return report
    return value


def render_report(report_payload: dict[str, Any], args: argparse.Namespace) -> str:
    report = report_object(report_payload)
    sections = report.get("sections")
    if not isinstance(sections, list):
        fail("Report must contain a sections array, or be wrapped as {report: ...}.")

    outputs: list[str] = []
    chart_count = 0
    max_charts = args.max_charts
    colors = color_enabled(args.color)

    for section_index, section in enumerate(sections, start=1):
        if not isinstance(section, dict):
            continue
        charts = section.get("charts")
        if not isinstance(charts, list):
            continue
        heading = str(section.get("heading") or f"Section {section_index}")
        for chart_index, chart in enumerate(charts, start=1):
            if max_charts and chart_count >= max_charts:
                remaining = remaining_report_charts(sections, chart_count)
                outputs.append(f"... {remaining} more chart(s) not shown")
                return "\n\n".join(outputs)
            if not isinstance(chart, dict):
                continue
            spec = report_chart_to_spec(chart, f"{heading} chart {chart_index}")
            if spec is None:
                continue
            chart_count += 1
            prefix = f"{heading}"
            if len(charts) > 1:
                prefix = f"{heading} / chart {chart_index}"
            rendered = render(spec, args)
            rule = "-" * min(len(prefix), max(8, int_width(args.width)))
            outputs.append(
                f"{style(prefix, colors, ANSI_BOLD)}\n"
                f"{style(rule, colors, ANSI_DIM)}\n"
                f"{rendered}"
            )

    if not outputs:
        return "No report charts could be rendered as terminal previews."
    return "\n\n".join(outputs)


def remaining_report_charts(sections: list[Any], already_rendered: int) -> int:
    total = 0
    for section in sections:
        if isinstance(section, dict) and isinstance(section.get("charts"), list):
            total += len(section["charts"])
    return max(0, total - already_rendered)


def int_width(width: str) -> int:
    if width == "auto":
        return shutil.get_terminal_size((80, 24)).columns
    try:
        return int(width)
    except ValueError:
        return 80


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="term_chart.py",
        description="Render FactIQ ChartSpec/report JSON as terminal charts.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("render", help="Print an ANSI/ASCII terminal chart")
    p.add_argument("--spec", required=True, help="ChartSpec JSON file, or '-' for stdin")
    p.add_argument(
        "--type",
        choices=["auto", "bar", "line", "table"],
        default="auto",
        help="Terminal rendering type. auto maps from ChartSpec.type.",
    )
    p.add_argument(
        "--width",
        default="80",
        help="Output width in columns, or 'auto' to read the terminal size.",
    )
    p.add_argument("--height", type=int, default=12, help="Plot height for line charts")
    p.add_argument(
        "--color",
        choices=["auto", "always", "never"],
        default="auto",
        help="ANSI color mode. auto respects TTY, NO_COLOR, and TERM=dumb.",
    )
    p.add_argument(
        "--charset",
        choices=["ascii", "unicode-block"],
        default="ascii",
        help="Glyph set. ascii is safest; unicode-block is denser.",
    )
    p.add_argument("--out", help="Also write the rendered chart to this file")
    p.set_defaults(func=lambda args: print_or_write(render(load_spec(args.spec), args), args.out))

    p = sub.add_parser(
        "report",
        help="Print terminal previews for a share_report report object",
    )
    p.add_argument(
        "--report",
        required=True,
        help="Report JSON file, share_report args JSON, or '-' for stdin",
    )
    p.add_argument(
        "--type",
        choices=["auto", "bar", "line", "table"],
        default="auto",
        help="Terminal rendering type. auto maps from each report chart_type.",
    )
    p.add_argument(
        "--width",
        default="80",
        help="Output width in columns, or 'auto' to read the terminal size.",
    )
    p.add_argument("--height", type=int, default=12, help="Plot height for line charts")
    p.add_argument(
        "--color",
        choices=["auto", "always", "never"],
        default="auto",
        help="ANSI color mode. auto respects TTY, NO_COLOR, and TERM=dumb.",
    )
    p.add_argument(
        "--charset",
        choices=["ascii", "unicode-block"],
        default="ascii",
        help="Glyph set. ascii is safest; unicode-block is denser.",
    )
    p.add_argument(
        "--max-charts",
        type=int,
        default=4,
        help="Maximum report charts to render in the terminal preview (0 means all).",
    )
    p.add_argument("--out", help="Also write the rendered report preview to this file")
    p.set_defaults(
        func=lambda args: print_or_write(
            render_report(load_json_object(args.report, "Report"), args),
            args.out,
        )
    )
    return parser


def print_or_write(output: str, out: str | None) -> None:
    print(output)
    if out:
        path = os.path.abspath(out)
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        try:
            with open(path, "w") as f:
                f.write(output)
                f.write("\n")
        except OSError as exc:
            fail(f"Cannot write {path}: {exc}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
