# Searching a library that is mostly PDFs

The honest version of a problem you will hit as soon as your garden gets useful.

## The problem

Search tools read text. Most research libraries are PDFs, epubs, and images. So the corpus
you most want to search is the one your search tool cannot see.

It is worse than it sounds, because the failure is silent and asymmetric. A paper saved as
`40614_2022_Article_338.pdf` is not just hard to find — it is invisible. It will never appear
in any result, and nothing will tell you it was skipped. Your search looks like it worked.

## The fix, in principle

Extract the text once, cache it, and point your search tool at the cache instead of the
binaries. The original stays untouched in `raw/`; the extracted text is a **derived** thing
that lives elsewhere and can be thrown away and rebuilt.

On a Mac, `pdftotext` (from `brew install poppler`) does the extraction. Roughly:

```bash
mkdir -p garden/.qmd/library
for f in garden/raw/*.pdf; do
  pdftotext -q "$f" "garden/.qmd/library/$(basename "$f").txt"
done
```

Then point your search tool at `garden/.qmd/library` as well as your notes.

**Two rules if you build this:**

1. **Put the original's path in the derived file**, as a first line or frontmatter. When a
   search hit comes back, you need to know which real file it came from — and *that* is what
   you cite. Never cite the extracted copy.
2. **Treat the cache as disposable.** It is git-ignored, rebuildable, and never provenance.
   If it disappears, you lose nothing but time.

## The order matters, and getting it wrong does not error

Extraction, index rebuild, and re-embedding feed each other in that sequence. Run them out
of order and every step still reports success — you just get an index that is confidently
describing the wrong thing:

```bash
pdftotext …                              # 1. extract, so there is text to read
python3 wiki/_generate.py --no-concepts  # 2. rebuild the index over it
qmd update && qmd embed                  # 3. re-index and embed, last
```

Embed before extracting and the new PDFs simply are not there. Also note that `qmd embed`
**can exit 0 with documents still unembedded** — check for a `Pending:` line in `qmd status`
and re-run until it is gone. Both traps are in
[README Step 4](../README.md#step-4--make-it-searchable).

## The part people skip

**Not everything extracts, and you must say so out loud.**

In the Stimpunks library, of 354 stored assets: 261 PDFs, epubs, and docs yield usable text.
Around 86 yield **nothing at all** — images, video, and cloud-document pointers. A handful
more produce so little text that indexing them is noise.

That is roughly a quarter of the library that search cannot see, and the temptation is to not
mention it. Do mention it. A tool that reports "268 assets searchable" alongside "86 yield no
text" is trustworthy. One that reports only the first number will eventually let you conclude
your garden is silent on something when it simply could not read the file.

Scanned PDFs are the sharp edge here: they look like documents and extract as nothing,
because they are pictures of pages. OCR is the answer, and it is a bigger project than this
document.

## Is it worth it?

If your library is small enough to remember, no. Filenames and a hand-written index are fine,
and step 1 of the [README](../README.md) is genuinely the whole system.

It becomes worth it at the point where you catch yourself unable to find something you know
you have. That is the signal — not a file count.
