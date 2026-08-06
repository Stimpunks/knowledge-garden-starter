# My Knowledge Garden

> **Rename this file's title and delete this quote block.** Everything below is yours to
> edit — it is a starting set of rules, not scripture. The point is that the rules are
> written down *where the work happens*, so every session starts from the same constraints.
> That includes AI sessions: this file is what a coding agent reads first.

A folder of originals, an index over them, and a habit of adding to both.

## Layout

```
garden/raw/      Original, unaltered sources — the library. Never edited.
garden/wiki/     An index over raw/ — regenerated, never hand-edited.
garden/notes/    Live working notes. A workspace, not an archive.
garden/inbox/    Staging tray for undecided things. Usually empty.
```

## Rules — do not break these

### `raw/` is read-only, forever
- **Never edit, rename, move, delete, reformat, or reorganize** anything in `raw/`.
- Only ever **add**. If something in there looks wrong, say so — do not fix it.
- Keep it **flat**. No subfolders. All the sorting happens in `wiki/`, where changing your
  mind is a config edit instead of a broken link.
- This is the load-bearing rule. It is what makes the folder provenance rather than storage.

### `wiki/` is generated, never hand-edited
- To change the index, change `wiki/_config.json` and re-run the generator.
- Hand-edits get silently overwritten on the next run, which is worse than being refused.
- Every entry must point at a real file in `raw/`.

### `notes/` is a workspace
- Edit it freely. Unlike `raw/`, it is meant to change.
- `notes/Inbox/` is the sanctioned landing spot for anything you want on disk before you
  have decided where it goes.

### The staging tray is not a store
- Things in `inbox/` are *awaiting* a decision. The permanent copy always ends up in `raw/`.
- An empty tray is the healthy state.

## Rebuild

```bash
cd garden
python3 wiki/_generate.py --no-concepts
```

Safe to run any time. Overwrites the index; touches nothing in `raw/`.

If you have a search index too, the three steps are **ordered** — extract text, rebuild the
index, then `qmd update && qmd embed`. Out of order, every step still succeeds and the index
describes the wrong thing. See [README Step 4](README.md#step-4--make-it-searchable).

## If you are an AI working in this garden

- **Read from `raw/`; write understanding into `wiki/`.** Never the other way round.
- **Never modify `raw/`** — not to fix a filename, not to normalise an encoding. If you
  think something in there is wrong, surface it and stop. Corrections go in
  `garden/wiki/_overrides.json`, which exists precisely so nothing has to be renamed.
- **Do not hand-edit generated pages.** Change the config and regenerate.
- **Cite the original, not the index.** An index entry is a pointer; the source is the
  evidence. If a claim's only support is something you generated, you have found nothing.
- **Say what you did not cover.** If extraction failed on 40 files, report the 40. Silent
  partial coverage reads as completeness and is worse than an admitted gap.
- **Do not fill gaps from your training data.** If the garden does not say it, say the
  garden does not say it. A confident answer from somewhere else defeats the purpose of
  having a garden.
- **An unread file is not a source.** A promising filename is not evidence. Open it, or say
  you only have the title.
- **Ask before anything irreversible.** Deleting, overwriting, renaming, force-pushing, or
  rewriting history. Propose it and wait.
- **When a guard refuses, that is the system working.** Report the refusal and stop. Do not
  raise a limit, pass a `--force`, or find a way around it on the user's behalf — the
  refusal is the last moment when the mistake is still cheap to undo.

### Skills available here

Five narrow tools in `.claude/skills/`. Prefer them over improvising the same work by hand,
because they encode the rules above:

| Skill | Does |
|---|---|
| `add-to-garden` | Store one new file in `raw/` untouched, record a real title, rebuild the index |
| `tend-the-garden` | Build the index; work the Unidentified pile by actually opening files |
| `ask-my-garden` | Answer only from this garden, citing a file beside every claim |
| `commit-garden` | Commit and push the text layer with a message that says what changed — refuses mass deletions and placeholder messages |
| `check-readability` | Audit reading level and sentence length against plain-language targets |

Full walk-through for the human: [docs/working-with-claude.md](docs/working-with-claude.md).

## Honest limits

Worth keeping a list like this and adding to it as you find things:

- The generated index will mis-file things. Keyword matching over filenames is crude. That
  is cheap to fix — a config edit — precisely because the originals were never touched.
- Files whose names say nothing stay opaque until someone opens them and records a real
  title.
- A search index reflects the last time it was rebuilt, not what is on disk.
