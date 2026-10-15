---
name: reindex
description: Rebuild the garden's index and its search in the one order that works — the index over raw/, then the extracted text of raw/, then qmd update and embed — and refuse to call it done while anything is still pending. Use when the user says "reindex", "rebuild the index", "update search", "refresh the search index", "make my PDFs searchable", or after adding files, editing notes, or retitling things in _overrides.json.
---

# reindex

One command for the three rebuild steps, so they cannot be run out of order:

```bash
python3 .claude/skills/reindex/reindex.py
```

| Step | What | If it fails |
|---|---|---|
| 1 | `garden/wiki/_generate.py` — the index over `raw/` | **Stop.** That *is* the index. |
| 2 | `garden/wiki/_qmd_library.py` — the text of `raw/`, for search | Report; the index is fine |
| 3 | `qmd update`, then `qmd embed` until nothing is pending | Report; the index is fine |

Other forms: `--check` reports and writes nothing · `--no-embed` skips the slow vector step ·
`--ocr` also OCRs scanned PDFs (minutes per book, cached afterwards, so pay it once).

## Why this is a script

Every step reports success when run in the wrong order. Embed before the index is rebuilt and
search describes the old index. Extract text into a format qmd does not read and the library
collection indexes **zero files** — this template's own docs once did exactly that. A rule in
a README is a suggestion; a fixed order is not.

## Steps

1. **Run it.** If the user has only edited notes, it is still the right command — it is quick
   when little has changed.
2. **Read the exit code and say what it means:**
   - **0** — index and search both current. Say so in one line.
   - **1** — the index did not rebuild. **Stop and report the message.** The common cause is
     the manifest guard: files the index knows about are missing from `raw/`, which usually
     means this is a second computer or a drive is unplugged. Do **not** pass
     `--allow-raw-shrink` on the user's behalf — that is the guard working.
   - **2** — the index is fine but search is behind. Name each problem it printed.
3. **Report coverage honestly.** Step 2 prints how many files are searchable and how many are
   not, by reason (images, scans, a missing tool). Pass those numbers on. "312 searchable,
   41 cannot be read — mostly images" is the useful sentence; "reindexed" is not.
4. **Offer the commit.** A rebuild changes `garden/wiki/`. Hand it to `commit-garden`; this
   skill never commits. Nothing under `.qmd/` is ever committed.

## The traps it exists for

- **`qmd embed` can exit 0 with work left.** It stops at an internal batch limit and says
  nothing. The script reads qmd's `Pending:` count after each pass and goes again while it
  is still falling. Until it reaches 0, `qmd query` silently cannot return what was skipped —
  so **never report a clean search while anything is pending.**
- **qmd only finds an index in the folder it is run from, or above it.** The index lives at
  the top of the project in `.qmd/`, which is where Claude works from. One made inside
  `garden/` is invisible from the top, and searching there returns nothing without an error.
  `--check` spots that.
- **A missing tool is not an empty file.** If `pdftotext` is not installed, step 2 says those
  PDFs were *not read*. Do not report them as unreadable.

## Rules

- **Never write to `garden/raw/`.** Nothing here does; keep it that way.
- **Never hand-edit the generated pages** to make a rebuild "pass". Change `_config.json` or
  `_overrides.json` and run it again.
- **If search is not set up, that is fine.** Step 3 is skipped with a pointer to README Step 4.
  The garden works without search; do not set it up unasked.
