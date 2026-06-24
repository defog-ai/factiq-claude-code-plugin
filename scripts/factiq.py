#!/usr/bin/env python3
"""FactIQ publishing client — auth + the publishing endpoints the MCP omits.

The read-only data tools (catalog, search, SQL, series, market, earnings) now
live on the FactIQ MCP server, which Claude Code talks to natively (see the
plugin's .mcp.json). This CLI is only what the read-only MCP deliberately does
NOT expose: storing/verifying the API key, and the two publishing endpoints —
`share-chart` (POST /shared-charts) and `share-report` (POST /tools/report).

Stdlib only (Python 3.10+). Every subcommand talks to the FactIQ backend over
HTTP and prints JSON to stdout.

Config lives at ~/.factiq/config.json. Resolution order for the API base URL:
--base-url flag > FACTIQ_API_URL env > config > https://api.worlddb.ai.
The config's base_url is written by set-key itself, so set-key treats it as
advisory: if it fails verification and was not explicitly requested, set-key
retries against the default URL and saves whichever one worked.
The web origin (for share-chart) resolves the same way via --web-url /
FACTIQ_WEB_URL / config / https://www.factiq.com.

Auth is API-key based: FACTIQ_API_KEY env > config api_key. Generate your key
at https://factiq.com/settings/security (shown only once) and store it with
`factiq.py set-key`.
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import stat
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_API_URL = "https://api.worlddb.ai"
# The apex domain 307-redirects /api/* to www; target www directly.
DEFAULT_WEB_URL = "https://www.factiq.com"
CONFIG_PATH = os.path.expanduser("~/.factiq/config.json")
DEFAULT_TIMEOUT = 120
MAX_REDIRECTS = 3
# The server enforces a fixed 1 req/s limit; transient 429s are retried
# with these sleeps before giving up (quota-exhausted 429s are not retried).
RATE_LIMIT_BACKOFF_SECONDS = (1.5, 3.0)


def load_config() -> dict:
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def save_config(config: dict) -> None:
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
    os.chmod(CONFIG_PATH, stat.S_IRUSR | stat.S_IWUSR)


def fail(message: str, code: int = 1) -> None:
    print(json.dumps({"error": message}), file=sys.stderr)
    sys.exit(code)


def base_url(args: argparse.Namespace, config: dict) -> str:
    url = (
        getattr(args, "base_url", None)
        or os.environ.get("FACTIQ_API_URL")
        or config.get("base_url")
        or DEFAULT_API_URL
    )
    return url.rstrip("/")


def web_url(args: argparse.Namespace, config: dict) -> str:
    url = (
        getattr(args, "web_url", None)
        or os.environ.get("FACTIQ_WEB_URL")
        or config.get("web_url")
        or DEFAULT_WEB_URL
    )
    return url.rstrip("/")


def base_url_overridden(args: argparse.Namespace) -> bool:
    """True when the API URL came from --base-url or FACTIQ_API_URL, not config."""
    return bool(getattr(args, "base_url", None) or os.environ.get("FACTIQ_API_URL"))


def http_json(
    method: str,
    url: str,
    body: dict | None = None,
    token: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    raise_network_errors: bool = False,
    _redirects: int = 0,
) -> tuple[int, dict]:
    """One HTTP round-trip. Returns (status, parsed JSON body).

    Network-level failures (unreachable host, timeout) exit with an error
    message by default; with raise_network_errors=True they propagate so the
    caller can retry elsewhere or enrich the message.
    """
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    # Cloudflare blocks urllib's default python-urllib/x.y user-agent outright.
    req.add_header("User-Agent", "factiq-cli/0.4 (+https://github.com/defog-ai/factiq-skill)")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as exc:
        # urllib refuses to redirect a request that carries a body, so POST
        # redirects (e.g. apex factiq.com -> www) surface here; re-issue at
        # the new location with the method and body intact.
        location = exc.headers.get("Location")
        if exc.code in (301, 302, 307, 308) and location and _redirects < MAX_REDIRECTS:
            return http_json(
                method,
                urllib.parse.urljoin(url, location),
                body,
                token,
                timeout,
                raise_network_errors,
                _redirects + 1,
            )
        try:
            payload = json.loads(exc.read().decode() or "{}")
        except json.JSONDecodeError:
            payload = {"detail": str(exc)}
        return exc.code, payload
    except urllib.error.URLError as exc:
        if raise_network_errors:
            raise
        fail(f"Cannot reach {url}: {exc.reason}")
    except TimeoutError:
        if raise_network_errors:
            raise
        fail(f"Request to {url} timed out after {timeout}s")


def resolve_api_key(config: dict) -> str | None:
    return os.environ.get("FACTIQ_API_KEY") or config.get("api_key")


def api_request(
    args: argparse.Namespace,
    method: str,
    path: str,
    body: dict | None = None,
    params: dict | None = None,
    timeout_hint: str | None = None,
) -> dict:
    """API-key-authenticated request (FACTIQ_API_KEY env > config api_key)."""
    config = load_config()
    api = base_url(args, config)
    api_key = resolve_api_key(config)
    if not api_key:
        fail(
            "No API key configured. Generate one at "
            "https://factiq.com/settings/security, then run: factiq.py set-key "
            "(or set FACTIQ_API_KEY)."
        )

    url = api + path
    if params:
        clean = {k: v for k, v in params.items() if v is not None}
        if clean:
            url += "?" + urllib.parse.urlencode(clean)

    timeout = getattr(args, "timeout", DEFAULT_TIMEOUT)
    for attempt in range(len(RATE_LIMIT_BACKOFF_SECONDS) + 1):
        try:
            status, payload = http_json(
                method, url, body, api_key, timeout, raise_network_errors=True
            )
        except urllib.error.URLError as exc:
            message = f"Cannot reach {url}: {exc.reason}"
            if api != DEFAULT_API_URL and not base_url_overridden(args):
                message += (
                    f". The base URL {api} was saved in {CONFIG_PATH} by a "
                    "previous set-key run — re-run factiq.py set-key (or pass "
                    "--base-url) if it is stale."
                )
            fail(message)
        except TimeoutError:
            message = f"Request to {url} timed out after {timeout}s"
            if timeout_hint:
                message += f". {timeout_hint}"
            fail(message)
        if status != 429:
            break
        detail = str(payload.get("detail", payload))
        # Quota exhaustion is also a 429 but won't clear in seconds.
        if "quota" in detail.lower() or attempt >= len(RATE_LIMIT_BACKOFF_SECONDS):
            break
        time.sleep(RATE_LIMIT_BACKOFF_SECONDS[attempt])

    if status == 401:
        fail(
            "Invalid API key (it may have been regenerated). Get the current "
            "key at https://factiq.com/settings/security and run: factiq.py set-key"
        )
    if status == 429:
        fail(f"Rate limited or quota exhausted: {payload.get('detail', payload)}", 3)
    if status >= 400:
        fail(f"HTTP {status}: {payload.get('detail', payload)}", 2)
    return payload


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------


def verify_key(api: str, api_key: str, timeout: int) -> tuple[dict, str | None]:
    """Probe {api}/auth/me with the key.

    Returns (payload, problem): problem is None on success, otherwise a short
    description that reads naturally after the API URL.
    """
    url = api + "/auth/me"
    try:
        status, payload = http_json(
            "GET", url, token=api_key, timeout=timeout, raise_network_errors=True
        )
    except urllib.error.URLError as exc:
        return {}, f"unreachable ({exc.reason})"
    except TimeoutError:
        return {}, f"no response within {timeout}s"
    if status == 401:
        return {}, "the key was rejected (HTTP 401)"
    if status >= 400:
        return {}, f"HTTP {status}: {payload.get('detail', payload)}"
    return payload, None


def cmd_set_key(args: argparse.Namespace) -> None:
    """Store an API key generated at factiq.com/settings/security.

    Verifies the key before saving. A base_url remembered in the config file
    (written by a previous set-key run, e.g. against a local dev server) can
    be stale; if it fails verification and was not explicitly requested via
    --base-url/FACTIQ_API_URL, the default API is tried next, and whichever
    URL verified the key is saved.
    """
    config = load_config()
    api = base_url(args, config)
    api_key = args.key or getpass.getpass("API key: ")
    if not api_key.startswith("fiq_"):
        fail("That does not look like a FactIQ API key (expected fiq_ prefix).")

    timeout = getattr(args, "timeout", DEFAULT_TIMEOUT)
    payload, problem = verify_key(api, api_key, timeout)
    note = None
    if problem and api != DEFAULT_API_URL and not base_url_overridden(args):
        fallback_payload, fallback_problem = verify_key(
            DEFAULT_API_URL, api_key, timeout
        )
        if fallback_problem:
            fail(
                f"Key verification failed — tried {api} (saved in {CONFIG_PATH}): "
                f"{problem}; then {DEFAULT_API_URL}: {fallback_problem}."
            )
        note = (
            f"The saved base URL {api} failed ({problem}); the key verified "
            f"against {DEFAULT_API_URL}, which is saved as the base URL now."
        )
        api, payload, problem = DEFAULT_API_URL, fallback_payload, None
    if problem:
        fail(f"Key verification against {api} failed — {problem}.")

    config.pop("access_token", None)
    config.pop("refresh_token", None)
    user = payload.get("user") or payload
    config.update(base_url=api, api_key=api_key)
    if user.get("email"):
        config["email"] = user["email"]
    web_override = getattr(args, "web_url", None)
    if web_override:
        config["web_url"] = web_override.rstrip("/")
    save_config(config)
    result = {
        "key_saved": True,
        "email": user.get("email"),
        "plan": user.get("plan_type"),
        "api": api,
    }
    if note:
        result["note"] = note
    print(json.dumps(result))


def cmd_whoami(args: argparse.Namespace) -> None:
    """Verify the stored publishing API key and show the account it belongs to.

    The MCP server has no whoami tool, and `/factiq:status` / `set-key` need a
    way to confirm the `fiq_` key that the publishing endpoints authenticate
    with; this hits the same `/auth/me` the key check has always used.
    """
    payload = api_request(args, "GET", "/auth/me")
    print(json.dumps(payload, indent=2, default=str))


# Quoted SQL literals that look like series ids (letters + digits, e.g.
# 'LNS14000000' or 'us_census_hs_M_10d_2846100010_5700') — used to spot
# lineage nodes whose series_refs list fewer series than the query touches.
SERIES_ID_LITERAL_RE = re.compile(r"'([A-Za-z0-9_]{6,})'")


def lint_lineage(lineage: object, where: str) -> None:
    """Warn about lineage that will render poorly on the share page.

    Warnings only — nothing here blocks publishing. The two defects the
    page cannot fix itself: code collapsed onto a single line (rendered
    verbatim in a code block) and series_refs listing one representative
    series instead of every series the step used.
    """
    nodes = lineage.get("nodes") if isinstance(lineage, dict) else None
    if not isinstance(nodes, list):
        return
    for node in nodes:
        if not isinstance(node, dict):
            continue
        label = f"{where} lineage node '{node.get('id', '?')}'"
        code = node.get("code")
        code = code.strip() if isinstance(code, str) else ""
        if len(code) > 80 and "\n" not in code:
            print(
                f"warning: {label} has its code collapsed onto one line — it "
                "renders verbatim in a code block, so embed real newlines "
                "(formatted SQL/Python)",
                file=sys.stderr,
            )
        if node.get("type") == "sql" and code:
            refs = node.get("series_refs") or []
            ids_in_code = {
                lit
                for lit in SERIES_ID_LITERAL_RE.findall(code)
                if any(c.isdigit() for c in lit) and any(c.isalpha() for c in lit)
            }
            if len(ids_in_code) > len(refs):
                print(
                    f"warning: {label} queries {len(ids_in_code)} series-like "
                    f"ids but series_refs lists only {len(refs)} — list every "
                    "series the query used (see the lineage rules in the "
                    "references)",
                    file=sys.stderr,
                )


def cmd_share_chart(args: argparse.Namespace) -> None:
    try:
        with open(args.spec) as f:
            payload = json.load(f)
    except OSError as exc:
        fail(f"Cannot read chart spec {args.spec}: {exc}")
    except json.JSONDecodeError as exc:
        fail(f"Chart spec {args.spec} is not valid JSON: {exc}")

    # Accept either a bare ChartSpec or a full {chart, chartData, ...} payload.
    body = payload if "chart" in payload else {"chart": payload}
    chart = body["chart"]
    missing = [
        field
        for field, ok in (
            ("type", bool(chart.get("type"))),
            ("xField", bool(chart.get("xField"))),
            ("series", isinstance(chart.get("series"), list)),
        )
        if not ok
    ]
    if missing:
        fail(f"Chart spec is missing required field(s): {', '.join(missing)}")
    if not chart.get("sources"):
        print(
            "warning: chart spec has no 'sources' — the shared page will show no "
            "Data Source citation (see references/chart-spec.md)",
            file=sys.stderr,
        )
    if not chart.get("lineage"):
        print(
            "warning: chart spec has no 'lineage' — the shared page will show no "
            "'How we built this' panel (see references/chart-spec.md)",
            file=sys.stderr,
        )
    else:
        lint_lineage(chart["lineage"], "chart spec")
    if args.question:
        body["question"] = args.question
    body.setdefault("source", "factiq-skill")

    # POST to the backend's editable, owner-tied store (DEF-1411/DEF-1412)
    # instead of the legacy unauthenticated Vercel Blob route. api_request adds
    # the API-key bearer token, so the chart is owned by the key's user and can
    # be edited + version-restored from the UI on /share-chart/<id>. The backend
    # sanitizes the payload (1200 rows / 40 cols / 400 chars) and enforces a
    # ~2MB cap; it returns {shareId} only, so we build shareUrl from the web
    # origin exactly as the frontend service does.
    response = api_request(args, "POST", "/shared-charts", body)
    share_id = response.get("shareId")
    if not share_id:
        fail(f"share-chart failed: no shareId in response: {response}")
    config = load_config()
    share_url = f"{web_url(args, config)}/share-chart/{share_id}"
    print(json.dumps({"shareId": share_id, "shareUrl": share_url}, indent=2))


REPORT_CHART_TYPES = {
    "line",
    "bar",
    "table",
    "bubble",
    "small_multiples",
    "stacked_area",
    "map",
    "heatmap",
}
REPORT_TABULAR_TYPES = {"line", "bar", "table"}


def cmd_share_report(args: argparse.Namespace) -> None:
    """Publish a multi-section report via POST /tools/report.

    Validation here is a fast local pre-flight only — the server re-validates
    everything against the real chart schemas and returns a 422 naming the
    failing field paths.
    """
    try:
        with open(args.report) as f:
            payload = json.load(f)
    except OSError as exc:
        fail(f"Cannot read report {args.report}: {exc}")
    except json.JSONDecodeError as exc:
        fail(f"Report {args.report} is not valid JSON: {exc}")

    # Accept either a bare report {summary, sections, ...} or a full
    # {question, report, model} request payload.
    body = payload if "report" in payload else {"report": payload}
    if args.question:
        body["question"] = args.question
    if args.model:
        body["model"] = args.model
    body.setdefault("model", "factiq-skill")
    if not str(body.get("question", "")).strip():
        fail("Provide --question (or a top-level 'question' in the report file).")

    report = body["report"]
    if not str(report.get("summary", "")).strip():
        fail("Report needs a non-empty 'summary'.")
    sections = report.get("sections")
    if not isinstance(sections, list) or not sections:
        fail("Report needs a non-empty 'sections' list.")

    chart_count = 0
    for i, section in enumerate(sections):
        if not str(section.get("heading", "")).strip():
            fail(f"sections[{i}] needs a 'heading'.")
        for j, chart in enumerate(section.get("charts") or []):
            chart_count += 1
            where = f"sections[{i}].charts[{j}]"
            if chart.get("chart_type") not in REPORT_CHART_TYPES:
                fail(f"{where}: chart_type must be one of {sorted(REPORT_CHART_TYPES)}")
            if not str(chart.get("title", "")).strip():
                fail(f"{where}: 'title' is required and should state the finding")
            if chart.get("chart_type") in REPORT_TABULAR_TYPES and not (
                chart.get("columns") and chart.get("data")
            ):
                fail(f"{where}: line/bar/table charts need 'columns' and 'data'")
            if not chart.get("sources"):
                print(
                    f"warning: {where} has no 'sources' — the report will show no "
                    "Data Source citation (see references/report-spec.md)",
                    file=sys.stderr,
                )
            if not chart.get("lineage"):
                print(
                    f"warning: {where} has no 'lineage' — its 'How we built this' "
                    "panel will be a generic stub (see references/report-spec.md)",
                    file=sys.stderr,
                )
            else:
                lint_lineage(chart["lineage"], where)
    if chart_count == 0:
        fail("Report needs at least one chart across its sections.")

    response = api_request(args, "POST", "/tools/report", body)
    # Compose the share URL from the CLI's own web origin so FACTIQ_WEB_URL /
    # --web-url overrides (e.g. localhost) carry through.
    config = load_config()
    share_path = response.get("share_path") or f"/share/{response.get('share_id')}"
    response["shareUrl"] = web_url(args, config) + share_path
    print(json.dumps(response, indent=2))


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    # Shared flags accepted both before and after the subcommand. SUPPRESS
    # keeps a subparser from clobbering a value parsed by the main parser;
    # all reads go through getattr with a default.
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument(
        "--base-url", default=argparse.SUPPRESS, help="API base URL override"
    )
    shared.add_argument(
        "--web-url",
        default=argparse.SUPPRESS,
        help="Web origin override (share-chart)",
    )
    shared.add_argument(
        "--timeout",
        type=int,
        default=argparse.SUPPRESS,
        help=f"HTTP timeout seconds (default {DEFAULT_TIMEOUT})",
    )

    parser = argparse.ArgumentParser(
        prog="factiq.py",
        description="FactIQ auth + publishing CLI (data tools live on the MCP "
        "server; see the plugin's .mcp.json)",
        parents=[shared],
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser(
        "set-key",
        help="Store your fiq_ API key (verifies it first)",
        parents=[shared],
    )
    p.add_argument("--key", help="The API key (prompted securely if omitted)")
    p.set_defaults(func=cmd_set_key)

    p = sub.add_parser("whoami", help="Show the authenticated user", parents=[shared])
    p.set_defaults(func=cmd_whoami)

    p = sub.add_parser(
        "share-chart", help="Publish a ChartSpec, get a share URL", parents=[shared]
    )
    p.add_argument("--spec", required=True, help="Path to chart spec JSON")
    p.add_argument("--question", help="Question shown with the shared chart")
    p.set_defaults(func=cmd_share_chart)

    p = sub.add_parser(
        "share-report",
        help="Publish a multi-section report, get a share URL",
        parents=[shared],
    )
    p.add_argument(
        "--report",
        required=True,
        help="Path to report JSON (see references/report-spec.md)",
    )
    p.add_argument(
        "--question", help="The question the report answers (overrides the file)"
    )
    p.add_argument("--model", help="Label for the model that authored the report")
    p.set_defaults(func=cmd_share_report)

    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
