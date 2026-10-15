---
name: process-inbox
description: Empty the garden's inbox tray — open each waiting file to learn what it really is, store it in raw/ untouched with a real title, clear it from the tray only after the stored copy is verified, then rebuild the index once. Use when the user says "process the inbox", "file what's in my inbox", "deal with the inbox", or has dropped several files into garden/inbox/.
---

# process-inbox

The batch version of `add-to-garden`. `garden/inbox/` is a tray for things nobody has decided
about yet. This skill decides — one file at a time — and leaves the tray empty.

The script does the copying, checking, and clearing. **You do the part a script cannot:
opening each file and working out what it actually is.**

## Steps

1. **See what is waiting.**
   ```bash
   python3 .claude/skills/process-inbox/process-inbox.py list
   ```
   If it is empty, say so and stop.

2. **Open each file before storing it.** Read enough to know the real title, the author, and
   roughly what it argues — the title page, the abstract, the first heading.
   - PDFs: `pdftotext -l 2 "<file>" - | head -60`
   - Anything else: open it, view it, or read its metadata.
   This is the step that earns its keep. A file stored with a true title is findable forever;
   one stored blind joins the Unidentified pile, and `2604.16106v2.pdf` tells nobody anything.

3. **Pick a shelf, or don't.**
   ```bash
   python3 .claude/skills/process-inbox/process-inbox.py categories
   ```
   If none fits, leave `--category` out. An honest Unidentified beats a wrong shelf. **Do not
   invent a category** — a new shelf is a change to `_config.json` the user owns. Note it
   for them instead.

4. **Store it — one command per file:**
   ```bash
   python3 .claude/skills/process-inbox/process-inbox.py ingest "garden/inbox/<file>" \
     --title "The Real Title" --category reading
   ```
   It copies the file into `garden/raw/` untouched, records the title in `_overrides.json`,
   checks the stored copy byte for byte, and only then removes it from the inbox. If raw/
   already holds the same bytes it says `already-present` and stores nothing twice. `--keep`
   stores it but leaves it in the tray.

5. **Rebuild once, at the end** — not after every file:
   ```bash
   python3 .claude/skills/reindex/reindex.py
   ```
   (Or `cd garden && python3 wiki/_generate.py --no-concepts` if search is not set up.)

6. **Report the batch.** For each file: where it was stored, the title you gave it, the shelf
   it landed on, and whether it was new or already there. Then say the tray is empty, or what
   was deliberately left. Name anything you could not read — an image, a scan with no text —
   rather than inventing a title from its filename.

## Rules

- **Never edit, rename, or delete anything in `garden/raw/`.** The script only ever adds.
- **A clipped web page is not an original.** If it lacks its source URL and the date it was
  clipped, say so before storing it. An unsourced clipping looks like evidence and is not.
- **One file, one considered title.** Do not loop the whole tray through a single command with
  made-up titles. The point of the tray is that each thing gets looked at.
- **If the script refuses, report it and stop.** It refuses rather than overwrite an original,
  and that is the guard working.
