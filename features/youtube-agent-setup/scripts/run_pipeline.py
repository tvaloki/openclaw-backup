#!/usr/bin/env python3
"""
Run YouTube pipeline: metadata + comments + transcript.

Usage:
  python3 run_pipeline.py --video <id_or_url> --api-key <key> --pretty
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from agentmail import AgentMail

BASE = Path(__file__).resolve().parent


def run_cmd(cmd):
    p = subprocess.run(cmd, text=True, capture_output=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def run_step(name, cmd):
    code, out, err = run_cmd(cmd)
    if code == 0:
        try:
            return {"ok": True, "data": json.loads(out)}
        except Exception:
            return {"ok": False, "error": f"{name} returned non-JSON output", "stderr": err, "raw": out[:500]}
    return {"ok": False, "error": out or err or f"{name} failed", "code": code}


def compact_text(s: str, max_len: int = 600) -> str:
    s = (s or "").replace("\n", " ").strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + "…"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run YouTube fetch pipeline")
    parser.add_argument("--video", required=True, help="YouTube video ID or URL")
    parser.add_argument("--api-key", help="YouTube API key (or use YOUTUBE_API_KEY env)")
    parser.add_argument("--comment-pages", type=int, default=1)
    parser.add_argument("--comment-max-results", type=int, default=20)
    parser.add_argument("--languages", default="en")
    parser.add_argument("--out", help="Optional output JSON file path")
    parser.add_argument("--email-to", help="Optional recipient email for AgentMail pipeline report")
    parser.add_argument("--agentmail-inbox", default="dougyfresh@agentmail.to", help="AgentMail sender inbox")
    parser.add_argument("--save-pgmemory", action="store_true", help="Save pipeline run summary to pgmemory")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    api_key = args.api_key or os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        print(json.dumps({"error": "Missing API key. Set YOUTUBE_API_KEY or pass --api-key"}))
        return 1

    meta_cmd = [
        "python3", str(BASE / "fetch_video_meta.py"),
        "--video", args.video,
        "--api-key", api_key,
    ]
    comments_cmd = [
        "python3", str(BASE / "fetch_comments.py"),
        "--video", args.video,
        "--api-key", api_key,
        "--pages", str(args.comment_pages),
        "--max-results", str(args.comment_max_results),
    ]
    transcript_cmd = [
        "python3", str(BASE / "fetch_transcript.py"),
        "--video", args.video,
        "--languages", args.languages,
    ]

    metadata = run_step("metadata", meta_cmd)
    comments = run_step("comments", comments_cmd)
    transcript = run_step("transcript", transcript_cmd)

    output = {
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "input": {
            "video": args.video,
            "comment_pages": args.comment_pages,
            "comment_max_results": args.comment_max_results,
            "languages": args.languages,
        },
        "results": {
            "metadata": metadata,
            "comments": comments,
            "transcript": transcript,
        },
    }

    if args.out:
        out_path = Path(args.out).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")

    # Optional AgentMail report step (M5 integrated email delivery)
    if args.email_to:
        mail_key = os.getenv("AGENTMAIL_API_KEY")
        if not mail_key:
            output["agentmail_report"] = {"ok": False, "error": "AGENTMAIL_API_KEY not set"}
        else:
            try:
                meta = output["results"]["metadata"]
                com = output["results"]["comments"]
                tr = output["results"]["transcript"]

                video_title = "(unknown)"
                video_id = args.video
                if meta.get("ok"):
                    v = meta["data"]["video"]
                    video_title = v.get("title", "(unknown)")
                    video_id = v.get("video_id", video_id)

                threads = com["data"].get("threads_returned", "n/a") if com.get("ok") else "n/a"
                entries = tr["data"].get("entry_count", "n/a") if tr.get("ok") else "n/a"
                lang = tr["data"].get("language_selected", "n/a") if tr.get("ok") else "n/a"

                body = (
                    "YouTube Agent Pipeline Report\n\n"
                    f"Run: {output['run_at_utc']}\n"
                    f"Video ID: {video_id}\n"
                    f"Title: {video_title}\n\n"
                    "Results\n"
                    f"- Metadata: {'OK' if meta.get('ok') else 'FAIL'}\n"
                    f"- Comments: {'OK' if com.get('ok') else 'FAIL'} (threads returned: {threads})\n"
                    f"- Transcript: {'OK' if tr.get('ok') else 'FAIL'} (entries: {entries}, language: {lang})\n"
                )
                if args.out:
                    body += f"\nArtifact\n- {str(Path(args.out).expanduser().resolve())}\n"

                client = AgentMail(api_key=mail_key)
                resp = client.inboxes.messages.send(
                    inbox_id=args.agentmail_inbox,
                    to=args.email_to,
                    subject="YouTube pipeline report",
                    text=body,
                )
                output["agentmail_report"] = {
                    "ok": True,
                    "to": args.email_to,
                    "inbox": args.agentmail_inbox,
                    "message_id": getattr(resp, "message_id", None),
                    "thread_id": getattr(resp, "thread_id", None),
                }
            except Exception as e:
                output["agentmail_report"] = {"ok": False, "error": str(e)}

    # Optional pgmemory persistence step (M6)
    if args.save_pgmemory:
        try:
            meta = output["results"]["metadata"]
            com = output["results"]["comments"]
            tr = output["results"]["transcript"]

            video_id = args.video
            video_title = "(unknown)"
            if meta.get("ok"):
                v = meta["data"]["video"]
                video_id = v.get("video_id", video_id)
                video_title = v.get("title", "(unknown)")

            summary = (
                f"YouTube pipeline run at {output['run_at_utc']} for {video_id} ({compact_text(video_title, 120)}). "
                f"metadata={'ok' if meta.get('ok') else 'fail'}, "
                f"comments={'ok' if com.get('ok') else 'fail'}"
            )
            if com.get("ok"):
                summary += f" threads={com['data'].get('threads_returned', 'n/a')}"
            summary += ", "
            summary += f"transcript={'ok' if tr.get('ok') else 'fail'}"
            if tr.get("ok"):
                summary += f" entries={tr['data'].get('entry_count', 'n/a')} lang={tr['data'].get('language_selected', 'n/a')}"

            key = f"youtube.pipeline.last_run.{video_id}"
            write_cmd = [
                "python3",
                "/home/ec2-user/.openclaw/workspace/skills/pgmemory/scripts/write_memory.py",
                "--key", key,
                "--content", summary,
                "--category", "task",
                "--importance", "2",
            ]
            code, out, err = run_cmd(write_cmd)
            if code == 0:
                output["pgmemory_save"] = {"ok": True, "key": key, "result": out}
            else:
                output["pgmemory_save"] = {"ok": False, "key": key, "error": out or err}
        except Exception as e:
            output["pgmemory_save"] = {"ok": False, "error": str(e)}

    if args.pretty:
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(output, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())
