#!/usr/bin/env python3
"""FactIQ bespoke-viz builder — assemble data into a self-contained HTML file
and render it headless so you can see (and fix) your own visualization.

This is the local-output counterpart to factiq.py's share-chart/share-report:
it never talks to the FactIQ API. You author an HTML file (any technique —
ECharts, D3, Canvas, SVG, WebGL), this script injects the data you already
fetched to disk, then screenshots the result so the render → look → fix loop
can run without pulling thousands of data rows back into your context.

Two subcommands:

  assemble  — inject on-disk JSON into an HTML template at the data marker,
              producing one portable, self-contained .html. Stdlib only.
  render    — open an HTML file in headless Chromium, write a PNG, and report
              any JS/console errors and failed requests. Needs Playwright;
              installs the package and Chromium on first run.

Data contract: the template must contain the marker token __FACTIQ_DATA__
inside a JSON script tag (see assets/viz-shell.html). After assembly the page
exposes a global `DATA` object keyed by the names you passed to --data; each
value is the full factiq payload, so result rows live at DATA.<key>.results.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import webbrowser

DATA_MARKER = "__FACTIQ_DATA__"


def fail(message: str, code: int = 1) -> None:
    print(json.dumps({"error": message}), file=sys.stderr)
    sys.exit(code)


def _row_count(value: object) -> int | None:
    """Best-effort count of data rows for the assemble stub.

    factiq.py --out files are payload objects with the rows under "results";
    a bare list counts directly. Anything else has no meaningful row count.
    """
    if isinstance(value, dict) and isinstance(value.get("results"), list):
        return len(value["results"])
    if isinstance(value, list):
        return len(value)
    return None


# ---------------------------------------------------------------------------
# save — lift a tool result out of the harness transcript onto disk
#
# The FactIQ MCP tools already return the full JSON payload into the model's
# context. Re-emitting that same payload through a Write call to feed `assemble`
# pays for every byte a second time (as output tokens) and risks a silent
# transcription slip in a numeric literal. Instead, read the payload straight
# from the on-disk transcript the harness already keeps and let the shell copy
# the bytes — the model never retypes the data. Works for Claude Code and Codex.
# ---------------------------------------------------------------------------

CLAUDE_PROJECTS = os.path.expanduser("~/.claude/projects")
CODEX_SESSIONS = os.path.expanduser("~/.codex/sessions")


def _newest(paths: list[str]) -> str | None:
    files = [p for p in paths if os.path.isfile(p)]
    return max(files, key=os.path.getmtime) if files else None


def _claude_transcript_for_cwd() -> str | None:
    # Claude Code stores each session at ~/.claude/projects/<slug>/<uuid>.jsonl,
    # where <slug> is the working directory with every "/" turned into "-".
    slug = os.getcwd().replace("/", "-")
    here = _newest(glob.glob(os.path.join(CLAUDE_PROJECTS, slug, "*.jsonl")))
    if here:
        return here
    # Subagents/commands may run from a different cwd; fall back to the globally
    # newest Claude transcript (the live session is the one being written).
    return _newest(glob.glob(os.path.join(CLAUDE_PROJECTS, "*", "*.jsonl")))


def _codex_transcript() -> str | None:
    return _newest(
        glob.glob(os.path.join(CODEX_SESSIONS, "**", "*.jsonl"), recursive=True)
    )


def _find_transcript() -> str | None:
    """Locate the live harness transcript — whichever of Claude Code / Codex was
    written most recently, since that is the session running right now."""
    cands = [p for p in (_claude_transcript_for_cwd(), _codex_transcript()) if p]
    return max(cands, key=os.path.getmtime) if cands else None


def _sniff_kind(path: str) -> str:
    if os.sep + ".codex" + os.sep in path:
        return "codex"
    if os.sep + ".claude" + os.sep in path:
        return "claude"
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                if isinstance(obj.get("payload"), dict):
                    return "codex"
                if isinstance(obj.get("message"), dict):
                    return "claude"
    except (OSError, json.JSONDecodeError):
        pass
    return "claude"


def _result_text(content: object) -> str:
    """Flatten a tool_result / MCP content value to its text payload."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [
            b.get("text", "")
            for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        ]
        return "".join(parts)
    return ""


