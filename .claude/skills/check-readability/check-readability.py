#!/usr/bin/env python3
"""Audit the reading level and sentence length of any text — pasted, piped, or on disk.

A diagnostic, not a generator: it writes nothing and gates nothing. Give it text
on stdin, a `--text` string, a file, a glob, or a directory, and it reports an
approximate reading grade level and — the signal that actually matters — the
average words per sentence, plus the specific sentences that run long.

Originally written for Stimpunks Foundation, generalised here to take arbitrary input.
Same caveats either way: the grade-level formulas are rough, and on short samples they
are worse than rough. Trust the words-per-sentence count and the list of long
sentences — those are measurements. The grade numbers are estimates.

It exists to support a plain-language / Easy Read audit against ASAN's
"One Idea Per Line" standard (https://autisticadvocacy.org/resources/accessibility/easyread/).
Two caveats, both from that guide:
  - Reading-level formulas are only one lens and disagree with each other, which
    is why three are reported here. Sentence length (words per sentence) is the
    clearer, more actionable signal. ASAN aims for ~10-15 words per sentence,
    one idea per sentence. The Stimpunks Editorial Voice says the same thing:
    "One idea at a time. One main idea per sentence, often one idea per line."
  - No script can certify Easy Read. That needs a focus group of people with
    intellectual and developmental disabilities: "nothing about us, without us."

Markdown chrome is stripped before scoring, on the same reasoning Cavendish used
for lineage credits and glossary links: proper nouns and defined terms inflate the
grade without being the thing to fix, and ASAN pulls such terms out before checking
a score. Dropped: frontmatter, code, HTML, images, URLs, tables, footnotes, and
headings (fragments, not sentences — scoring them glues them onto the next
paragraph). Link and wikilink text is kept, its target dropped. Blockquotes are
skipped by default: they are usually someone else's words, not prose you can fix.
Use --include-quotes to score them, --strip-pattern to pull out anything else.

Nothing here is written to disk. Safe to point at raw/.

No third-party dependencies.

Usage, from the project root:
    pbpaste | python3 .claude/skills/check-readability/check-readability.py
    python3 .claude/skills/check-readability/check-readability.py --text "Some prose."
    python3 .claude/skills/check-readability/check-readability.py notes/Inbox/draft.md
    python3 .claude/skills/check-readability/check-readability.py wiki/learnings/
    python3 .claude/skills/check-readability/check-readability.py 'notes/**/*.md' --top 12
    python3 .claude/skills/check-readability/check-readability.py draft.md --sentences
    python3 .claude/skills/check-readability/check-readability.py draft.md --json
"""

from pathlib import Path
import argparse
import glob as globlib
import json
import os
import re
import statistics
import sys

TEXT_SUFFIXES = {".md", ".markdown", ".mdown", ".txt", ".text"}
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".obsidian"}

# ASAN targets, printed with every report.
EASY_READ_GRADE = (3, 5)
PLAIN_LANGUAGE_GRADE = (6, 8)
WPS_TARGET = (10, 15)

# Above this many words per sentence, the input almost certainly has no sentence
# punctuation at all — an auto-generated transcript, an OCR dump, a log. Its
# "grade level" is then an artifact of the missing periods, not of the writing,
# so it is reported separately instead of poisoning the averages.
UNPUNCTUATED_WPS = 60

# Readability formulas are unstable on small samples — a two-word note scores as
# postgraduate. The conventional floor is ~100 words. Shorter inputs are still
# measured and shown, but they are kept out of corpus averages and the
# worst-offenders ranking, where they would otherwise crowd out real problems.
MIN_WORDS = 100

