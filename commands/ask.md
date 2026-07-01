---
description: Answer a data question with FactIQ — a quick chart, terminal chart, or full report
argument-hint: "<question, e.g. How has US unemployment changed since 2019?>"
disable-model-invocation: true
allowed-tools: >
  mcp__plugin_factiq_factiq__*,
  mcp__factiq__*,
  mcp__claude_ai_FactIQ__*,
  Bash(python3:*), Bash(python:*), Read, Write, AskUserQuestion, Agent
---

Answer this question with real data from FactIQ:

> $ARGUMENTS

Read `${CLAUDE_PLUGIN_ROOT}/skills/factiq/SKILL.md` first. If no question was
provided above, ask the user what they want to know.

Everything — discovery, fetching, and publishing — runs through the FactIQ MCP
tools. If they aren't available or return an auth error, the MCP isn't
connected — tell the user to authorize it (Claude Code: `/mcp` → factiq;
Codex: `codex mcp login factiq`), then retry.

**Pick the output mode before doing any data work:**

- **Quick chart** — one focused shared chart, terminal preview, and short
  narrative. Right when the question names a single metric, series, or
  comparison: "How has X changed?", "X vs Y", "What is the current Z?".
- **Terminal chart** — an ANSI/ASCII preview without a share link. Use only
  when the user asks for terminal-only, ASCII-only, or local text output.
- **Detailed report** — a multi-section shareable report (summary, 2–5
  sections of narrative + charts, methodology notes) plus terminal previews of
  the report charts. Right when the question is broad or analytical: "the state
  of the US labor market", "what's driving inflation", "deep dive", or the user
  says report / analysis / comprehensive.

If the question clearly fits one mode, proceed without asking. Only when it
is genuinely ambiguous — broad enough that a report would add value, but a
single chart could plausibly satisfy it — use the AskUserQuestion tool to
offer the two modes, noting that the report takes noticeably longer and uses
more of their tokens and FactIQ tool quota.

Then follow the skill's orchestration workflow (catalog → discover → fetch →
compute, all via the MCP tools) and finish per the mode:

- **Quick chart** → build a ChartSpec (`references/chart-spec.md`), save it to
  JSON, publish with the `share_chart` tool, run
  `python3 scripts/term_chart.py render --spec <file> --charset ascii --color auto`,
  and return the share URL, terminal preview, and a short narrative of what the
  data shows.
- **Terminal chart** → build a ChartSpec (`references/chart-spec.md`), save it
  to JSON, run `python3 scripts/term_chart.py render --spec <file> --charset ascii --color auto`,
  and return the rendered output plus a short narrative without publishing.
- **Detailed report** → follow the skill's **Detailed reports** section and
  `references/report-spec.md`, save the report object to JSON, publish with the
  `share_report` tool, run
  `python3 scripts/term_chart.py report --report <file> --charset ascii --color auto`,
  and return the share URL, terminal previews, and the report's key findings.

For report-mode questions that span multiple topics, companies, or data sources,
decompose the research into parallel subagents after initial discovery — one
agent per research thread. Then synthesize and hand off to a report-assembler
subagent. See the skill's **Subagent orchestration** section for the pattern.
