#!/usr/bin/env python3
"""
Fetch YouTube comments via YouTube Data API v3.

Usage:
  python3 fetch_comments.py --video dQw4w9WgXcQ --pretty
  python3 fetch_comments.py --video "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --pages 3 --max-results 50

Env:
  YOUTUBE_API_KEY=...
"""

import argparse
import json
import os
import re
import sys
from urllib.parse import parse_qs, urlparse

import requests

API_BASE = "https://www.googleapis.com/youtube/v3"


def extract_video_id(video_input: str) -> str:
    video_input = video_input.strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", video_input):
        return video_input

    parsed = urlparse(video_input)
    if parsed.netloc in {"youtu.be", "www.youtu.be"}:
        candidate = parsed.path.lstrip("/").split("/")[0]
        if re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate):
            return candidate

    qs = parse_qs(parsed.query)
    if "v" in qs and qs["v"]:
        candidate = qs["v"][0]
        if re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate):
            return candidate

    parts = [p for p in parsed.path.split("/") if p]
    for idx, part in enumerate(parts):
        if part in {"embed", "shorts", "v"} and idx + 1 < len(parts):
            candidate = parts[idx + 1]
            if re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate):
                return candidate

    raise ValueError("Could not parse a valid YouTube video ID from input")


def api_get(path: str, params: dict) -> dict:
    resp = requests.get(f"{API_BASE}/{path}", params=params, timeout=20)
    if resp.status_code != 200:
        raise RuntimeError(f"YouTube API error {resp.status_code}: {resp.text[:400]}")
    return resp.json()


def parse_comment_thread(item: dict) -> dict:
    snippet = item.get("snippet", {})
    top = snippet.get("topLevelComment", {}).get("snippet", {})
    replies = item.get("replies", {}).get("comments", [])

    reply_items = []
    for r in replies:
        rs = r.get("snippet", {})
        reply_items.append(
            {
                "comment_id": r.get("id"),
                "author_display_name": rs.get("authorDisplayName"),
                "author_channel_id": (rs.get("authorChannelId") or {}).get("value"),
                "text_display": rs.get("textDisplay"),
                "text_original": rs.get("textOriginal"),
                "like_count": rs.get("likeCount"),
                "published_at": rs.get("publishedAt"),
                "updated_at": rs.get("updatedAt"),
            }
        )

    return {
        "thread_id": item.get("id"),
        "can_reply": snippet.get("canReply"),
        "total_reply_count": snippet.get("totalReplyCount"),
        "is_public": snippet.get("isPublic"),
        "top_level_comment": {
            "comment_id": (snippet.get("topLevelComment") or {}).get("id"),
            "author_display_name": top.get("authorDisplayName"),
            "author_channel_id": (top.get("authorChannelId") or {}).get("value"),
            "text_display": top.get("textDisplay"),
            "text_original": top.get("textOriginal"),
            "like_count": top.get("likeCount"),
            "published_at": top.get("publishedAt"),
            "updated_at": top.get("updatedAt"),
        },
        "replies": reply_items,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch YouTube comments")
    parser.add_argument("--video", required=True, help="YouTube video ID or URL")
    parser.add_argument("--api-key", help="Override API key (else YOUTUBE_API_KEY env)")
    parser.add_argument("--pages", type=int, default=1, help="Pages to fetch (default: 1)")
    parser.add_argument("--max-results", type=int, default=50, help="Per-page max (1-100, default: 50)")
    parser.add_argument(
        "--order",
        choices=["time", "relevance"],
        default="relevance",
        help="Comment order (default: relevance)",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    api_key = args.api_key or os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        print(json.dumps({"error": "Missing API key. Set YOUTUBE_API_KEY or use --api-key."}))
        return 1

    if args.max_results < 1 or args.max_results > 100:
        print(json.dumps({"error": "--max-results must be between 1 and 100"}))
        return 1
    if args.pages < 1:
        print(json.dumps({"error": "--pages must be >= 1"}))
        return 1

    try:
        video_id = extract_video_id(args.video)
    except ValueError as e:
        print(json.dumps({"error": str(e), "input": args.video}))
        return 1

    all_threads = []
    page_token = None
    pages_fetched = 0

    try:
        while pages_fetched < args.pages:
            params = {
                "part": "snippet,replies",
                "videoId": video_id,
                "maxResults": args.max_results,
                "order": args.order,
                "textFormat": "plainText",
                "key": api_key,
            }
            if page_token:
                params["pageToken"] = page_token

            data = api_get("commentThreads", params)

            items = data.get("items", [])
            all_threads.extend(parse_comment_thread(i) for i in items)

            pages_fetched += 1
            page_token = data.get("nextPageToken")
            if not page_token:
                break

    except Exception as e:
        print(json.dumps({"error": str(e), "video_id": video_id, "pages_fetched": pages_fetched}))
        return 1

    output = {
        "video_id": video_id,
        "order": args.order,
        "pages_requested": args.pages,
        "pages_fetched": pages_fetched,
        "threads_returned": len(all_threads),
        "threads": all_threads,
    }

    if args.pretty:
        print(json.dumps(output, indent=2))
    else:
        print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