# Deciding whether a line break ends a thought or just wraps one.
#
# Hard-wrapped prose (CLAUDE.md, wiki/learnings/) fills every line to a wrap
# column and breaks mid-sentence, so its lines must be rejoined. One-idea-per-
# line writing — which is exactly what ASAN asks for, and how Ryan often writes
# — breaks at each idea, with no terminal period, so rejoining it would read a
# whole section as one enormous sentence and score the best-formed text worst.
# Telling them apart: in wrapped text a continuing line is *full*, within a few
# characters of the longest line in the file. A line well short of that is a
# deliberate break. JOIN_MIN keeps short-lined files from ever being rejoined.
JOIN_SLACK = 12
JOIN_MIN = 55
_CONTINUES = re.compile(r"[,;:—–-]$")

_WORD = re.compile(r"[A-Za-z][A-Za-z'’-]*")
_MASK = "\x00"  # stands in for a period that does not end a sentence

# Periods that are not sentence ends. Case-sensitive on purpose: a lowercase
# "no." or "st." at the end of a real sentence is far more common than the
# abbreviation, so those are left out entirely.
_ABBREV = re.compile(
    r"\b(?:e\.g|i\.e|etc|vs|cf|approx|et\sal|al|Dr|Mr|Mrs|Ms|Prof|Rev|Sr|Jr"
    r"|Inc|Ltd|Fig|Vol|Ch|Ed|Eds|pp|Ph\.D|M\.D|U\.S|U\.K|a\.m|p\.m)\."
)
_INITIAL = re.compile(r"\b[A-Z]\.")
_DECIMAL = re.compile(r"(?<=\d)\.(?=\d)")
_ELLIPSIS = re.compile(r"\.\.\.|…")

# End of sentence: terminal punctuation, optional closers, whitespace, then
# something that is not a lowercase letter (which would signal a false split).
_SENT_END = re.compile(r'(?<=[.!?])["”’\')\]]*\s+(?=[^a-z\s])')

_LIST_ITEM = re.compile(r"^\s{0,6}(?:[-*+]|\d+[.)])\s+")
_TASK_BOX = re.compile(r"^\[[ xX]\]\s+")
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s")
_SETEXT = re.compile(r"^\s{0,3}(?:=+|-+)\s*$")
_HRULE = re.compile(r"^\s{0,3}(?:(?:[-*_]\s*){3,})$")
_TABLE = re.compile(r"^\s{0,3}\|")
_FOOTNOTE_DEF = re.compile(r"^\s{0,3}\[\^[^\]]+\]:")
_LINKREF_DEF = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*\S+")
_QUOTE = re.compile(r"^\s{0,3}>+\s?")
_TAGS_ONLY = re.compile(r"^\s{0,3}(?:#[\w/-]+[ \t]*)+$")  # a bare #tag line is metadata


# ---------------------------------------------------------------- text prep

