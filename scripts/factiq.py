#!/usr/bin/env python3
"""FactIQ tools client — a self-contained HTTP CLI for the FactIQ /tools API.

Stdlib only (Python 3.10+). No codebase access required: every subcommand
talks to the FactIQ backend over HTTP and prints JSON to stdout.

Config lives at ~/.factiq/config.json. Resolution order for the API base URL:
--base-url flag > FACTIQ_API_URL env > config > https://api.worlddb.ai.
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


def http_json(
    method: str,
    url: str,
    body: dict | None = None,
    token: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    timeout_hint: str | None = None,
    _redirects: int = 0,
) -> tuple[int, dict]:
    """One HTTP round-trip. Returns (status, parsed JSON body)."""
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
                timeout_hint,
                _redirects + 1,
            )
        try:
            payload = json.loads(exc.read().decode() or "{}")
        except json.JSONDecodeError:
            payload = {"detail": str(exc)}
        return exc.code, payload
    except urllib.error.URLError as exc:
        fail(f"Cannot reach {url}: {exc.reason}")
    except TimeoutError:
        message = f"Request to {url} timed out after {timeout}s"
        if timeout_hint:
            message += f". {timeout_hint}"
        fail(message)


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
        status, payload = http_json(method, url, body, api_key, timeout, timeout_hint)
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


def emit(payload: dict, args: argparse.Namespace) -> None:
    """Print payload to stdout, or write it to --out and print a stub.

    The --out pattern keeps large result sets out of the orchestrator's
    context: full data goes to disk, stdout carries only the shape.

    Tool-level failures (SQL errors, statement timeouts) arrive as HTTP 200
    with an `error` body. Surface them like any other failure — stderr and a
    non-zero exit — and never write them to --out, where a poisoned file
    crashes downstream parsing long after the failed call.
    """
    if isinstance(payload, dict) and payload.get("error"):
        print(json.dumps(payload, indent=2, default=str), file=sys.stderr)
        sys.exit(4)

    out = getattr(args, "out", None)
    if out:
        with open(out, "w") as f:
            json.dump(payload, f, indent=2)
        stub = {"out": out}
        for key in ("columns", "row_count", "total_row_count", "title", "schema_name"):
            if key in payload:
                stub[key] = payload[key]
        rows = payload.get("results")
        if isinstance(rows, list) and "row_count" not in stub:
            stub["row_count"] = len(rows)
        print(json.dumps(stub, indent=2))
    else:
        print(json.dumps(payload, indent=2, default=str))


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------


def cmd_set_key(args: argparse.Namespace) -> None:
    """Store an API key generated at factiq.com/settings/security."""
    config = load_config()
    api = base_url(args, config)
    api_key = args.key or getpass.getpass("API key: ")
    if not api_key.startswith("fiq_"):
        fail("That does not look like a FactIQ API key (expected fiq_ prefix).")

    status, payload = http_json("GET", api + "/auth/me", token=api_key)
    if status == 401:
        fail("The server rejected this API key (HTTP 401).")
    if status >= 400:
        fail(f"Verification failed (HTTP {status}): {payload.get('detail', payload)}")

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
    print(
        json.dumps(
            {
                "key_saved": True,
                "email": user.get("email"),
                "plan": user.get("plan_type"),
                "api": api,
            }
        )
    )


def cmd_whoami(args: argparse.Namespace) -> None:
    emit(api_request(args, "GET", "/auth/me"), args)


def cmd_context(args: argparse.Namespace) -> None:
    emit(
        api_request(
            args,
            "GET",
            "/tools/context",
            params={"schemas": args.schemas},
            timeout_hint=(
                "Retry with --schemas to narrow the response "
                "(e.g. --schemas bls,bea,census); the full schema list is "
                "included either way."
            ),
        ),
        args,
    )


def cmd_search(args: argparse.Namespace) -> None:
    if len(args.schema) != len(args.terms):
        fail("Provide one --terms per --schema (repeat the pair per schema).")
    queries = [
        {"schema": schema, "terms": [t.strip() for t in terms.split(",") if t.strip()]}
        for schema, terms in zip(args.schema, args.terms)
    ]
    body = {
        "queries": queries,
        "limit": args.limit,
        "include_compound": not args.no_compound,
    }
    emit(api_request(args, "POST", "/tools/search", body), args)


def cmd_sql(args: argparse.Namespace) -> None:
    query = args.query
    if args.query_file:
        with open(args.query_file) as f:
            query = f.read()
    if not query:
        fail("Provide --query or --query-file.")
    body = {
        "question": args.question or "",
        "sql": query,
        "schema": args.schema,
        "exploration": args.explore,
        "auto_retry": args.auto_retry,
        "sample": not args.full,
        "max_rows": args.max_rows,
    }
    emit(api_request(args, "POST", "/tools/sql", body), args)


def cmd_series(args: argparse.Namespace) -> None:
    series_id = urllib.parse.quote(args.series_id, safe="")
    emit(
        api_request(
            args,
            "GET",
            f"/tools/series/{args.schema}/{series_id}",
            params={
                "from_year": args.from_year,
                "to_year": args.to_year,
                "sample": str(not args.full).lower(),
            },
        ),
        args,
    )


def cmd_market(args: argparse.Namespace) -> None:
    body = {
        "function": args.function,
        "symbol": args.symbol,
        "interval": args.interval,
        "outputsize": args.outputsize,
        "sample": not args.full,
    }
    emit(api_request(args, "POST", "/tools/market", body), args)


def cmd_earnings(args: argparse.Namespace) -> None:
    body = {
        "query": args.query,
        "search_target": args.target,
        "company_filter": args.companies.split(",") if args.companies else None,
        "quarter_filter": args.quarter,
        "limit": args.limit,
    }
    emit(api_request(args, "POST", "/tools/earnings", body), args)


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
    if args.question:
        body["question"] = args.question
    body.setdefault("source", "factiq-skill")

    config = load_config()
    target = web_url(args, config) + "/api/share-chart"
    status, response = http_json(
        "POST", target, body, timeout=getattr(args, "timeout", DEFAULT_TIMEOUT)
    )
    if status >= 400 or not response.get("shareUrl"):
        fail(f"share-chart failed (HTTP {status}): {response}")
    print(json.dumps(response, indent=2))


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
        prog="factiq.py", description="FactIQ tools API client", parents=[shared]
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
        "context", help="Dataset catalog + table structure", parents=[shared]
    )
    p.add_argument("--schemas", help="Comma-separated schema filter, e.g. bls,bea")
    p.add_argument("--out", help="Write full JSON to file, print a stub")
    p.set_defaults(func=cmd_context)

    p = sub.add_parser(
        "search", help="Series catalog search by title terms", parents=[shared]
    )
    p.add_argument(
        "--schema", action="append", required=True, help="Schema (repeatable)"
    )
    p.add_argument(
        "--terms",
        action="append",
        required=True,
        help="Comma-separated terms for the preceding --schema (repeatable)",
    )
    p.add_argument("--limit", type=int, default=15)
    p.add_argument("--no-compound", action="store_true")
    p.add_argument("--out")
    p.set_defaults(func=cmd_search)

    p = sub.add_parser(
        "sql", help="Run read-only SQL against a schema", parents=[shared]
    )
    p.add_argument("--schema", required=True)
    p.add_argument("--query", help="SQL text")
    p.add_argument("--query-file", help="Read SQL from a file")
    p.add_argument("--question", help="The question motivating the query")
    p.add_argument("--explore", action="store_true", help="Data exploration query")
    p.add_argument(
        "--auto-retry",
        action="store_true",
        help="Opt into the server-side LLM reviser on zero rows",
    )
    p.add_argument(
        "--full", action="store_true", help="Full rows instead of sampled preview"
    )
    p.add_argument("--max-rows", type=int, default=500)
    p.add_argument("--out")
    p.set_defaults(func=cmd_sql)

    p = sub.add_parser(
        "series", help="Fetch one series (incl. COMPOUND::)", parents=[shared]
    )
    p.add_argument("schema")
    p.add_argument("series_id")
    p.add_argument("--from-year", type=int)
    p.add_argument("--to-year", type=int)
    p.add_argument("--full", action="store_true")
    p.add_argument("--out")
    p.set_defaults(func=cmd_series)

    p = sub.add_parser(
        "market",
        help="Market data (quotes, fundamentals, commodities)",
        parents=[shared],
    )
    p.add_argument("function", help="e.g. GLOBAL_QUOTE, TIME_SERIES_DAILY, WTI")
    p.add_argument("--symbol")
    p.add_argument("--interval")
    p.add_argument("--outputsize", default="compact")
    p.add_argument("--full", action="store_true")
    p.add_argument("--out")
    p.set_defaults(func=cmd_market)

    p = sub.add_parser(
        "earnings", help="Search earnings call intelligence", parents=[shared]
    )
    p.add_argument("query")
    p.add_argument(
        "--target",
        default="all",
        choices=["all", "sections", "themes", "qa_exchanges"],
    )
    p.add_argument("--companies", help="Comma-separated tickers")
    p.add_argument("--quarter", help="e.g. 2025Q4")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--out")
    p.set_defaults(func=cmd_earnings)

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
