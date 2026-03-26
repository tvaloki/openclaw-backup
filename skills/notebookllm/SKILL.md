---
name: notebookllm
description: "Push YouTube videos and other sources to NotebookLM. Triggered by /notebook_upload or /start notebook_upload_<id>."
user-invocable: true
---

# NotebookLLM Skill

This skill pushes content into NotebookLM using the `notebooklm` Python library.

## Commands

- `/notebook_upload <source>` — Upload a URL, file, or text to the default Knowledge Base notebook.
- `/start notebook_upload_<video_id>` — Special handler for Telegram deep links (e.g. from digests).
- `/research <topic>` — Automatically search the web, fetch the top 3-5 pages, save them locally, and push them to the Research Notebook.

## IDs

- **Knowledge Base (Default)**: `5af9a497-5958-4149-9de4-9bd47d7eff16`
- **Research / Deep Dives**: `e8014f98-4fe2-400c-a663-b1be9169753a`

## Instructions

- If you receive a message like `/start notebook_upload_<video_id>`, it means the user clicked a "Send to NotebookLLM" link.
  - **Action**: Immediately call the `notebook_upload` tool with the video URL `https://www.youtube.com/watch?v=<video_id>`. Use the Knowledge Base ID.
  - **Confirmation**: Tell the user you've pushed the video to NotebookLM.

- If you receive `/research <topic>`:
  1. Use your `web_search` tool to find 3-5 high-quality, relevant results for the topic.
  2. Use your `web_fetch` tool to extract the markdown text for those top results.
  3. Write the markdown to temporary files in `/tmp` (e.g., `/tmp/research_topic_1.md`).
  4. Call the `notebook_upload` tool (below) for each file, using the **Research / Deep Dives** Notebook ID (`e8014f98-4fe2-400c-a663-b1be9169753a`).
  5. Tell the user exactly what articles/sources you pushed to their Research notebook.

## Tools

### notebook_upload
Upload a source to a NotebookLM notebook.

**Usage:**
```bash
/home/ec2-user/.openclaw/workspace/features/notebookllm-integration/.venv/bin/python3 \
  /home/ec2-user/.openclaw/workspace/features/notebookllm-integration/scripts/notebookllm.py \
  "<notebook_id>" "<source>"
```

**Parameters:**
- `notebook_id`: The ID of the target notebook.
- `source`: The URL, local file path, or raw text to upload.
