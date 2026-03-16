# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.

### OpenBrain MCP Tools

- **`search_docs`**: When calling the `search_docs` Supabase GraphQL tool via MCP, the resulting type is `SearchResultCollection`. It DOES NOT have fields like `docs`, `results`, `title`, or `content`. You MUST query the `nodes` or `edges` array instead. 
  Example valid query:
  ```graphql
  query {
    searchDocs(query: "YOUR_QUERY", limit: 5) {
      nodes {
        title
        href
        content
      }
    }
  }
  ```
