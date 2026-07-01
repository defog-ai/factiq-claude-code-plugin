#!/usr/bin/env python3
"""Render a FactIQ ChartSpec as an ANSI/ASCII terminal preview.

This is a local-only companion to share_chart: feed it the same ChartSpec object
you would publish, and it prints a compact terminal rendering. The renderer is
stdlib-only and intentionally conservative: v1 handles bars, sparklines, simple
line charts, and falls back to a table for anything else.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import sys
from datetime import datetime
from typing import Any


ASCII_LEVELS = ".:-=+*#%@"
BLOCK_LEVELS = "▁▂▃▄▅▆▇█"
ANSI_COLORS = [31, 34, 32, 35, 36, 33, 90]


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


def ellipsize(text: object, width: int) -> str:
    value = str(text)
    if width <= 0:
        return ""
    if len(value) <= width:
        return value
    if width <= 3:
        return value[:width]
    return value[: width - 3] + "..."


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


def header(spec: dict[str, Any], width: int) -> list[str]:
    title = str(spec.get("title") or "FactIQ chart")
    return [ellipsize(title, width), ""]


def choose_type(spec: dict[str, Any], rows: list[dict[str, Any]], series: list[dict[str, Any]]) -> str:
    ctype = str(spec.get("type") or "").lower()
    if ctype == "bar":
        return "bar"
    if ctype == "line":
        if len(series) <= 2 and len(rows) >= 3:
            return "line"
        return "sparkline"
    if ctype in {"area", "stacked_area"}:
        return "sparkline"
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
    lines = header(spec, width)
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
        lines.append(
            f"{pad(ellipsize(label, max_label), max_label)} "
            f"{pad(bar, bar_width + (1 if val < 0 else 0))} "
            f"{pad(fmt_num(val), val_width, 'right')}"
        )
    return "\n".join(lines)


def level_char(value: float | None, low: float, high: float, charset: str) -> str:
    levels = ASCII_LEVELS if charset == "ascii" else BLOCK_LEVELS
    if value is None:
        return " "
    if high == low:
        return levels[-1]
    pos = (value - low) / (high - low)
    idx = max(0, min(len(levels) - 1, round(pos * (len(levels) - 1))))
    return levels[idx]


def render_sparkline(
    spec: dict[str, Any],
    rows: list[dict[str, Any]],
    x_key: str,
    series: list[dict[str, Any]],
    width: int,
    colors: bool,
    charset: str,
) -> str:
    lines = header(spec, width)
    label_width = min(22, max(8, max(len(str(s.get("label") or s["key"])) for s in series)))
    spark_width = max(10, width - label_width - 24)

    for si, s in enumerate(series):
        vals = [number(row.get(s["key"])) for row in rows]
        numeric = [v for v in vals if v is not None]
        if not numeric:
            continue
        low, high = min(numeric), max(numeric)
        if len(vals) > spark_width:
            bucketed: list[float | None] = []
            for i in range(spark_width):
                start = math.floor(i * len(vals) / spark_width)
                end = math.floor((i + 1) * len(vals) / spark_width)
                sample = [v for v in vals[start : max(end, start + 1)] if v is not None]
                bucketed.append(sum(sample) / len(sample) if sample else None)
            vals = bucketed
        spark = "".join(level_char(v, low, high, charset) for v in vals)
        latest = next((v for v in reversed(vals) if v is not None), None)
        label = str(s.get("label") or s["key"])
        lines.append(
            f"{pad(ellipsize(label, label_width), label_width)} "
            f"{paint(spark, si, colors)} "
            f"{pad(fmt_num(low), 9, 'right')}..{pad(fmt_num(high), 9, 'right')}"
            f" last {fmt_num(latest)}"
        )

    if rows:
        lines.append("")
        lines.append(f"{parse_dateish(rows[0].get(x_key, ''))} -> {parse_dateish(rows[-1].get(x_key, ''))}")
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
    lines = header(spec, width)
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
    points = ".o" if charset == "ascii" else "•◆"

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
        lines.append(f"{' ' * 12}{ellipsize(axis, plot_width)}")
    legend_parts = []
    legend_budget = max(8, width // max(1, len(series)) - 2)
    for i, s in enumerate(series):
        symbol = "." if charset == "ascii" else "•"
        label = ellipsize(str(s.get("label") or s["key"]), legend_budget - 2)
        legend_parts.append(paint(f"{symbol} {label}", i, colors))
    lines.append("  ".join(legend_parts))
    return "\n".join(lines)


def render_table(
    spec: dict[str, Any],
    rows: list[dict[str, Any]],
    x_key: str,
    series: list[dict[str, Any]],
    width: int,
) -> str:
    lines = header(spec, width)
    keys = [x_key] + [str(s["key"]) for s in series]
    labels = [x_key] + [str(s.get("label") or s["key"]) for s in series]
    col_count = len(keys)
    gap = 2 * (col_count - 1)
    col_width = max(6, (width - gap) // col_count)
    widths = [col_width] * col_count
    lines.append("  ".join(pad(ellipsize(label, widths[i]), widths[i]) for i, label in enumerate(labels)))
    lines.append("  ".join("-" * w for w in widths))
    for row in rows[: min(len(rows), 12)]:
        cells = []
        for i, key in enumerate(keys):
            val = row.get(key)
            num = number(val)
            text = fmt_num(num) if num is not None and key != x_key else parse_dateish(val)
            cells.append(pad(ellipsize(text, widths[i]), widths[i]))
        lines.append("  ".join(cells))
    if len(rows) > 12:
        lines.append(f"... {len(rows) - 12} more rows")
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
    if selected == "sparkline":
        return render_sparkline(spec, rows, x_key, series, width_int, colors, charset)
    if selected == "line":
        if len(series) > 2:
            return render_sparkline(spec, rows, x_key, series, width_int, colors, charset)
        return render_line(spec, rows, x_key, series, width_int, args.height, colors, charset)
    if selected == "table":
        return render_table(spec, rows, x_key, series, width_int)
    fail(f"Unsupported --type {selected!r}.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="term_chart.py",
        description="Render a FactIQ ChartSpec as a terminal chart.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("render", help="Print an ANSI/ASCII terminal chart")
    p.add_argument("--spec", required=True, help="ChartSpec JSON file, or '-' for stdin")
    p.add_argument(
        "--type",
        choices=["auto", "bar", "sparkline", "line", "table"],
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