def _dumps_input(inp: object) -> str:
    if isinstance(inp, str):
        return inp
    try:
        return json.dumps(inp, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(inp)


def _make_record(tool: str, input_str: str, text: str) -> dict:
    parsed: object | None = None
    if text:
        try:
            parsed = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            parsed = None
    # Some clients store an MCP result as its raw envelope
    # {"content": [{"type": "text", "text": "<json>"}]}; unwrap it to the actual
    # payload so the saved file is the tool's data, not the transport wrapper.
    if (
        isinstance(parsed, dict)
        and "content" in parsed
        and "results" not in parsed
        and "columns" not in parsed
    ):
        inner = _result_text(parsed.get("content"))
        if inner:
            try:
                parsed = json.loads(inner)
                text = inner
            except (json.JSONDecodeError, TypeError):
                pass
    rows = _row_count(parsed) if parsed is not None else None
    return {"tool": tool, "input": input_str, "json": parsed, "rows": rows}


def _parse_claude(path: str) -> list[dict]:
    names: dict[str, tuple[str, str]] = {}
    results: list[tuple[str, str]] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            msg = obj.get("message")
            content = msg.get("content") if isinstance(msg, dict) else None
            if not isinstance(content, list):
                continue
            for b in content:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "tool_use":
                    names[b.get("id")] = (
                        b.get("name", ""),
                        _dumps_input(b.get("input")),
                    )
                elif b.get("type") == "tool_result":
                    results.append(
                        (b.get("tool_use_id"), _result_text(b.get("content")))
                    )
    out = []
    for tuid, text in results:
        name, inp = names.get(tuid, ("", ""))
        out.append(_make_record(name, inp, text))
    return out


def _parse_codex(path: str) -> list[dict]:
    names: dict[str, tuple[str, str]] = {}
    results: list[tuple[str, str]] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            p = obj.get("payload") if isinstance(obj.get("payload"), dict) else obj
            pt = p.get("type")
            if pt == "function_call":
                names[p.get("call_id")] = (p.get("name", ""), p.get("arguments", "") or "")
            elif pt == "function_call_output":
                out = p.get("output")
                text = out if isinstance(out, str) else _result_text(out)
                results.append((p.get("call_id"), text))
    recs = []
    for cid, text in results:
        name, inp = names.get(cid, ("", ""))
        recs.append(_make_record(name, inp, text))
    return recs


def _tool_matches(name: str, wanted: str) -> bool:
    if not name:
        return False
    if name == wanted or name.split("__")[-1] == wanted:
        return True
    return wanted in name


def cmd_save(args: argparse.Namespace) -> None:
    path = args.transcript or _find_transcript()
    if not path:
        fail(
            "Could not locate a harness transcript. Pass --transcript PATH, or "
            "fall back to writing the payload with the Write tool."
        )
    if not os.path.isfile(path):
        fail(f"No such transcript: {path}")

    recs = _parse_codex(path) if _sniff_kind(path) == "codex" else _parse_claude(path)

    sel = recs
    if args.tool:
        sel = [r for r in sel if _tool_matches(r["tool"], args.tool)]
    if args.match:
        m = args.match.lower()
        sel = [
            r
            for r in sel
            if m in (r["input"] or "").lower() or m in (r["tool"] or "").lower()
        ]

    if args.list or not args.out:
        listing = [
            {
                "index": i,
                "neg_index": i - len(sel),
                "tool": r["tool"] or None,
                "rows": r["rows"],
                "json": r["json"] is not None,
                "input_preview": (r["input"] or "")[:120],
            }
            for i, r in enumerate(sel)
        ]
        print(json.dumps({"transcript": path, "results": listing}, indent=2))
        if not args.out and not args.list:
            fail("Nothing saved: pass --out FILE to save one of the results above.")
        return

    if not sel:
        fail(
            "No tool result matched. Re-run with --list (optionally --tool "
            "run_sql) to see what the transcript holds."
        )
    try:
        rec = sel[args.index]
    except IndexError:
        fail(f"--index {args.index} is out of range; {len(sel)} result(s) matched.")
    if rec["json"] is None:
        fail(
            "The matched result is not JSON, so it can't be saved as viz data. "
            "Use --list to pick another (narrow with --tool/--match)."
        )

    out = os.path.abspath(args.out)
    parent = os.path.dirname(out)
    if parent:
        os.makedirs(parent, exist_ok=True)
    try:
        with open(out, "w") as f:
            json.dump(rec["json"], f)
    except OSError as exc:
        fail(f"Cannot write {out}: {exc}")

    stub = {
        "out": out,
        "tool": rec["tool"] or None,
        "input_preview": (rec["input"] or "")[:120],
    }
    if rec["rows"] is not None:
        stub["rows"] = rec["rows"]
    print(json.dumps(stub, indent=2))


def _escape_for_html(text: str) -> str:
    """Make a JSON string safe to embed inside an HTML <script> element.

    JSON.parse decodes these escapes back to the original characters, so the
    data is unchanged — this only prevents a literal </script> (or a U+2028 /
    U+2029 line separator) in the data from breaking out of the script tag or
    the surrounding JS.
    """
    # JSON.parse decodes these \\uXXXX escapes, so the data is unchanged.
    return text.translate(
        {
            0x3C: "\\u003c",  # <
            0x3E: "\\u003e",  # >
            0x26: "\\u0026",  # &
            0x2028: "\\u2028",  # line separator
            0x2029: "\\u2029",  # paragraph separator
        }
    )


def cmd_assemble(args: argparse.Namespace) -> None:
    try:
        with open(args.template) as f:
            html = f.read()
    except OSError as exc:
        fail(f"Cannot read template {args.template}: {exc}")

    if DATA_MARKER not in html:
        fail(
            f"Template {args.template} has no {DATA_MARKER} marker. Author the "
            "HTML on assets/viz-shell.html (or add a JSON script tag containing "
            f"{DATA_MARKER}) so the data has somewhere to land."
        )

    data: dict = {}
    counts: dict = {}
    # --data is action="append" over nargs="+", so args.data is a list of
    # lists: both `--data a=x b=y` (one flag, many pairs) and `--data a=x
    # --data b=y` (repeated flag) end up here. Flatten so neither form
    # silently drops pairs.
    pairs = [pair for group in (args.data or []) for pair in group]
    for pair in pairs:
        if "=" not in pair:
            fail(f"--data expects key=path, got {pair!r}")
        key, path = pair.split("=", 1)
        key = key.strip()
        if not key:
            fail(f"--data entry {pair!r} has an empty key")
        if key in data:
            fail(f"--data key {key!r} given twice")
        try:
            with open(path) as f:
                value = json.load(f)
        except OSError as exc:
            fail(f"Cannot read data file {path}: {exc}")
        except json.JSONDecodeError as exc:
            fail(f"Data file {path} is not valid JSON: {exc}")
        data[key] = value
        rc = _row_count(value)
        if rc is not None:
            counts[key] = rc

    payload = _escape_for_html(json.dumps(data))
    html = html.replace(DATA_MARKER, payload)

    out = os.path.abspath(args.out)
    try:
        with open(out, "w") as f:
            f.write(html)
    except OSError as exc:
        fail(f"Cannot write {out}: {exc}")

    stub = {"out": out, "bytes": len(html.encode()), "keys": list(data.keys())}
    if counts:
        stub["rows"] = counts
    print(json.dumps(stub, indent=2))

    if args.open:
        webbrowser.open(f"file://{out}")


VENV_DIR = os.path.expanduser("~/.factiq/viz-venv")


def _venv_python(venv_dir: str) -> str:
    if os.name == "nt":
        return os.path.join(venv_dir, "Scripts", "python.exe")
    return os.path.join(venv_dir, "bin", "python")


def _venv_has_playwright(venv_py: str) -> bool:
    return (
        subprocess.run(
            [venv_py, "-c", "import playwright.sync_api"],
            capture_output=True,
        ).returncode
        == 0
    )


def _ensure_render_env():
    """Return sync_playwright, or re-exec this script under a dedicated venv.

    The interpreter that launched us may be externally managed (Homebrew, uv,
    distro python) where `pip install` is refused. Rather than touch it, we
    keep a private venv at ~/.factiq/viz-venv, install Playwright there, and
    re-exec the same command under that venv's python. Chromium itself is
    installed lazily by the launch fallback in cmd_render, now running under
    the venv.
    """
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401

        return sync_playwright
    except ImportError:
        pass

    if os.environ.get("FACTIQ_VIZ_REEXEC"):
        fail("Playwright is unavailable even after venv setup.", 6)

    venv_py = _venv_python(VENV_DIR)
    # Prefer uv when present: the interpreter that launched us is often a
    # uv-managed build with no ensurepip, so stdlib `venv --with-pip` aborts.
    # uv creates the venv and installs into it without needing pip bootstrapped.
    uv = shutil.which("uv")
    if not os.path.exists(venv_py):
        print(
            "Creating a Playwright virtualenv (first run, one time)…",
            file=sys.stderr,
            flush=True,
        )
        try:
            if uv:
                subprocess.run([uv, "venv", VENV_DIR], check=True)
            else:
                import venv

                venv.EnvBuilder(with_pip=True).create(VENV_DIR)
        except (subprocess.CalledProcessError, OSError) as exc:
            fail(
                f"Failed to create a virtualenv at {VENV_DIR}: {exc}. Install uv "
                "(https://docs.astral.sh/uv/) or a python that bundles pip.",
                6,
            )
    if not _venv_has_playwright(venv_py):
        print(
            "Installing Playwright into the virtualenv (first run, one time)…",
            file=sys.stderr,
            flush=True,
        )
        cmd = (
            [uv, "pip", "install", "--python", venv_py, "--quiet", "playwright"]
            if uv
            else [venv_py, "-m", "pip", "install", "--quiet", "playwright"]
        )
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as exc:
            fail(f"Failed to install the playwright package into {VENV_DIR}: {exc}", 6)

    env = dict(os.environ, FACTIQ_VIZ_REEXEC="1")
    os.execve(venv_py, [venv_py, os.path.abspath(__file__), *sys.argv[1:]], env)


def _install_chromium() -> None:
    print(
        "Installing Chromium for Playwright (first run, one time)…",
        file=sys.stderr,
        flush=True,
    )
    try:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"], check=True
        )
    except subprocess.CalledProcessError as exc:
        fail(f"Failed to install Chromium: {exc}", 6)


