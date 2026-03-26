#!/usr/bin/env python3
"""
Fetch YouTube transcript with safe, local-only behavior.

- No host network mutation
- No VPN auto-setup
- Graceful error outputs

Usage:
  python3 fetch_transcript.py --video dQw4w9WgXcQ --pretty
  python3 fetch_transcript.py --video https://www.youtube.com/watch?v=dQw4w9WgXcQ --languages en,es
"""

import argparse
import json
import re
import sys
from urllib.parse import parse_qs, urlparse

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import (
        NoTranscriptFound,
        TranscriptsDisabled,
        VideoUnavailable,
    )
except ImportError:
    print(json.dumps({
        "error": "Missing dependency: youtube-transcript-api",
        "hint": "Install with: pip install youtube-transcript-api",
    }))
    sys.exit(1)


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


def normalize_entries(entries):
    out = []
    for e in entries:
        out.append(
            {
                "text": e.get("text", ""),
                "start": e.get("start", 0.0),
                "duration": e.get("duration", 0.0),
            }
        )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch YouTube transcript safely")
    parser.add_argument("--video", required=True, help="YouTube video ID or URL")
    parser.add_argument(
        "--languages",
        default="en",
        help="Comma-separated language priority list (default: en)",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    try:
        video_id = extract_video_id(args.video)
    except ValueError as e:
        print(json.dumps({"error": str(e), "input": args.video}))
        return 1

    languages = [x.strip() for x in args.languages.split(",") if x.strip()]
    if not languages:
        languages = ["en"]

    try:
        api = YouTubeTranscriptApi()
        fetched = api.fetch(video_id, languages=languages)
        entries = normalize_entries(fetched.to_raw_data())
        full_text = " ".join(x["text"] for x in entries).strip()

        output = {
            "video_id": video_id,
            "languages_requested": languages,
            "language_selected": getattr(fetched, "language_code", None),
            "is_generated": getattr(fetched, "is_generated", None),
            "entry_count": len(entries),
            "full_text": full_text,
            "transcript": entries,
        }

        if args.pretty:
            print(json.dumps(output, indent=2, ensure_ascii=False))
        else:
            print(json.dumps(output, ensure_ascii=False))
        return 0

    except TranscriptsDisabled:
        print(json.dumps({
            "error": "Transcripts are disabled for this video",
            "video_id": video_id,
            "languages_requested": languages,
        }))
        return 1
    except NoTranscriptFound:
        print(json.dumps({
            "error": "No transcript found for requested languages",
            "video_id": video_id,
            "languages_requested": languages,
        }))
        return 1
    except VideoUnavailable:
        print(json.dumps({"error": "Video unavailable", "video_id": video_id}))
        return 1
    except Exception as e:
        print(json.dumps({
            "error": str(e),
            "video_id": video_id,
            "languages_requested": languages,
        }))
        return 1


if __name__ == "__main__":
    sys.exit(main())
