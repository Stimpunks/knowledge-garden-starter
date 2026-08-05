# Knowledge Garden Starter

A template for keeping everything you read, save, and write in one place you can still
trust in ten years — and search, and cite, and hand to someone else.

It is the pattern behind the
[Stimpunks Knowledge System](https://stimpunks.org/fieldguide/it/knowledge-system/),
stripped of anything Stimpunks-specific. Copy it, rename three things, and it is yours.

**You do not need all of it.** The first step needs no software at all. Stop wherever it
stops being useful — most of the value is in step one, and each later step only adds
convenience on top of a thing that already worked.

---

## Step 1 — Make a garden. No tools required.

From [The Stimpunks Knowledge System as Curriculum](https://stimpunks.org/space/knowledge-system/):

> 1. One folder. Everything they read, save, or write goes in it, untouched.
> 2. One index file, listing what's in the folder with a line about why each thing is there.
> 3. A habit of adding to both.
>
> That's it. That's a garden. No app, no subscription, no AI.

That is genuinely the whole idea. This repo is that, with the folders already made:

```
garden/
  raw/      Your originals. NEVER edited, renamed, or reorganised. Kept flat.
  wiki/     Your index. Points at raw/. Regenerated, not hand-maintained.
  notes/    Your live writing. Edit this freely — it is a workspace, not an archive.
  inbox/    Undecided things. Should usually be empty.
```

**The one rule that makes it work:** never edit anything in `raw/`. Not to tidy a filename,
not to fix a typo. Every derived thing — every summary, category, and index — lives
somewhere else and points back. That is the difference between provenance you can cite and
a pile you have been quietly rewriting.

You can do step 1 in Finder, in [Obsidian](https://obsidian.md/), in anything. Put a PDF in
`garden/raw/`, write a line about why in `garden/wiki/README.md`, repeat. **If you stop
here you already have the thing.** Everything below is convenience.

**Why write "why this is here"?** Because that line is a small act of synthesis, repeated
hundreds of times — and it is the exact skill a citation is testing.

---

## Step 2 — Put it in git.

Not for collaboration. For **mercy**: a history means you can always get back, so you stop
being afraid to change things.

```bash
cd garden
git init
git add .
git commit -m "My garden, day one"
```

That is four commands and you now have a record of every version of your thinking. See
[docs/terminal-week.md](docs/terminal-week.md) for a walk-through written for someone who
has not used a terminal before — including what each command actually does, and what to do
when it goes wrong.

Our own argument for this is in
[Teaching change management and revision control](https://stimpunks.org/space/knowledge-system/):
*get your shit in git.* A commit history is a record of iterations, and a diff is how a
human supervises a machine.

---

## Step 3 — Let something else write the index.

Once you have more than a few dozen files, maintaining the index by hand stops being fun.
`garden/wiki/_generate.py` walks `raw/` and writes the index for you: a README plus one page
per shelf, every entry linking to the real file.

**Edit `garden/wiki/_config.json` first** — it is the only file you need to change. Set your
garden's name, and replace the three placeholder categories with your own shelves. Then:

```bash
cd garden
python3 wiki/_generate.py --no-concepts
```

Re-run it any time; it is safe and it overwrites. Anything whose filename matches no
keyword lands in **Unidentified**, which is not a bug — it is your to-do list for the files
whose names say nothing about what they are.

> **The index is disposable, the sources are not.** If the generated index is wrong, change
> the config and re-run. Never hand-edit the generated pages: your edits get overwritten,
> which is worse than being refused.

---

## Step 4 — Make it searchable.

A library you cannot search is half a library — and filenames are a terrible index of
meaning. [qmd](https://github.com/tobi/qmd) is a local search engine for folders of
Markdown: keyword search, meaning-based search, and a reranker, all running on your own
machine with no vendor and no network.

```bash
npm install -g @tobilu/qmd
cd garden
qmd collection add ./notes --name notes
qmd collection add ./wiki --name wiki
qmd embed                      # first run downloads models; takes a while
qmd query "what did I read about X"
```

The payoff is finding things by what they *mean*. "Why does being interrupted mid-task hurt
so much" finds writing about monotropism without either of you using that word.

Note that qmd reads **text**. PDFs in `raw/` are invisible to it unless you extract their
text first — see [docs/searching-pdfs.md](docs/searching-pdfs.md) for the honest version of
that problem.

---

## Step 5 — Concepts, if you have a vocabulary.

The Stimpunks system has a layer that indexes *ideas* rather than files: one page per
concept, gathering everything the whole garden holds about it. It works because it keys on a
**published glossary of 445 terms** that already existed.

**This is the one part of the pattern that does not travel on its own.** If you do not have
a controlled vocabulary, there is nothing for it to key on, and inventing one with a machine
is how you end up with a taxonomy nobody believes. It is deliberately left out of this
template. If you want it, that is a conversation, not a download.

---

## What this template is not

It is not an app, a product, or a thing that requires a subscription. It is folders, a
Python script, and a rule about not editing your own sources.

It also will not create capacity. It stops you wasting the capacity you have on finding
things you already had.

## Credit

The source-plus-index pattern comes from Andrej Karpathy's
[llm-wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f). Search is
[tobi/qmd](https://github.com/tobi/qmd). The access argument, and the insistence that
originals are never edited because we get cited, is ours —
[Stimpunks Foundation](https://stimpunks.org/).

Steal all of it.
