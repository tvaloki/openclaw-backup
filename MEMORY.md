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
