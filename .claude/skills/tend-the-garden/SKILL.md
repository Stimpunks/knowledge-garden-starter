---
name: tend-the-garden
description: Build or rebuild the garden's index, then work through the Unidentified pile by opening files and recording real titles for them. Use when the user says "build my index", "make the wiki", "tend the garden", "what's in Unidentified", "clean up my index", or has just added a batch of files.
---

# tend-the-garden

This is the skill that makes the index get better over time instead of merely existing.
Two halves: build it, then reduce the pile of things nobody has looked at.

## Half one: build the index

```bash
cd garden && python3 wiki/_generate.py --no-concepts
```

Safe to run at any time. It reads `garden/raw/`, writes `garden/wiki/README.md` plus one
page per shelf, and overwrites whatever was there. It never touches `raw/`.

**First time?** If `garden/wiki/_config.json` still has the placeholder shelves
(`reading`, `writing`, `reference`), say so and offer to replace them with categories that
match what the user actually collects. That single file is the difference between a useful
index and a generic one. Look at what is in `raw/` before proposing shelves — suggest
categories the library actually needs, not categories in the abstract.

## Half two: work the Unidentified pile

Open `garden/wiki/unidentified.md`. Everything there is a file whose name told the
generator nothing. **This is the to-do list, not a failure.**

For each one, in small batches — five or ten, not eighty:

1. **Open the file and read enough to name it.** Title page, abstract, first heading.
2. **Add an entry to `garden/wiki/_overrides.json`** with a real `title` and, if one fits, a
   `category`.
3. **Regenerate** and report how the count moved.

**Say what you could not do.** Images, scanned PDFs with no text layer, and cloud-document
pointers cannot be read. Those stay Unidentified legitimately. Report them as *"N files
yield no readable text"* rather than quietly leaving them in the pile as though nobody has
got to them yet. A pile with a known floor is manageable; a pile of unknown composition is
just guilt.

## Rules

- **Never rename anything in `raw/` to fix a title.** That is what `_overrides.json` is for.
  Renaming breaks the one guarantee the library makes.
- **Never hand-edit `garden/wiki/*.md`.** Every page there is regenerated. Your edits vanish
  on the next run, which is worse than being refused.
- **Do not invent a title from a filename.** If you have not opened the file, you do not know
  what it is. `2604.16106v2.pdf` is not a title and neither is your best guess at one.
- **Do not invent categories** to make the pile look smaller. A wrong shelf is worse than an
  honest Unidentified, because it hides the file behind a confident label.

## A good report looks like

> Rebuilt: 47 files across 4 shelves. Unidentified went 19 → 11.
> Titled 8 papers (all opened and read). Of the remaining 11: 6 are images with no text,
> 3 are scanned PDFs I cannot extract, and 2 I could open but could not confidently
> categorise — they are listed below if you want to place them.
