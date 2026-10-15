---
name: add-to-garden
description: Store a new file in the garden's library untouched, work out what it actually is, record a real title for it, and rebuild the index. Use whenever the user hands over a file to keep — a PDF, epub, doc, image, or a page they clipped — or says "add this", "file this", "keep this", or "add to my garden".
---

# add-to-garden

One job: put an original into `garden/raw/` **without altering it**, then make the index
describe it honestly. Nothing else.

## The two rules that must not break

1. **`garden/raw/` is append-only.** Copy in. Never edit, rename, move, delete, reformat,
   or reorganise anything already there. If a stored file looks wrong, say so and stop.
2. **Never hand-edit the generated pages** in `garden/wiki/`. They are overwritten on every
   run. Corrections go in `garden/wiki/_overrides.json`, then you regenerate.

## Steps

1. **Get a real path.** One file per run. If the user gestured at something vague
   ("that paper"), ask which file rather than guessing.

2. **Look at it before storing it.** Open the PDF, epub, or doc far enough to know the real
   title, the author, and roughly what it argues. This is the step that earns its keep — a
   file stored with a truthful title is findable forever, and one stored blind joins the
   Unidentified pile.

3. **Copy it in, unchanged, and record what it is** — one command does both:

   ```bash
   python3 .claude/skills/process-inbox/process-inbox.py ingest "/path/to/the/file.pdf" \
     --title "Applied Behavior Analysis in Children and Youth with Autism: A Scoping Review" \
     --category reading
   ```

   It copies — never moves, never links — so the user's own copy stays where they had it.
   It refuses to overwrite: a name collision gets a ` (2)` suffix, and the result says so.
   If `raw/` already holds the same bytes it reports `already-present` and stores nothing
   twice. It checks the stored copy byte for byte, and writes the title into
   `garden/wiki/_overrides.json` under the exact stored filename.

4. **Choose the category honestly.** `process-inbox.py categories` lists the shelf ids from
   `garden/wiki/_config.json`. If none fit, **leave `--category` out** and say so — the file
   lands in Unidentified, which is an honest to-do rather than a wrong shelf. Do not invent
   a new category without asking; that is a config change the user owns.

5. **Rebuild the index.**

   ```bash
   python3 .claude/skills/reindex/reindex.py
   ```

   That also refreshes search, if the user has set it up. Without search,
   `cd garden && python3 wiki/_generate.py --no-concepts` is enough.

6. **Report plainly.** The stored filename, the title you recorded, which shelf it landed
   on, and anything you could not determine. If you could not read the file — an image, a
   scanned PDF with no text layer — **say that outright** instead of inventing a title from
   the filename.

## Notes

- **A clipped web page is not an original.** If the file came from a web clipper, it is a
  conversion, and it must carry its source URL and clip date in its frontmatter. If it does
  not, say so before storing it — an unsourced clipping looks like evidence and is not.
- Adding several files? Do them one at a time, or use `process-inbox` if the user has been
  dropping things into `garden/inbox/`.
- The index is disposable and the sources are not. If a category turns out wrong, that is a
  one-line edit to `_overrides.json` and a rebuild. Nothing in `raw/` ever moves.
