import asyncio
import sys
from notebooklm import NotebookLMClient

async def get_transcript(notebook_id, source_id):
    async with await NotebookLMClient.from_storage() as client:
        try:
            fulltext = await client.sources.get_fulltext(notebook_id, source_id)
            print(f"Title: {fulltext.title}")
            print(f"Text Length: {len(fulltext.content)}")
            print("-" * 40)
            print(fulltext.content[:1000] + "..." if len(fulltext.content) > 1000 else fulltext.content)
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: get_transcript.py <notebook_id> <source_id>")
        sys.exit(1)
    asyncio.run(get_transcript(sys.argv[1], sys.argv[2]))
