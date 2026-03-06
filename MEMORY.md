# MEMORY.md

## Stable Preferences
- User has a scheduled "ULTRA-COMPACT Nashville Brief" format preference: 3 bullets only (Tesla status, route ETA to Downtown Nashville, local Nashville/Middle TN news) plus a final "✅ Quick Focus" line.
- Briefs should be tightly constrained and concise.

## Current Operational Follow-up
- Required local commands for that brief (`tessie`, `smart-route`, `daily-news-digest`) were unavailable in this runtime on 2026-03-03; restoring/installing them is needed for live briefs.
- Missing `tessie`, `smart-route`, `daily-news-digest` commands impede brief generation; need to install/restore them. This is a priority follow-up.

## Model Routing Playbook (Cost-Minimizing)
- User is in OpenClaw build phase and wants low spend while maintaining quality.
- Default routing policy:
  - Use FREE model (`NVIDIA_FREE`) for routine work: summaries, drafts, formatting, status checks, cron reports, first-pass ideation.
  - Use Codex (`openai-codex/gpt-5.3-codex`) only for high-leverage tasks: debugging failing systems, architecture decisions, production scripts, security-sensitive actions, and final pre-ship review.
- Enforce 2-step pattern by default:
  1) First pass on FREE model.
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
