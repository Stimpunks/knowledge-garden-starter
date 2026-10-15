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

## The fix, in practice

From the top of your project:

```bash
python3 garden/wiki/_qmd_library.py
qmd collection add ./.qmd/library --name library    # once
```

It writes one Markdown file per original into `.qmd/library/`, titled with whatever you
recorded in `garden/wiki/_overrides.json`, with a `source:` line naming the original. PDFs need
`pdftotext` (`brew install poppler`). Epubs, Word files, Markdown and plain text need nothing.
After that, the `reindex` skill reruns it whenever the library changes.

> **If you followed an earlier version of this page, check what you made.** It gave a shell
> loop that saved `pdftotext` output as `.txt` files. qmd only indexes `**/*.md` by default, so
> that collection held **zero documents**, without an error, and every search over the library
> came back empty. That is the silent failure this whole page warns about, in the page's own
> recipe. Delete the `.txt` files and use the script.

**Two rules the script follows, and that you should follow if you build your own:**

1. **Put the original's path in the derived file.** When a search hit comes back, you need to
   know which real file it came from — and *that* is what you cite. Never cite the extracted
   copy.
2. **Treat the cache as disposable.** It is git-ignored, rebuildable, and never provenance.
   If it disappears, you lose nothing but time. (Keep it out of git for a second reason, too:
   on a public repository it would publish the full text of everything you hold.)

## The order matters, and getting it wrong does not error

Index rebuild, extraction, and re-embedding feed the search in that sequence. Run them out of
order and every step still reports success — you just get an index that is confidently
describing the wrong thing. Embed before extracting and the new PDFs simply are not there.

One command runs them in order, and checks the trap at the end — `qmd embed` **can exit 0 with
documents still unembedded**, so it reads the `Pending:` count in `qmd status` and goes again
until it reaches zero:

```bash
python3 .claude/skills/reindex/reindex.py
```

## The part people skip

**Not everything extracts, and you must say so out loud.**

In the Stimpunks library in August 2026, of 354 stored assets, 261 PDFs, epubs, and docs
yielded usable text. Around 86 yielded **nothing at all** — images, video, and cloud-document
pointers. A handful more produced so little text that indexing them was noise.

That is roughly a quarter of the library that search cannot see, and the temptation is to not
mention it. Do mention it. A tool that reports "268 assets searchable" alongside "86 yield no
text" is trustworthy. One that reports only the first number will eventually let you conclude
your garden is silent on something when it simply could not read the file.

So the script does not just print a count and move on. It writes `_UNSEARCHABLE.md` into the
library, listing every file it could not read, by its recorded title, grouped by reason. That
list is itself searchable — so a search for a book you hold but cannot read finds a page
saying *"we have this; search cannot see inside it; open the original,"* instead of silence.

### Scanned PDFs, and OCR

Scanned PDFs are the sharp edge here: they look like documents and extract as nothing,
because they are pictures of pages. OCR — reading the text off the picture — fixes most of
them:

```bash
brew install ocrmypdf
python3 garden/wiki/_qmd_library.py --ocr
```

It is slow, minutes per book, so it only runs when you ask for it. Each file's result is cached,
so you pay for it once. Two details that matter, both learned the hard way:

- **It tries gently first.** `--skip-text` OCRs only the pages with no text layer, so a PDF that
  is half real text never has its good half replaced by a worse reading. If that still comes
  back nearly empty, it forces OCR on every page. A publisher's *"Downloaded from…"* stamp is
  text, and it makes the gentle pass skip pages that are otherwise pure scan. On one 1957 paper
  the gentle pass recovered 410 characters and the forced pass 15,777.
- **Nothing is written to `raw/`.** The OCR'd PDF is thrown away; only the text is kept.

When the Stimpunks library added this in September 2026, it recovered nine substantial PDFs —
books and papers — that no search had ever been able to see. Among them was a 104-page ebook on
monotropism, the subject most central to the work, which had extracted as 104 characters and
came back as 33,581. Nothing had distinguished them from things the library did not hold at
all.

## Is it worth it?

If your library is small enough to remember, no. Filenames and a hand-written index are fine,
and step 1 of the [README](../README.md) is genuinely the whole system.

It becomes worth it at the point where you catch yourself unable to find something you know
you have. That is the signal — not a file count.
