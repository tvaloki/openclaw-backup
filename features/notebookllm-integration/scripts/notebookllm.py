import asyncio
import logging
import argparse
import sys
import os
from urllib.parse import urlparse
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s [%(name)s] %(message)s')

# Add the local library to the path (it's in the .venv/lib/python3.11/site-packages)
# Since we are in an OpenClaw environment, we might want to ensure the .venv is used.

try:
    from notebooklm import NotebookLMClient
except ImportError:
    # Attempt to find the .venv site-packages if not in path
    venv_path = Path(__file__).parent.parent / ".venv" / "lib" / "python3.11" / "site-packages"
    if venv_path.exists():
        sys.path.append(str(venv_path))
        from notebooklm import NotebookLMClient
    else:
        print("Error: notebooklm library not found. Please install it in the .venv.")
        sys.exit(1)

def is_youtube_url(url):
    """Check if a URL is a YouTube URL."""
    try:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        return hostname in ["youtube.com", "www.youtube.com", "youtu.be", "m.youtube.com"]
    except Exception:
        return False

async def add_source(notebook_id, source_input):
    """Add a source to a NotebookLM notebook."""
    async with await NotebookLMClient.from_storage() as client:
        # Refresh auth to ensure tokens are fresh
        print("Refreshing authentication...")
        await client.refresh_auth()
        
        # 1. Check if it's a URL
        if source_input.startswith(("http://", "https://")):
            # The library's add_url already detects YouTube and routes correctly.
            # This avoids local yt-dlp processing and the AWS IP block.
            print(f"Adding URL source: {source_input}")
            source = await client.sources.add_url(notebook_id, source_input, wait=True)
            print(f"Successfully added source: {source.title} (ID: {source.id})")
            return source
        
        # 2. Check if it's a local file
        elif os.path.isfile(source_input):
            print(f"Adding file source: {source_input}")
            source = await client.sources.add_file(notebook_id, source_input, wait=True)
            print(f"Successfully added file source: {source.title} (ID: {source.id})")
            return source
        
        # 3. Otherwise, treat as raw text
        else:
            print("Adding as text source...")
            title = "Pasted Text " + source_input[:20]
            source = await client.sources.add_text(notebook_id, title, source_input, wait=True)
            print(f"Successfully added text source: {source.title} (ID: {source.id})")
            return source

def main():
    parser = argparse.ArgumentParser(description="NotebookLM Ingest Script")
    parser.add_argument("notebook_id", help="The Notebook ID to add the source to")
    parser.add_argument("source", help="URL, file path, or text content")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(add_source(args.notebook_id, args.source))
    except Exception as e:
        print(f"Error: {e}")
        if hasattr(e, 'found_ids'):
            print(f"Found IDs in response: {e.found_ids}")
        if hasattr(e, 'raw_response'):
            print(f"Raw response preview: {e.raw_response}")
        sys.exit(1)

if __name__ == "__main__":
    main()