def strip_markdown(raw, include_quotes=False, extra_strips=()):
    """Reduce Markdown to a list of prose units.

    A "unit" is a run of text with a hard boundary at each end — a paragraph, a
    list item, a table-free block. Units matter because a bullet that ends
    without a period must not glue itself onto the next bullet and read as one
    enormous sentence.
    """
    text = raw.replace("\r\n", "\n")

    text = re.sub(r"\A---\n.*?\n(?:---|\.\.\.)\n", "", text, flags=re.S)  # frontmatter
    text = re.sub(r"^[ \t]*(`{3,}|~{3,})[^\n]*\n.*?(?:^[ \t]*\1[^\n]*$|\Z)", "",
                  text, flags=re.S | re.M)                                # fenced code
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)                    # html comments
    text = re.sub(r"`[^`\n]*`", " ", text)                                # inline code
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)                      # images
    text = re.sub(r"!\[\[[^\]]*\]\]", "", text)                           # wiki images

    for pattern in extra_strips:
        text = re.sub(pattern, "", text, flags=re.S | re.M)

    # Keep what a reader reads; drop what they don't.
    text = re.sub(r"\[\[([^\]|]*)\|([^\]]*)\]\]", r"\2", text)            # [[target|text]]
    text = re.sub(r"\[\[([^\]]*)\]\]", r"\1", text)                       # [[text]]
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)                  # [text](url)
    text = re.sub(r"\[([^\]]*)\]\[[^\]]*\]", r"\1", text)                 # [text][ref]
    text = re.sub(r"\[\^[^\]]*\]", "", text)                              # footnote refs
    text = re.sub(r"<https?://[^>]*>", "", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"<[^>\n]{1,200}>", "", text)                           # html tags
    text = re.sub(r"\(\s*\)|\[\s*\]", "", text)                           # emptied brackets
    text = re.sub(r"~~|\*+", "", text)                                    # emphasis
    text = re.sub(r"(?<![A-Za-z0-9])_+|_+(?![A-Za-z0-9])", "", text)      # underscores

    # Pass one: keep only prose lines, remembering which ones start a new block.
    kept = []  # (text, starts_block)
    for line in text.split("\n"):
        if not line.strip():
            kept.append((None, True))  # blank: hard boundary
            continue
        if (_HEADING.match(line) or _SETEXT.match(line) or _HRULE.match(line)
                or _TABLE.match(line) or _FOOTNOTE_DEF.match(line)
                or _LINKREF_DEF.match(line) or _TAGS_ONLY.match(line)):
            kept.append((None, True))
            continue
        if _QUOTE.match(line):
            if not include_quotes:
                kept.append((None, True))
                continue
            line = _QUOTE.sub("", line)
            if not line.strip():
                kept.append((None, True))
                continue
        starts = False
        if _LIST_ITEM.match(line):
            starts = True
            line = _TASK_BOX.sub("", _LIST_ITEM.sub("", line))
        kept.append((line.strip(), starts))

    # Pass two: the file's own wrap column, measured from its longest prose line.
    widths = [len(t) for t, _ in kept if t]
    join_at = max(JOIN_MIN, max(widths) - JOIN_SLACK) if widths else JOIN_MIN

    units, current = [], []

    def flush():
        if current:
            joined = " ".join(current).strip()
            if joined:
                units.append(joined)
            current.clear()

    for line, starts in kept:
        if line is None or starts:
            flush()
            if line is None:
                continue
        elif current:
            previous = current[-1]
            if len(previous) < join_at and not _CONTINUES.search(previous):
                flush()  # a deliberate line break, not a wrap
        current.append(line)
    flush()

    return units


def sentences_in(unit):
    """Split one prose unit into sentences, guarding abbreviations and decimals."""
    masked = _ELLIPSIS.sub(_MASK * 3, unit)
    masked = _DECIMAL.sub(_MASK, masked)
    masked = _ABBREV.sub(lambda m: m.group(0).replace(".", _MASK), masked)
    masked = _INITIAL.sub(lambda m: m.group(0).replace(".", _MASK), masked)
    parts = _SENT_END.split(masked)
    out = []
    for part in parts:
        s = part.replace(_MASK, ".").strip()
        if s and _WORD.search(s):
            out.append(s)
    return out


def sentences_of(raw, include_quotes=False, extra_strips=()):
    out = []
    for unit in strip_markdown(raw, include_quotes, extra_strips):
        out.extend(sentences_in(unit))
    return out


# ---------------------------------------------------------------- measuring

def syllables(word):
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    n = len(re.findall(r"[aeiouy]+", w))
    # Silent trailing e, unless it is the vowel of a final consonant+le ("table").
    if w.endswith("e") and not re.search(r"[^aeiou]le$", w) and n > 1:
        n -= 1
    if w.endswith("ed") and re.search(r"[^aeioudt]ed$", w) and n > 1:
        n -= 1  # "walked" is one syllable, "wanted" is two
    return max(1, n)


def is_complex(word):
    """Gunning Fog's 'complex word': 3+ syllables, ignoring common inflections."""
    if syllables(word) < 3:
        return False
    lower = word.lower()
    for suffix in ("es", "ed", "ing"):
        if lower.endswith(suffix) and syllables(lower[: -len(suffix)]) < 3:
            return False
    return True


