#!/usr/bin/env python3
import sys
import os
import subprocess
from pathlib import Path

# Default Notebook ID (Knowledge Base)
DEFAULT_NOTEBOOK_ID = "5af9a497-5958-4149-9de4-9bd47d7eff16"

# Path to the main ingest script
INGEST_SCRIPT = "/home/ec2-user/.openclaw/workspace/features/notebookllm-integration/scripts/notebookllm.py"
VENV_PYTHON = "/home/ec2-user/.openclaw/workspace/features/notebookllm-integration/.venv/bin/python3"

def main():
    if len(sys.argv) < 2:
        print("Usage: notebookllm_dispatch <command_string>")
        return

    full_args = " ".join(sys.argv[1:])
    
    # Handle /start notebook_upload_<id>
    if "notebook_upload_" in full_args:
        # Extract video id
        video_id = full_args.split("notebook_upload_")[-1].strip()
        url = f"https://www.youtube.com/watch?v={video_id}"
        print(f"Triggered by deep link. Uploading video: {url}")
        upload(DEFAULT_NOTEBOOK_ID, url)
    
    # Handle /notebook_upload <source>
    elif "/notebook_upload" in full_args:
        source = full_args.split("/notebook_upload")[-1].strip()
        if not source:
            print("Error: No source provided. Usage: /notebook_upload <url|file|text>")
            return
        upload(DEFAULT_NOTEBOOK_ID, source)
    
    else:
        # Check if it looks like just a URL or ID passed directly to the tool
        source = full_args.strip()
        if source:
            upload(DEFAULT_NOTEBOOK_ID, source)
        else:
            print("NotebookLLM Dispatcher: Ready.")

def upload(notebook_id, source):
    cmd = [VENV_PYTHON, INGEST_SCRIPT, notebook_id, source]
    try:
        # Use subprocess.run to capture output and print it
        result = subprocess.run(cmd, text=True, capture_output=True)
        if result.returncode == 0:
            print(result.stdout)
        else:
            print(f"Upload failed (code {result.returncode}):\n{result.stderr}")
    except Exception as e:
        print(f"Internal error: {e}")

if __name__ == "__main__":
    main()
