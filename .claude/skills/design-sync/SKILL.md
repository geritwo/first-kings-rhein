---
name: design-sync
description: Apply a pasted "design delta" from a claude.ai design chat to First Kings' design docs, decision log and open questions — or export the current design state for upload back to claude.ai.
---

# Design sync

## Import (delta → docs)
Input: a design delta pasted by me, in this shape:

```
DESIGN DELTA — <date> — <topic>
Decided:   <bullets>
Leaning:   <bullets>
Proposed:  <bullets>   (Claude's suggestions I haven't accepted)
Open:      <bullets>
Resolved open questions: <bullets>
Affects files: <docs/design/0X-...>
```

Steps:
1. Read the affected design files and `docs/decisions.md`.
2. Show me a short diff plan: which lines change in which file, and any **conflict** with
   existing `DECIDED` items or with code already built. Wait for my OK if there is a conflict.
3. Edit the design files with the right status tags. Mark superseded decisions, don't delete them
   from the log.
4. Append `Decided` items to `docs/decisions.md` (source: `chat`).
5. Update `docs/open-questions.md` (add new, tick resolved).
6. If a change affects a backlog item that is `done` or `doing`, add a follow-up row to
   `docs/backlog.md` instead of silently changing code.

## Export (docs → claude.ai)
When I say "export design": list the design files changed since the last export (use git log),
so I can re-upload them to the claude.ai project. Optionally produce `docs/design-snapshot.md`
— all design files concatenated, for a single upload.