def measure(sents, max_words):
    words_per = [_WORD.findall(s) for s in sents]
    flat = [w for ws in words_per for w in ws]
    if not sents or not flat:
        return None

    W, S = len(flat), len(sents)
    Sy = sum(syllables(w) for w in flat)
    C = sum(1 for w in flat if is_complex(w))
    wps, spw = W / S, Sy / W

    long_pairs = sorted(
        ((len(ws), s) for ws, s in zip(words_per, sents) if len(ws) > max_words),
        key=lambda p: -p[0],
    )
    return {
        "words": W,
        "sentences": S,
        "wps": wps,
        "fk_grade": 0.39 * wps + 11.8 * spw - 15.59,
        "fog": 0.4 * (wps + 100 * (C / W)),
        "ease": 206.835 - 1.015 * wps - 84.6 * spw,
        "complex_pct": 100 * C / W,
        "longest": max(len(ws) for ws in words_per),
        "long_sentences": len(long_pairs),
        "long_pct": 100 * len(long_pairs) / S,
        "offenders": long_pairs,
    }


def grades_of(m):
    return (m["fk_grade"], m["fog"])


def headline_grade(m):
    """The number to sort and summarize by: mean of the two grade formulas."""
    return statistics.mean(grades_of(m))


# ---------------------------------------------------------------- inputs

def expand(arg):
    """Turn one CLI argument into file paths: literal, glob, or directory walk."""
    p = Path(arg)
    if p.is_dir():
        found = []
        for root, dirs, files in os.walk(p):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
            for f in sorted(files):
                if Path(f).suffix.lower() in TEXT_SUFFIXES:
                    found.append(Path(root) / f)
        return sorted(found)
    if p.is_file():
        return [p]
    hits = [Path(h) for h in sorted(globlib.glob(arg, recursive=True))]
    return [h for h in hits if h.is_file()]


def load_inputs(args, stdin_text):
    """Return [(label, group, text)] — group is the folder, used for the summary table."""
    inputs = []
    if args.text:
        inputs.append(("--text", "(inline)", args.text))
    if stdin_text and stdin_text.strip():
        inputs.append(("(stdin)", "(pasted)", stdin_text))

    missing = []
    for arg in args.paths:
        if arg == "-":
            continue
        paths = expand(arg)
        if not paths:
            missing.append(arg)
        for path in paths:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                missing.append(f"{arg} ({exc.strerror})")
                continue
            try:
                label = str(path.relative_to(Path.cwd()))
            except ValueError:
                label = str(path)
            parent = path.parent.name or "."
            inputs.append((label, parent, text))
    return inputs, missing


# ---------------------------------------------------------------- reporting

def clip(s, width=96):
    s = " ".join(s.split())
    return s if len(s) <= width else s[: width - 1] + "…"


def print_targets():
    print(f"Targets (ASAN Easy Read): grade {EASY_READ_GRADE[0]}-{EASY_READ_GRADE[1]}; "
          f"plain language grade {PLAIN_LANGUAGE_GRADE[0]}-{PLAIN_LANGUAGE_GRADE[1]}; "
          f"{WPS_TARGET[0]}-{WPS_TARGET[1]} words per sentence, one idea each.")


def print_offenders(m, max_words, limit):
    if not m["offenders"]:
        print(f"  No sentence runs over {max_words} words.")
        return
    shown = m["offenders"][:limit]
    print(f"  Sentences over {max_words} words "
          f"({m['long_sentences']} of {m['sentences']}, showing {len(shown)}):")
    for n, s in shown:
        print(f"    {n:3d}w  {clip(s)}")


def warn_unpunctuated(rows):
    print(f"\nNot scored — no sentence punctuation found "
          f"(over {UNPUNCTUATED_WPS} words per apparent sentence). Likely a "
          f"transcript, OCR dump, or log; a grade level here would measure the "
          f"missing periods, not the writing. Use --include-unpunctuated to force it:")
    for label, _, m in rows[:8]:
        print(f"  {m['wps']:7.0f} w/s  {clip(label, 70)}")
    if len(rows) > 8:
        print(f"  ...and {len(rows) - 8} more")


