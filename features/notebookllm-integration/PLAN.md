# PLAN: NotebookLLM Transcript Push

## Phase 1: Planning and Discovery
- [x] Investigate NotebookLLM API/upload capabilities.
- [x] Document required credentials or setup steps for the user.
- [x] Define the exact Telegram deep link format based on the active bot.

## Phase 2: Digest Modification
- [x] Modify `channel_daily_digest.py` in the `youtube-agent-setup` project to append a "Send to NotebookLLM" Telegram link to each video block.

## Phase 3: Command Implementation
- [ ] Create a new OpenClaw command (`/notebook_upload`) to catch the deep link text.
- [ ] Implement the logic: fetch full transcript -> push to NotebookLLM -> reply to user in Telegram with success/failure.

## Phase 4: Testing & Deployment
- [ ] Test the full loop end-to-end.
- [ ] Ensure the auth state with NotebookLLM remains stable.