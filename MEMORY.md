# MEMORY.md - Long-Term Memory Summary

_Note: Canonical memory is stored in Postgres (Supabase). This file is a local summary only._

## Core Facts
- **Human**: Austin King
- **Setup**: OpenClaw running on Amazon EC2 (Linux).
- **Primary Agent**: `main` (current session).
- **Agents Configured**: `main` (active), `builder` (planned), `maintainer` (planned).
- **Communication**: Primary channel is Telegram.

## System Configuration
- **Memory Source of Truth**: External Postgres (Supabase) (`public.thoughts`, `public.memories`).
- **Git Remote**: `https://github.com/tvaloki/openclaw-backup.git` (Use SSH/PAT).
- **Branch Naming**: Local `master` vs Remote `main`.
- **Model Preferences**: Google Gemini (Primary), OpenAI Codex (Fallback). OpenRouter is currently unavailable.

## Known Issues & Resolutions
- **NotebookLM YouTube Ingest**: Solved AWS IP block by routing URLs directly to the NotebookLM library (bypassing local yt-dlp/fetch).
- **Auth Cache**: If model auth fails after config update, restart the gateway (`openclaw gateway restart`) to clear cached `auth_permanent` flags.
- **Telegram Group Traffic**: Empty `groupAllowFrom` with `groupPolicy: allowlist` drops all group messages. Populate to fix.
- **OpenRouter Key**: Current key `sk-or-v1-2ffd...` is invalid (401).
- **Skill Keys**: `goplaces` API key in `openclaw.json` works for `smart-route`. `tessie` skill is installed but requires a manual API key.

## Local Sourcing
- **Nashville News**: Use `curl -s https://www.wkrn.com/news/local-news/feed/ | grep -o "<title>.*</title>" | sed 's/<title>//;s/<\/title>//'` for direct local headlines.

---
_Last updated: 2026-03-26 02:50 UTC_
