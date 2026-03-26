---
summary: "Plan and progress tracker for a safe YouTube agent stack (metadata, comments, transcripts)"
owner: "austin"
status: "in_progress"
last_updated: "2026-03-22"
title: "YouTube Agent Setup"
---

# YouTube Agent Setup

## Objective

Build a safe, maintainable YouTube agent workflow that can:
1. Pull video/channel metadata
2. Pull comments
3. Pull transcripts (with safe fallback behavior)
4. Store/query results for downstream agent use

## Current status

In progress.

Already done:
- Evaluated ClawHub YouTube skills
- Rejected `youtube-transcript` skill for safety on main host (network/VPN manipulation + flagged suspicious)
- Chosen direction: official API-first + safe local tooling fallback

## Architecture decision

- Primary source: YouTube Data API v3 (official)
- Transcript path: official captions when available, fallback local extraction (no routing/network mutation)
- Orchestration: simple script-first (expand to n8n/cron if needed)
- Storage: pgmemory/Postgres-backed workflow

## Safety constraints

- No scripts that auto-change host networking (no `wg-quick`, no `ip rule` mutation)
- No hidden proxying in skill code
- Explicit rate limiting and retry/backoff
- Keep secrets in env/user service config only

## Milestones

- [ ] M1: Baseline project scaffold (`scripts/`, `data/`, `docs/`)
- [ ] M2: Metadata fetch script (single video + channel)
- [ ] M3: Comments fetch script with pagination + limits
- [ ] M4: Transcript fetch script with clean fallback handling
- [ ] M5: Unified runner + output normalization
- [ ] M6: Persist to pgmemory-friendly schema
- [ ] M7: Scheduled job / heartbeat integration

## Open questions

- Which transcript fallback is acceptable if captions unavailable?
- Preferred output target (JSON files only vs DB insert by default)?
- Scope for sentiment/topic analysis in v1?

## Next actions

1. Create implementation scaffold under this feature directory
2. Add minimal config template (`.env.example`)
3. Build M2 metadata fetcher first
