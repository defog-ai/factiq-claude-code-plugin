---
description: Store your FactIQ API key for the factiq skill
argument-hint: "[fiq_... key — omit to be shown the secure paste option]"
disable-model-invocation: true
allowed-tools: Bash(python3:*), Bash(python:*)
---

Store the user's FactIQ API key so the factiq skill can **publish** charts and
reports (`share-chart` / `share-report`). Note for the user: the **data** tools
(catalog, SQL, series, market, earnings) authenticate separately through the
FactIQ MCP server — to connect those, run `/mcp`, pick **factiq**, and complete
the browser sign-in. This key is only needed when publishing.

Arguments: "$ARGUMENTS"

1. If the arguments above contain a `fiq_...` key, store and verify it in one
   step (the CLI calls the API to check the key before saving):

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/factiq.py" set-key --key "fiq_..."
   ```

   On success, report the verified email and plan, and remind the user they
   can clear this message from history if they prefer the key not sit in the
   transcript.

2. If no key was provided, do NOT ask the user to paste it into the chat.
   Instead tell them:
   - Get the key at https://factiq.com/settings/security (**API key** →
     Generate, or Regenerate if it was never copied — keys are shown only
     once).
   - Then run this in the prompt box for a secure, in-session prompt that
     keeps the key out of the conversation:

     ```
     ! python3 "<absolute path to this plugin>/scripts/factiq.py" set-key
     ```

     Substitute the real absolute path (`${CLAUDE_PLUGIN_ROOT}/scripts/factiq.py`)
     into the command you show them.
   - Alternatively they can re-run `/factiq:set-key fiq_...` with the key as
     an argument if they don't mind it appearing in the transcript.

3. After the key is stored, confirm auth works:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/factiq.py" whoami
   ```
