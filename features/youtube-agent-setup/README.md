# YouTube Agent Setup (Feature Workspace)

This directory tracks implementation for a safe YouTube agent pipeline.

## Structure

- `PLAN.md` — roadmap and architecture decisions
- `PROGRESS.md` — dated progress log
- `scripts/` — fetchers and runner scripts
- `data/` — local output artifacts (gitignored later if needed)
- `docs/` — design and API notes
- `tests/` — test cases for parsing/fetch logic
- `.env.example` — configuration template

## Initial build order

1. `scripts/fetch_video_meta.py`
2. `scripts/fetch_comments.py`
3. `scripts/fetch_transcript.py`
4. `scripts/run_pipeline.py`