def cmd_render(args: argparse.Namespace) -> None:
    html_path = os.path.abspath(args.html)
    if not os.path.exists(html_path):
        fail(f"No such HTML file: {html_path}")
    out = os.path.abspath(args.out) if args.out else os.path.splitext(html_path)[0] + ".png"

    sync_playwright = _ensure_render_env()

    errors: list[str] = []
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as exc:  # missing browser binary on first run
            msg = str(exc).lower()
            if "install" in msg or "executable doesn't exist" in msg:
                _install_chromium()
                browser = p.chromium.launch()
            else:
                raise
        try:
            page = browser.new_page(
                viewport={"width": args.width, "height": args.height},
                device_scale_factor=args.scale,
            )
            # A console.error, an uncaught exception, or a failed asset load
            # (e.g. a CDN library that didn't reach the page) all leave a
            # broken or blank visualization — collect each so a silent failure
            # surfaces instead of producing an innocent-looking screenshot.
            page.on(
                "console",
                lambda m: errors.append(f"console.{m.type}: {m.text}")
                if m.type == "error"
                else None,
            )
            page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
            page.on(
                "requestfailed",
                lambda r: errors.append(
                    f"requestfailed: {r.url} ({r.failure})"
                ),
            )
            page.goto(f"file://{html_path}", wait_until="load")
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                # Some pages (animations, polling) never go idle — not fatal.
                pass
            if args.wait:
                page.wait_for_timeout(args.wait)
            target = page.locator(args.selector) if args.selector else page
            target.screenshot(path=out, **({} if args.selector else {"full_page": args.full_page}))
        finally:
            browser.close()

    stub = {"out": out, "width": args.width, "height": args.height}
    print(json.dumps(stub, indent=2))
    if errors:
        print(
            "\nWARNING: the page reported "
            f"{len(errors)} error(s) — the screenshot may be broken or blank:",
            file=sys.stderr,
        )
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        sys.exit(5)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="build_viz.py", description="Assemble and render bespoke local visualizations"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser(
        "assemble",
        help="Inject on-disk JSON into an HTML template; write a self-contained file",
    )
    p.add_argument("--template", required=True, help="HTML you authored (with the data marker)")
    p.add_argument(
        "--data",
        nargs="+",
        action="append",
        metavar="KEY=PATH",
        help="One or more key=path pairs; each file's JSON lands at DATA.<key>. "
        "Pass several after one flag (--data a=x b=y) or repeat the flag "
        "(--data a=x --data b=y); both work.",
    )
    p.add_argument("--out", required=True, help="Output HTML path")
    p.add_argument("--open", action="store_true", help="Open the result in the browser")
    p.set_defaults(func=cmd_assemble)

    p = sub.add_parser(
        "save",
        help="Copy a tool result's raw JSON from the harness transcript to a "
        "file — no retyping (feeds assemble --data)",
    )
    p.add_argument(
        "--out",
        help="Where to write the extracted JSON. Omit (or pass --list) to just "
        "list the available results without saving.",
    )
    p.add_argument(
        "--tool",
        help="Only match results from this tool, e.g. run_sql / get_series / "
        "get_market_data (matches the MCP tool-name suffix).",
    )
    p.add_argument(
        "--match",
        help="Only match results whose tool input contains this substring "
        "(case-insensitive) — e.g. a schema name or a distinctive bit of your "
        "SQL. Lets you pin the exact call without reading its output back.",
    )
    p.add_argument(
        "--index",
        type=int,
        default=-1,
        help="Which of the matching results to save (default -1, the most "
        "recent). Use --list to see indices.",
    )
    p.add_argument(
        "--list",
        action="store_true",
        help="List the matching results (tool, row count, input preview) "
        "instead of saving.",
    )
    p.add_argument(
        "--transcript",
        help="Transcript file to read (default: auto-detect the live Claude "
        "Code / Codex session).",
    )
    p.set_defaults(func=cmd_save)

    p = sub.add_parser(
        "render",
        help="Screenshot an HTML file headless and report JS/console errors",
    )
    p.add_argument("html", help="Path to the HTML file to render")
    p.add_argument("--out", help="PNG output path (default: alongside the HTML)")
    p.add_argument("--width", type=int, default=1280, help="Viewport width (default 1280)")
    p.add_argument("--height", type=int, default=900, help="Viewport height (default 900)")
    p.add_argument("--scale", type=float, default=2.0, help="Device scale factor (default 2)")
    p.add_argument("--full-page", action="store_true", help="Capture the full scrollable page")
    p.add_argument("--selector", help="Screenshot only the element matching this CSS selector")
    p.add_argument(
        "--wait",
        type=int,
        default=600,
        help="Extra wait in ms after load for late renders/animations (default 600)",
    )
    p.set_defaults(func=cmd_render)

    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
