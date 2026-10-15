---
name: check-readability
description: Audit the reading level and sentence length of any text — pasted, piped, or a file/folder/glob in this garden — against ASAN's Easy Read and plain-language targets, then say what to shorten. Use when the user says "/check-readability", "check the readability", "how readable is this", "run a plain language check", "is this Easy Read", or hands over a draft and asks how hard it is to read.
---

# check-readability

A **diagnostic, not a gate.** It reports how hard a piece of writing is to read and points at
the specific sentences to fix. It writes nothing, changes nothing, and blocks nothing.

Adapted from a script Stimpunks Foundation wrote to audit one fixed set of cards. This one
takes whatever the user gives it: pasted text, a file, a folder, a glob.

`check-readability.py` does the counting. **You do the judgment** — reading the numbers,
deciding whether they matter for this piece, and offering rewrites.

## The two caveats — say them, don't bury them

Both come from ASAN's [Easy Read guide](https://autisticadvocacy.org/resources/accessibility/easyread/),
and they are the reason this skill exists in this form:

1. **Reading-level formulas are one lens and they disagree with each other.** The script prints
   three on purpose. **Words per sentence is the clearer, more actionable signal** — that's the
   number to lead with. ASAN aims for **10–15 words per sentence, one idea per sentence** — one
   idea at a time, one main idea per sentence, often one idea per line. If your garden has a
   house style file of its own, hold the text to that too.
2. **No script can certify Easy Read.** That takes a focus group of people with intellectual and
   developmental disabilities. *Nothing about us, without us.* Never report a passing score as if
   the text has been cleared — say what was measured and what wasn't.

Never present a grade level as a verdict. A grade of 9 on a piece written for a policy audience
may be fine; a grade of 9 on a Resources page for the community is a problem. Judge against who
it's for.

## Running it

```bash
python3 .claude/skills/check-readability/check-readability.py [inputs] [options]
```

Inputs — any mix, and it's safe to point at `raw/` since nothing is ever written:

| Input | Command |
|---|---|
| Pasted text | `pbpaste \| python3 .../check-readability.py` |
| Text the user gave you in chat | `--text "…"` (or write it to the scratchpad and pass the path) |
| One file | `garden/notes/Inbox/draft.md` |
| A folder | `garden/notes/` |
| A glob | `'garden/notes/**/*.md'` (quote it — let Python expand it) |

Options: `--max-words N` (long-sentence threshold, default 15) · `--top N` (how many to list,
default 8) · `--sentences` (dump long sentences for the worst files in a multi-file run) ·
`--include-quotes` (blockquotes are skipped by default — usually someone else's words, not ours
to fix) · `--strip-pattern REGEX` (repeatable; pull out credits, defined terms, or boilerplate
before scoring, the way ASAN pulls defined terms out before checking a score) ·
`--include-unpunctuated` · `--json`.

If the user pasted the text into chat rather than the clipboard, write it to a scratchpad file and
pass that path — it avoids shell-quoting mangling their punctuation.

## Reading the output

Single input → full metrics plus every long sentence, worst first. Many inputs → a per-folder
table, an overall line, and the hardest files to work on first.

Lead with **words per sentence** and **the long-sentence list**, because those are the ones the user
can act on. Report the grade as a range across the three formulas, not a single authoritative
number.

Three buckets get held out of the averages, and each is reported rather than hidden:
- **Too short to grade** (under 100 words) — formulas are unstable on small samples. A single
  short input is still scored, with the caveat attached.
- **No sentence punctuation** (auto-transcripts, OCR dumps) — a grade there measures missing
  periods, not writing.
- **No scorable prose** — noted on stderr.

## What gets stripped before scoring, and why

Frontmatter, code, HTML, images, URLs, tables, footnotes, tag-only lines, and **headings**
(fragments, not sentences — scoring them glues them onto the next paragraph). Link and wikilink
text is kept, the target dropped. Proper nouns and defined terms inflate a grade without being
the thing to fix.

The script decides per file whether a line break ends a thought or just wraps one, so
**one-idea-per-line writing is scored as one idea per line** — not as a single enormous sentence.
That matters here: it's the format ASAN asks for and the one the user often writes in.

## Then do the useful part

Numbers alone aren't the deliverable. After the run:

1. **Name the top 3–5 sentences to fix**, quoting each with its word count.
2. **Offer a rewrite** for the worst ones — split at the joints, one idea per sentence. Keep
   the writer's own voice, and any house style the garden has written down (Stimpunks', for
   one, uses identity-first language and capitalizes **Autistic** and **Disabled**).
   Plainspoken, not dumbed down: *don't flatten the idea, clear the fog away.*
3. **Say what a score can't tell the user** — whether the words are the right words, whether the
   structure supports re-entry, whether it needs an Easy Read version reviewed by the people it's
   for.

Don't rewrite the file unless the user asks. If they do, and it lives in `garden/notes/`, edit in place;
otherwise follow the usual rules for that folder (`raw/` is never edited).
