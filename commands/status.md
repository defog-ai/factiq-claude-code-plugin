---
description: Check FactIQ auth, plan, and connection status
disable-model-invocation: true
allowed-tools: Bash(python3:*), Bash(python:*)
---

## Current FactIQ publishing-key status

!`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/factiq.py" whoami 2>&1`

## Your task

This checks the `fiq_` **publishing** key (used by `share-chart` /
`share-report`). The **data** tools authenticate separately, through the FactIQ
MCP server's OAuth connection — its status is shown by Claude Code's own
**`/mcp`** command, not here.

Summarize the publishing-key status above for the user in one or two sentences:

- If it shows a user object: report the email, plan, and monthly usage
  (`monthly_usage.request_count` of `request_limit`), and confirm publishing is
  ready. Add: data tools require the MCP to be connected — run `/mcp` and pick
  **factiq** if it isn't.
- If it shows an auth error (no key / invalid key): tell the user to get
  their API key at https://factiq.com/settings/security and run
  `/factiq:set-key`, then stop.
- If it shows a connection error: report which API base URL failed and
  suggest checking `FACTIQ_API_URL` / `~/.factiq/config.json`.