def report_single(label, m, args):
    print(f"{label}\n")
    print(f"  words {m['words']}   sentences {m['sentences']}   "
          f"mean words/sentence {m['wps']:.1f}   longest {m['longest']}w")
    print(f"  Flesch-Kincaid grade {m['fk_grade']:.1f}   "
          f"Gunning Fog {m['fog']:.1f}   reading ease {m['ease']:.0f}/100   "
          f"3+ syllable words {m['complex_pct']:.0f}%")
    print(f"  Over {args.max_words} words: {m['long_sentences']} sentences "
          f"({m['long_pct']:.0f}%)\n")
    print_targets()
    print()
    print_offenders(m, args.max_words, args.top)


def report_many(rows, args):
    by_group = {}
    for _, group, m in rows:
        by_group.setdefault(group, []).append(m)

    print(f"{'folder':32}{'files':>7}{'grade':>8}{'words/sent':>12}{'long sents':>12}")
    for group in sorted(by_group):
        ms = by_group[group]
        print(f"{clip(group, 31):32}{len(ms):>7}"
              f"{statistics.mean(headline_grade(m) for m in ms):>8.1f}"
              f"{statistics.mean(m['wps'] for m in ms):>12.1f}"
              f"{sum(m['long_sentences'] for m in ms):>12d}")

    all_m = [m for _, _, m in rows]
    total_long = sum(m["long_sentences"] for m in all_m)
    total_sents = sum(m["sentences"] for m in all_m)
    with_long = sum(1 for m in all_m if m["long_sentences"])
    print(f"\nOVERALL: {len(rows)} files | mean grade "
          f"{statistics.mean(headline_grade(m) for m in all_m):.1f} "
          f"| mean words/sentence {statistics.mean(m['wps'] for m in all_m):.1f}")
    print(f"Sentences over {args.max_words} words: {total_long} / {total_sents} "
          f"| files containing one: {with_long} / {len(rows)}")
    print_targets()

    hardest = sorted(rows, key=lambda r: -headline_grade(r[2]))[: args.top]
    print(f"\nHardest {len(hardest)} to work on first (by grade level):")
    for label, _, m in hardest:
        print(f"  grade {headline_grade(m):5.1f}  {m['wps']:5.1f} w/s  "
              f"{clip(label, 60)}  (longest {m['longest']}w)")

    if args.sentences:
        print(f"\nLong sentences, worst files first:")
        for label, _, m in hardest:
            if m["offenders"]:
                print(f"\n{label}")
                print_offenders(m, args.max_words, args.top)


