# One-Shot Delegation Test (Main -> Maintainer)

Use this as a single user message to validate delegation routing behavior.

## Test Prompt (send exactly)

```text
Run a delegation routing test now.

Task: Have Maintainer perform diagnostics-only work: verify whether file `/tmp/openclaw-delegation-test.txt` exists and report result.

Requirements:
- You (Main) must delegate to Maintainer using explicit agentId.
- Do not delegate to main.
- After successful delegation, respond only with:
  Status
  Issue Summary
  Decision
  Why
  Handoff (must include delegated agentId and runId if available)
- Do not include implementation or diagnostic details in Main response.
- If delegation fails, report exact failure reason.
```

## Expected Main response shape

- `Status: Routed to Maintainer`
- `Issue Summary: ...`
- `Decision: Maintainer`
- `Why: ... diagnostics ...`
- `Handoff: Delegated to agentId: maintainer (runId: ...)`

No extra lines after `Handoff`.

## Expected Maintainer follow-up

A separate Maintainer result should appear with the diagnostic outcome (`exists` / `not found`).

## Fail conditions

Any of these means fail:
- Main spawns `agentId: main`
- Main says "Recommendation only" without attempted spawn error
- Main includes specialist findings/details in its own handoff reply
- Main emits a second specialist-style deliverable after Maintainer output arrives
- Main omits delegated `agentId` from Handoff

## Evidence capture

If it fails, save:
1. Main handoff message
2. Maintainer message (or wrong-agent message)
3. Any `Subagent ... finished/failed` system line

Then run:

```bash
python3 /home/ec2-user/.openclaw/workspaces/builder/scripts/classify_duplicate_layer.py msg_a.txt msg_b.txt
```
