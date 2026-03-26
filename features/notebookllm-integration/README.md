# NotebookLLM Integration

**Purpose:** Provide an opt-in integration for routing targeted YouTube transcripts from daily digests into NotebookLLM via Telegram deep links.

## Core Flow
1. **Email Modification:** Update `youtube-agent-setup` digest script to include a Telegram Deep Link under each video (e.g., `tg://resolve?domain=YOUR_BOT_USERNAME&text=/notebook_upload%20<VIDEO_ID>`).
2. **Command Handler:** A new agent command or skill listening for `/notebook_upload <VIDEO_ID>` in Telegram.
3. **Extraction Engine:** On trigger, the agent uses the `youtube-transcript-yt-dlp` skill to fetch the full transcript.
4. **NotebookLLM Push:** The agent formats the transcript and pushes it to NotebookLLM (authentication/API method TBD).

## Open Questions & Next Steps
- [ ] Determine the NotebookLLM ingest method (API, headless browser, or third-party proxy).
- [ ] Determine the exact Telegram bot username to construct the deep links.
- [ ] Draft the new Telegram command handler.