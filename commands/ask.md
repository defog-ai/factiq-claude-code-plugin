---
description: Answer a data question with FactIQ — a quick chart or a full report
argument-hint: "<question, e.g. How has US unemployment changed since 2019?>"
disable-model-invocation: true
allowed-tools: Bash(python3:*), Bash(python:*), Read, Write, AskUserQuestion
---

Answer this question with real data from FactIQ:

> $ARGUMENTS

Read `${CLAUDE_PLUGIN_ROOT}/SKILL.md` first. If no question was provided
above, ask the user what they want to know.

**Pick the output mode before doing any data work:**

- **Quick chart** — one focused chart plus a short narrative. Right when the
  question names a single metric, series, or comparison: "How has X
  changed?", "X vs Y", "What is the current Z?".
- **Detailed report** — a multi-section shareable report (summary, 2–5
  sections of narrative + charts, methodology notes). Right when the
  question is broad or analytical: "the state of the US labor market",
  "what's driving inflation", "deep dive", or the user says report /
  analysis / comprehensive.

If the question clearly fits one mode, proceed without asking. Only when it
is genuinely ambiguous — broad enough that a report would add value, but a
single chart could plausibly satisfy it — use the AskUserQuestion tool to
offer the two modes, noting that the report takes noticeably longer and uses
more of their tokens and FactIQ tool quota.

Then follow SKILL.md's orchestration workflow (context → discover → fetch →
compute) and finish per the mode:

- **Quick chart** → build a ChartSpec (`references/chart-spec.md`), publish
  with `share-chart`, and return the share URL plus a short narrative of
  what the data shows.
- **Detailed report** → follow SKILL.md's **Detailed reports** section and
  `references/report-spec.md`, publish with `share-report`, and return the
  share URL plus the report's key findings.
