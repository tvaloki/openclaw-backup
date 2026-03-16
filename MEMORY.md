# MEMORY.md

## Stable Preferences
- User has a scheduled "ULTRA-COMPACT Nashville Brief" format preference: 2 bullets only (route ETA to Downtown Nashville, local Nashville/Middle TN news) plus a final "✅ Quick Focus" line.
- Briefs should be tightly constrained and concise.

## Current Operational Follow-up
- **GitHub Backup Sync:** The nightly GitHub sync cron job is successfully committing changes locally, but failing the `git push` step. Needs a remote GitHub repository and authentication (SSH or PAT) configured to complete the off-site backup loop.
- (Resolved) `smart-route` and `daily-news-digest` commands are fully restored and the Morning Brief routing is operational. The Nashville Morning Brief has been handed off to the Builder agent for formatting. (Tessie uninstalled and removed from brief).

## Model Routing Playbook (Cost-Minimizing)
- User is in OpenClaw build phase and wants low spend while maintaining quality.
- Default routing policy:
  - Use a fast, cheap, reliable paid model (e.g., `google/gemini-flash-latest`) for routine work: summaries, drafts, formatting, status checks, cron reports, first-pass ideation. (Note: Previously used `NVIDIA_FREE`, but it suffers from severe API rate-limit drops resulting in missed replies).
  - Use Codex (`openai-codex/gpt-5.3-codex` or `gpt-5.4`) only for high-leverage tasks: debugging failing systems, architecture decisions, production scripts, security-sensitive actions, and final pre-ship review.
- Enforce 2-step pattern by default:
  1) First pass on Flash/fast model.
  2) Escalate to Codex only if risk/complexity or quality threshold requires it.
- Assistant should proactively recommend model choice at task start when relevant.

## Recent Plan Review (2026-03-06)
- Adopted declarative, version‑controlled connection‑profile store and pure‑Python pre‑flight validator for Supabase PSQL connections.
- Critical flaws identified: fragile URI parsing, incomplete port whitelist, static service‑string mapping, incomplete IPv4 reachability check, optional SSL fingerprint verification, insufficient dry‑run validation, missing lock_timeout, stale golden‑profile risk, etc.
- Missing assumptions: static network topology, single‑process execution, immutable CSV schema, always‑available env vars, PostgreSQL version compatibility, observability pipeline readiness, lock‑contention tolerance, backup sufficiency.
- Better alternative: fully declarative migration pipeline with Python validator, SAVEPOINT‑based transaction, rolling update, fallback tunnel for IPv6‑only networks.
- Acceptance conditions: profile file exists and is version‑controlled, validator executable returns 0, dry‑run bulk‑copy succeeds (row count, 1536‑element vectors, non‑null source_id), IPv4 resolution succeeds and host reachable within timeout, SSL fingerprint validation passes and matches stored SHA‑256, metrics emitted and consumable by observability pipeline, outstanding follow‑ups: implement validator, write and test validator, verify dry‑run passes.
- Outstanding follow‑ups: implement profile store and validator, write and test validator, verify dry‑run passes, integrate into CI pipeline.

## Core Directive: Doug (OpenBrain/pgmemory) First
- **Always check Doug for context.** When asked a question, tackling a problem, or dealing with operational/personal data, proactively search `public.thoughts` (via pgmemory/SQL) for past conversations, decisions, or context *before* starting from scratch or saying data is unavailable. The user has 2+ years of ChatGPT history stored there.

## Agent Collaboration & Delegation Rules
- **Honest Handoff Rule (Main):** The Main agent must only claim delegation ("Handed to...", "Routed to...") if it successfully performs a `sessions_spawn` to another agent. If no delegation occurs, use:
  - `Status: Recommendation only`
  - `Next Action: Send this to [Builder|Maintainer]`
  - Standardized response format: Status, Issue Summary, Decision, Why, Next Action.

## Infrastructure & Architecture Notes
- **EC2 Gateway Daemon:** OpenClaw runs as a system-level service (`openclaw-gateway.service`) on this host. The user-scoped service (`systemctl --user`) is intentionally disabled. Cron jobs and self-healing scripts must use `sudo systemctl restart openclaw-gateway.service`.
- **Google Maps API Readiness:** `smart-route` command is fully restored and the Nashville Morning Brief routing is operational. Requires `GOOGLE_ROUTES_API_KEY` to be active and the Google Routes API enabled in the Google Cloud Console.
