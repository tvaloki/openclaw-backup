#!/usr/bin/env python3
"""
Fetch YouTube video + channel metadata via YouTube Data API v3.

Usage:
  python3 fetch_video_meta.py --video "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
  python3 fetch_video_meta.py --video dQw4w9WgXcQ --pretty

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
    """Extract 11-char video ID from raw ID or URL."""
    video_input = video_input.strip()

    # Direct ID
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", video_input):
        return video_input

    # URL forms
    try:
        parsed = urlparse(video_input)

        # youtu.be/<id>
        if parsed.netloc in {"youtu.be", "www.youtu.be"}:
            candidate = parsed.path.lstrip("/").split("/")[0]
            if re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate):
                return candidate

        # youtube.com/watch?v=<id>
        qs = parse_qs(parsed.query)
        if "v" in qs and qs["v"]:
            candidate = qs["v"][0]
            if re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate):
                return candidate

        # youtube.com/embed/<id> or /shorts/<id>
        parts = [p for p in parsed.path.split("/") if p]
        for idx, part in enumerate(parts):
            if part in {"embed", "shorts", "v"} and idx + 1 < len(parts):
                candidate = parts[idx + 1]
                if re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate):
                    return candidate
    except Exception:
        pass

    raise ValueError("Could not parse a valid YouTube video ID from input")


def api_get(path: str, params: dict) -> dict:
    resp = requests.get(f"{API_BASE}/{path}", params=params, timeout=20)
    if resp.status_code != 200:
        raise RuntimeError(f"YouTube API error {resp.status_code}: {resp.text[:400]}")
    return resp.json()


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch YouTube video metadata")
    parser.add_argument("--video", required=True, help="YouTube video ID or URL")
    parser.add_argument("--api-key", help="Override API key (else YOUTUBE_API_KEY env)")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    api_key = args.api_key or os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        print(json.dumps({"error": "Missing API key. Set YOUTUBE_API_KEY or use --api-key."}))
        return 1

    try:
        video_id = extract_video_id(args.video)
    except ValueError as e:
        print(json.dumps({"error": str(e), "input": args.video}))
        return 1

    try:
        video_data = api_get(
            "videos",
            {
                "part": "snippet,contentDetails,statistics,status",
                "id": video_id,
                "key": api_key,
            },
        )
    except Exception as e:
        print(json.dumps({"error": str(e), "video_id": video_id}))
        return 1

    items = video_data.get("items", [])
    if not items:
        print(json.dumps({"error": "Video not found", "video_id": video_id}))
        return 1

    video = items[0]
    snippet = video.get("snippet", {})
    stats = video.get("statistics", {})
    content_details = video.get("contentDetails", {})
    status = video.get("status", {})

    channel_id = snippet.get("channelId")
    channel_payload = {}

    if channel_id:
        try:
            ch_data = api_get(
                "channels",
                {
                    "part": "snippet,statistics,status",
                    "id": channel_id,
                    "key": api_key,
                },
            )
            ch_items = ch_data.get("items", [])
            if ch_items:
                ch = ch_items[0]
                ch_snippet = ch.get("snippet", {})
                channel_payload = {
                    "channel_id": ch.get("id"),
                    "title": ch_snippet.get("title"),
                    "description": ch_snippet.get("description"),
                    "custom_url": ch_snippet.get("customUrl"),
                    "published_at": ch_snippet.get("publishedAt"),
                    "country": ch_snippet.get("country"),
                    "statistics": ch.get("statistics", {}),
                    "status": ch.get("status", {}),
                }
        except Exception as e:
            channel_payload = {"error": str(e), "channel_id": channel_id}

    output = {
        "video": {
            "video_id": video.get("id"),
            "url": f"https://www.youtube.com/watch?v={video.get('id')}",
            "title": snippet.get("title"),
            "description": snippet.get("description"),
            "published_at": snippet.get("publishedAt"),
            "channel_id": snippet.get("channelId"),
            "channel_title": snippet.get("channelTitle"),
            "tags": snippet.get("tags", []),
            "category_id": snippet.get("categoryId"),
            "default_language": snippet.get("defaultLanguage"),
            "duration": content_details.get("duration"),
            "definition": content_details.get("definition"),
            "caption": content_details.get("caption"),
            "licensed_content": content_details.get("licensedContent"),
            "projection": content_details.get("projection"),
            "statistics": stats,
            "status": status,
        },
        "channel": channel_payload,
    }

    if args.pretty:
        print(json.dumps(output, indent=2))
    else:
        print(json.dumps(output))

    return 0


if __name__ == "__main__":
    sys.exit(main())
