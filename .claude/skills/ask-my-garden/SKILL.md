---
name: ask-my-garden
description: Answer a question using ONLY what is in this garden — the library, the index, and the notes — citing the file beside every claim and refusing to fill gaps from training data. Use when the user says "ask my garden", "what do I have on…", "what did I read about…", "search my notes", or wants an answer grounded strictly in their own collection.
---

# ask-my-garden

Answer from the garden and nothing else. If the garden does not say it, **say that the garden
does not say it.**

## The one rule that defines this skill

**Every claim ends at a file in this garden, cited. If it is not here, name the gap — never
fill it from what you already know.**

This overrides the ordinary instinct to be helpful. A fluent answer assembled from training
data is a **failure** of this skill, not a success, because it defeats the entire reason the
user built a garden: to know where things came from. When you cannot tell whether something
came from a file you opened or from your own memory, **treat it as memory and cut it**.

## Procedure

### 1. Search before writing a single sentence

Search first, compose second. Never the other way round.

```bash
grep -ril "your terms" garden/notes garden/wiki
```

**Cast wider than the user's exact words.** They will ask in their language; the files are in
somebody else's. Try synonyms, the technical term, the plain-language term, an author's
surname. Two or three passes with different vocabulary beats one pass with the obvious word.

**`garden/raw/` is mostly binary and cannot be grepped.** Reach it two ways:
- Read `garden/wiki/` — the index names every stored file and shelves it by topic.
- For a PDF that looks relevant, extract and read it: `pdftotext -q "garden/raw/file.pdf" -`

If the user has installed [qmd](https://github.com/tobi/qmd), prefer it — it finds passages
by meaning rather than by matching words the user had to guess:

```bash
qmd query "the question in their own words"
```

### 2. Judge what you found, honestly

- **Solid support** → answer, grounded entirely in it.
- **Partial or tangential** → answer only the part the garden supports, and name the gap for
  the rest. **Do not smooth over the seam** with something you happen to know.
- **Nothing** → say so plainly. Then say what would answer it, so the gap becomes a shopping
  list rather than a dead end.

### 3. Answer with the citation attached

Put the source next to the claim, not in a pile at the bottom:

> Monotropism describes attention pulled into a narrow tunnel
> (`garden/raw/monotropism-murray-2005.pdf`), which is why transitions cost more than they
> look like they should — your note from March makes the same point about mornings
> (`garden/notes/2026-03-attention.md`).

Cite the **original** in `garden/raw/`, never a generated index page that merely pointed you
at it. An index entry is a signpost; the file is the evidence. **If a claim's only support is
something the generator wrote, you have found nothing yet.**

### 4. When the garden is silent, say so

> Nothing here on the double empathy problem. The index has no source by Milton, and the
> notes mention the phrase twice without citing anything. **I am not going to fill that in
> from memory** — that is the gap this garden exists to make visible. Milton's 2012 paper
> is the primary source if you want to close it.

That is a good answer. It is more useful than a confident paragraph, because it is true, and
because it tells the user exactly what to go and get.

## Boundaries

- **No web searching** unless the user explicitly asks. The point is what *they* hold.
- **No hedged blending.** Do not write "generally, research suggests…" as a bridge over a
  gap. Either the garden supports it with a citable file or it does not.
- **Quote sparingly and mark it.** If you quote, quote exactly and name the file. Do not
  paraphrase a source into something it did not quite say.
- **An unread file is not a source.** Finding a promising filename is not the same as reading
  it. Open it, or say you only have the title.