def to_json(rows, short, unpunctuated, args):
    def entry(label, group, m):
        d = {k: v for k, v in m.items() if k != "offenders"}
        d["label"] = label
        d["group"] = group
        d["grade"] = headline_grade(m)
        d["long_sentence_list"] = [{"words": n, "text": s} for n, s in m["offenders"]]
        return d

    out = [entry(*r) for r in rows]
    all_m = [m for _, _, m in rows] or [{"wps": 0, "words": 0, "sentences": 0,
                                         "long_sentences": 0, "fk_grade": 0, "fog": 0}]
    return {
        "max_words": args.max_words,
        "min_words_for_grade": MIN_WORDS,
        "files": out,
        "too_short": [entry(*r) for r in short],
        "unpunctuated": [entry(*r) for r in unpunctuated],
        "overall": {
            "inputs": len(rows),
            "grade": statistics.mean(headline_grade(m) for m in all_m),
            "wps": statistics.mean(m["wps"] for m in all_m),
            "words": sum(m["words"] for m in all_m),
            "sentences": sum(m["sentences"] for m in all_m),
            "long_sentences": sum(m["long_sentences"] for m in all_m),
        },
        "targets": {
            "easy_read_grade": list(EASY_READ_GRADE),
            "plain_language_grade": list(PLAIN_LANGUAGE_GRADE),
            "words_per_sentence": list(WPS_TARGET),
        },
        "caveat": "Formulas are one lens only. No script can certify Easy Read — "
                  "that needs a focus group of people with intellectual and "
                  "developmental disabilities. Nothing about us, without us.",
    }


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(
        description="Readability and sentence-length audit for pasted text or files.",
        epilog="With no paths and no --text, reads stdin. Writes nothing, ever.",
    )
    ap.add_argument("paths", nargs="*",
                    help="files, directories, or globs (default: read stdin)")
    ap.add_argument("--text", help="score this string directly")
    ap.add_argument("--max-words", type=int, default=WPS_TARGET[1],
                    help=f"flag sentences longer than this (default {WPS_TARGET[1]})")
    ap.add_argument("--top", type=int, default=8,
                    help="how many hardest files / long sentences to list (default 8)")
    ap.add_argument("--sentences", action="store_true",
                    help="with many files, also dump long sentences from the hardest")
    ap.add_argument("--include-quotes", action="store_true",
                    help="score blockquotes too (skipped by default: others' words)")
    ap.add_argument("--include-unpunctuated", action="store_true",
                    help="score transcripts and other text lacking sentence punctuation")
    ap.add_argument("--strip-pattern", action="append", default=[], metavar="REGEX",
                    help="drop text matching this before scoring (repeatable)")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of a report")
    args = ap.parse_args()

    # Read stdin only when it is actually the input: named explicitly as "-", or
    # implied because nothing else was given. Checking isatty() alone would hang
    # `--text ...` forever whenever stdin is a pipe that nobody is writing to.
    stdin_text = ""
    wants_stdin = "-" in args.paths or (not args.paths and not args.text)
    if wants_stdin and not sys.stdin.isatty():
        stdin_text = sys.stdin.read()

    inputs, missing = load_inputs(args, stdin_text)
    for m in missing:
        print(f"warning: no readable text files matched {m!r}", file=sys.stderr)
    if not inputs:
        ap.print_usage(sys.stderr)
        sys.exit("nothing to read: pipe text in, pass --text, or name a file.")

    rows, short, unpunctuated, empty = [], [], [], []
    for label, group, text in inputs:
        sents = sentences_of(text, args.include_quotes, args.strip_pattern)
        m = measure(sents, args.max_words)
        if not m:
            empty.append(label)
        elif m["wps"] > UNPUNCTUATED_WPS and not args.include_unpunctuated:
            unpunctuated.append((label, group, m))
        elif m["words"] < MIN_WORDS:
            short.append((label, group, m))
        else:
            rows.append((label, group, m))
    for label in empty:
        print(f"note: no scorable prose in {label}", file=sys.stderr)

    # Never let a guard swallow the only thing asked about. With one input there
    # is no average to protect, so score it and say plainly what the caveat is.
    caveat = ""
    if not rows and len(inputs) == 1:
        if unpunctuated:
            rows, unpunctuated = unpunctuated, []
            caveat = ("This text has no sentence punctuation. The numbers below "
                      "measure the missing periods, not the writing.")
        elif short:
            rows, short = short, []
            caveat = (f"Under {MIN_WORDS} words. Grade levels are unreliable on "
                      f"samples this small — trust the words-per-sentence count "
                      f"and the long sentences, not the grade.")

    if not rows and not short and not unpunctuated:
        sys.exit("No prose found to measure.")

    if args.json:
        print(json.dumps(to_json(rows, short, unpunctuated, args), indent=2))
        return
    if caveat:
        print(f"note: {caveat}\n")
    if rows and len(rows) == 1 and not short:
        report_single(rows[0][0], rows[0][2], args)
    elif rows:
        report_many(rows, args)
    if short:
        print(f"\nToo short to grade reliably (under {MIN_WORDS} words), "
              f"left out of the averages above: {len(short)} "
              f"{'input' if len(short) == 1 else 'inputs'}.")
    if unpunctuated:
        warn_unpunctuated(unpunctuated)


if __name__ == "__main__":
    main()
