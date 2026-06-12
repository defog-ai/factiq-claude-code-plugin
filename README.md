# FactIQ Claude Code Plugin

A [Claude Code plugin](https://code.claude.com/docs/en/plugins) that lets
Claude answer economic and financial data questions using FactIQ's data tools
over HTTP — catalog search, read-only SQL, series lookup, market data,
earnings-call search, and shareable chart publishing. Claude orchestrates the
whole analysis itself; no codebase or database access is required, only a
FactIQ account.

## Install

Inside Claude Code:

```
/plugin marketplace add defog-ai/factiq-skill
/plugin install factiq@factiq
```

This adds the skill (Claude invokes it automatically for economic/financial
data questions) plus three slash commands:

| Command | Purpose |
|---|---|
| `/factiq:set-key` | Store your FactIQ API key (guides you through getting one) |
| `/factiq:status` | Check auth, plan, and monthly usage |
| `/factiq:ask <question>` | Run a full analysis and get a shareable chart |

<details>
<summary>Alternative: install as a plain skill (no slash commands)</summary>

```bash
git clone git@github.com:defog-ai/factiq-skill.git ~/.claude/skills/factiq
```

The skill auto-invokes the same way; store your key with
`python3 ~/.claude/skills/factiq/scripts/factiq.py set-key`.
</details>

## Get your API key

1. Sign in at [factiq.com](https://factiq.com) and open
   **[Settings → Security](https://factiq.com/settings/security)**.
2. In the **API key** section, click **Generate API key** (or **Regenerate**
   if one already exists — this revokes the old key).
3. Copy the `fiq_...` key immediately — it is shown only once and cannot be
   retrieved later (the server stores only a hash).

Then run `/factiq:set-key` in Claude Code and follow the instructions. The
key is verified against the API and cached in `~/.factiq/config.json`
(chmod 600) — never stored in this folder. Alternatively, set the
`FACTIQ_API_KEY` env var, which overrides the config.

## Contents

- `SKILL.md` — the skill definition Claude loads (setup, workflow, limits)
- `commands/` — the `/factiq:*` slash commands
- `scripts/factiq.py` — self-contained stdlib-only CLI for the FactIQ
  `/tools/*` API (Python 3.10+, no dependencies)
- `references/` — SQL idioms, ChartSpec format, and dataset schema overview
- `.claude-plugin/` — plugin + marketplace manifests

## Configuration

The CLI targets `https://api.worlddb.ai` (API) and `https://www.factiq.com`
(share links) by default. Override with `FACTIQ_API_URL` / `FACTIQ_WEB_URL`
env vars or `--base-url` / `--web-url` flags — e.g. `http://localhost:8000`
and `http://localhost:3000` for local development against the worlddb repos.

## Security

No secrets belong in this repo. Auth uses per-user API keys (`set-key`
prompts via getpass; `FACTIQ_API_KEY` env var also works); the key lives only
in `~/.factiq/config.json`. The backend stores keys hashed, and enforces a
1 request/second rate limit and a monthly tool-call quota per plan.
