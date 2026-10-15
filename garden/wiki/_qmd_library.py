#!/usr/bin/env python3
"""Make raw/ searchable: extract the text of every stored file into `.qmd/library/`.

Search tools read text, and most of a research library is PDFs, epubs and Word files. This
writes one Markdown file per stored original, carrying the human title you recorded in
`wiki/_overrides.json` and a `source:` line pointing back at the original — which is what you
cite, never the extracted copy.

    python3 garden/wiki/_qmd_library.py          # from the top of your project
    python3 garden/wiki/_qmd_library.py --ocr    # also OCR scanned PDFs (slow, opt-in)

Then add `.qmd/library` to qmd once (README Step 4), and `qmd update && qmd embed`.
The `reindex` skill runs all of it in the right order.

WHY MARKDOWN AND NOT .txt. qmd indexes `**/*.md` by default. An earlier version of this
template's docs wrote `pdftotext` output as `.txt`, and qmd indexed zero of them — no error,
no warning, every search over the library silently empty. That is the exact failure this
whole layer exists to prevent, so the format is not a style choice.

RULES THIS OBEYS
  - raw/ is read-only. Nothing here writes to it, links to it, or modifies it.
  - `.qmd/library/` is derived, git-ignored and rebuildable — never provenance, never cited.
  - Files that yield no text are COUNTED OUT LOUD and listed in `_UNSEARCHABLE.md`, which is
    itself indexed. A search for the title of a scan nothing can read then finds that list
    saying so, instead of returning silence — which would read as "I don't have it".
  - A missing extractor is reported as a missing extractor, never as "this PDF is empty".

Needs `pdftotext` for PDFs (macOS: `brew install poppler`). `--ocr` also needs `ocrmypdf`
(`brew install ocrmypdf`). Epub, docx, Markdown and plain text need nothing extra.
"""
import argparse
import gzip
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import zipfile

GARDEN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT = os.path.dirname(GARDEN)
RAW = os.path.join(GARDEN, "raw")
OVERRIDES = os.path.join(GARDEN, "wiki", "_overrides.json")
OUT = os.path.join(PROJECT, ".qmd", "library")
CACHE = os.path.join(PROJECT, ".qmd", "_textcache.json.gz")

SKIP = {".DS_Store", "README.md", "readme.md"}
EXTRACT_LIMIT = 20_000_000      # a safety valve, not a policy — a hit on it is reported
MIN_CHARS = 400                 # below this it is a cover page or an OCR burp, not a document
MIN_CHARS_PER_PAGE = 200        # a real text layer runs ~1,500-3,000 characters per page
OCR_THIN_CHARS = 2_000          # below this, a PDF is probably a scan with no text layer
OCR_TIMEOUT = 3_600             # a large scanned book can genuinely take this long
EXTRACTOR_V = 1                 # bump when extraction changes, so cached text is redone
OCR_V = 1
MANIFEST = "_UNSEARCHABLE.md"


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def have(tool):
    return subprocess.run(["which", tool], capture_output=True).returncode == 0


def extract(path):
    """(text, problem). Read-only. `problem` is set only when a TOOL is missing — a file
    that genuinely holds no text returns ("", "")."""
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    try:
        if ext == "pdf":
            if not have("pdftotext"):
                return "", "pdftotext not installed"
            r = subprocess.run(["pdftotext", "-q", "-enc", "UTF-8", path, "-"],
                               capture_output=True, timeout=300)
            return r.stdout.decode("utf-8", "replace")[:EXTRACT_LIMIT], ""
        if ext in ("md", "markdown", "txt", "csv", "html", "htm"):
            with open(path, encoding="utf-8", errors="replace") as fh:
                return fh.read()[:EXTRACT_LIMIT], ""
        if ext in ("epub", "docx"):
            buf = []
            with zipfile.ZipFile(path) as z:
                for n in sorted(z.namelist()):
                    if not n.endswith((".xhtml", ".html", ".htm", ".xml")):
                        continue
                    buf.append(re.sub(r"<[^>]+>", " ", z.read(n).decode("utf-8", "replace")))
                    if sum(map(len, buf)) > EXTRACT_LIMIT:
                        break
            return " ".join(buf)[:EXTRACT_LIMIT], ""
    except Exception:
        return "", ""
    return "", ""


def ocr(path, force=False):
    """(text, error). Read-only: the OCR'd PDF goes to stdout and is thrown away; only the
    text sidecar is kept. raw/ is never written to.

    Two modes, tried in this order. `--skip-text` keeps any text layer a page already has
    and only OCRs the image pages, so a good layer is never replaced by a worse reading of
    itself. But it skips a page with ANY text on it — and a publisher's "Downloaded from…"
    stamp is text. Upstream, a fully scanned 1957 paper with one stamped line per page came
    back as 410 characters under --skip-text and 15,777 under --force-ocr. So: politely
    first, forcefully only if the result is still unreadable, keep whichever is longer."""
    fd, side = tempfile.mkstemp(suffix=".txt")
    os.close(fd)
    try:
        r = subprocess.run(
            ["ocrmypdf", "--force-ocr" if force else "--skip-text", "--optimize", "0",
             "--quiet", "--sidecar", side, path, "-"],
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=OCR_TIMEOUT)
        if r.returncode != 0:
            err = r.stderr.decode("utf-8", "replace").strip().splitlines()
            return "", (err[-1][:120] if err else f"exit {r.returncode}")
        with open(side, encoding="utf-8", errors="replace") as fh:
            return fh.read()[:EXTRACT_LIMIT], ""
    except FileNotFoundError:
        return "", "ocrmypdf not installed"
    except subprocess.TimeoutExpired:
        return "", f"timed out after {OCR_TIMEOUT}s"
    finally:
        try:
            os.unlink(side)
        except OSError:
            pass


def page_count(path):
    if not path.lower().endswith(".pdf") or not have("pdfinfo"):
        return None
    try:
        out = subprocess.run(["pdfinfo", path], capture_output=True,
                             timeout=30).stdout.decode("utf-8", "replace")
        m = re.search(r"^Pages:\s+(\d+)", out, re.M)
        return int(m.group(1)) if m else None
    except Exception:
        return None


def clean(text):
    text = text.replace("\f", "\n\n").replace("­", "")   # page breaks, soft hyphens
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def why_blind(name, problem):
    if problem and "not installed" in problem:
        return problem + " — install it and re-run; this file may be perfectly readable"
    if problem:
        return problem
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext in ("png", "jpg", "jpeg", "webp", "gif", "heic"):
        return "an image — no text to extract"
    if ext in ("mp4", "m4a", "mov", "mp3", "wav"):
        return "audio or video — not transcribed"
    if ext in ("gdoc", "gsheet", "gslides"):
        return "a cloud-document pointer, not a document"
    if ext == "pdf":
        return "a PDF with no text layer (a scan) — `--ocr` may recover it"
    return "no extractor here reads this format"


def write_if_changed(path, body):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            if fh.read() == body:
                return False
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(body)
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ocr", action="store_true",
                    help="OCR PDFs that extract as (nearly) empty. SLOW — minutes per book — "
                         "and cached, so each file is paid for once.")
    ap.add_argument("--ocr-retry", action="store_true",
                    help="with --ocr, also retry files whose OCR failed last time")
    a = ap.parse_args()

    if not os.path.isdir(RAW):
        sys.exit(f"ERROR: no {RAW} — run this from inside a garden made from the template.")

    names = sorted([f for f in os.listdir(RAW) if f not in SKIP
                    and not os.path.isdir(os.path.join(RAW, f))], key=str.lower)
    overrides = load_json(OVERRIDES, {})
    cache = {}
    if os.path.exists(CACHE):
        try:
            with gzip.open(CACHE, "rt", encoding="utf-8") as fh:
                cache = json.load(fh)
        except Exception:
            cache = {}

    texts, problems, extracted = {}, {}, 0
    for name in names:
        p = os.path.join(RAW, name)
        try:
            st = os.stat(p)
        except OSError:
            texts[name], problems[name] = "", "a broken link — the file it points at is gone"
            continue
        fp = f"{st.st_size}:{int(st.st_mtime)}:v{EXTRACTOR_V}"
        ent = cache.get(name) or {}
        if ent.get("fp") == fp and not ent.get("problem"):
            texts[name] = ent.get("text", "")
            continue
        txt, prob = extract(p)
        texts[name] = txt
        if prob:
            problems[name] = prob
        # A fresh entry, not a merge: if the file changed, an old OCR verdict no longer applies.
        cache[name] = {"fp": fp, "text": txt, "problem": prob}
        extracted += 1

    # OCR: opt-in, because it is minutes per book and nobody wants a 40-minute surprise.
    # "Thin" is judged per PAGE where the page count is known: a two-page handout with 1,500
    # characters is a real document, and calling it a scan would be a false alarm.
    def is_thin(n):
        t = clean(texts.get(n, ""))
        pages = page_count(os.path.join(RAW, n))
        return (len(t) / pages < MIN_CHARS_PER_PAGE) if pages else len(t) < OCR_THIN_CHARS

    thin = [n for n in names if n.lower().endswith(".pdf") and n not in problems and is_thin(n)]
    if a.ocr and thin:
        todo = [n for n in thin
                if (cache.get(n) or {}).get("ocr_v") != OCR_V
                or (a.ocr_retry and (cache.get(n) or {}).get("ocr") != "ok")]
        skipped = len(thin) - len(todo)
        if skipped:
            print(f"  · OCR: {skipped} scan(s) already tried — --ocr-retry to retry failures")
        for i, n in enumerate(todo, 1):
            path = os.path.join(RAW, n)
            print(f"  · OCR {i}/{len(todo)}  {os.path.getsize(path) / 1e6:6.1f} MB  {n[:60]}",
                  flush=True)
            t0 = time.time()
            txt, err = ocr(path)
            pages = page_count(path) or 1
            if not err and len(clean(txt)) / pages < MIN_CHARS_PER_PAGE:
                t2, e2 = ocr(path, force=True)
                if not e2 and len(t2) > len(txt):
                    txt = t2
            if err:
                print(f"      ! {err}")
                cache.setdefault(n, {}).update({"ocr": f"failed: {err}", "ocr_v": OCR_V})
                if err == "ocrmypdf not installed":
                    print("      (brew install ocrmypdf — then re-run with --ocr)")
                    break
                continue
            if len(txt) > len(texts.get(n, "")):
                texts[n] = txt
                cache[n].update({"text": txt})
                print(f"      {len(txt):,} characters in {time.time() - t0:.0f}s")
            else:
                print("      no gain — keeping the original reading")
            cache[n].update({"ocr": "ok", "ocr_v": OCR_V})
    elif thin:
        print(f"  · {len(thin)} PDF(s) look like scans with no text layer — "
              "re-run with --ocr to recover them (slow, cached)")

    for stale in set(cache) - set(names):
        cache.pop(stale, None)
    os.makedirs(OUT, exist_ok=True)
    try:
        with gzip.open(CACHE, "wt", encoding="utf-8") as fh:
            json.dump(cache, fh)
    except OSError:
        pass

    written = unchanged = 0
    keep, blind = {MANIFEST}, []
    for name in names:
        text = clean(texts.get(name, ""))
        if not text:
            blind.append((name, why_blind(name, problems.get(name, "")), ""))
            continue
        if len(text) < MIN_CHARS:
            blind.append((name, "too little text extracted to be the document",
                          f"{len(text)} characters"))
            continue
        pages = page_count(os.path.join(RAW, name))
        if pages and len(text) / pages < MIN_CHARS_PER_PAGE:
            blind.append((name, "text layer too thin to be the document — likely a scan",
                          f"{len(text) // pages} characters per page over {pages} pages"))
            continue

        title = (overrides.get(name) or {}).get("title") or name
        truncated = len(text) >= EXTRACT_LIMIT
        note = (f"> **INCOMPLETE.** Extraction stopped at {EXTRACT_LIMIT:,} characters, so a\n"
                f"> search that finds nothing here is NOT evidence the original lacks it.\n\n"
                if truncated else "")
        body = (f"---\n"
                f"title: {json.dumps(title, ensure_ascii=False)}\n"
                f"source: garden/raw/{name}\n"
                f"complete: {str(not truncated).lower()}\n"
                f"---\n\n"
                f"# {title}\n\n"
                f"{note}"
                f"> Text extracted from `garden/raw/{name}`. **Cite that original, never this\n"
                f"> file** — this is a rebuildable search copy.\n\n"
                f"{text}\n")
        dest = name + ".md"            # keep the original name, so a hit maps back exactly
        keep.add(dest)
        if write_if_changed(os.path.join(OUT, dest), body):
            written += 1
        else:
            unchanged += 1

    lines = ["---", 'title: "Files the library cannot search"', "complete: true", "---", "",
             "# Files the library cannot search", "",
             f"> **{len(blind)} of the {len(names)} files in `garden/raw/` yield no usable "
             "text**, so no search will\n> ever match their contents. **A search finding "
             "nothing is not evidence the garden\n> lacks it** — if what you want might be "
             "one of these, open the original.", ""]
    groups = {}
    for name, reason, detail in blind:
        groups.setdefault(reason, []).append((name, detail))
    for reason in sorted(groups):
        lines += [f"## {reason[0].upper()}{reason[1:]} ({len(groups[reason])})", ""]
        for name, detail in sorted(groups[reason], key=lambda x: x[0].lower()):
            title = (overrides.get(name) or {}).get("title") or name
            lines.append(f"- **{title}** — `garden/raw/{name}`" + (f" · {detail}" if detail else ""))
        lines.append("")
    write_if_changed(os.path.join(OUT, MANIFEST), "\n".join(lines))

    pruned = 0
    for f in os.listdir(OUT):
        if f.endswith(".md") and f not in keep:
            os.remove(os.path.join(OUT, f))
            pruned += 1

    searchable = written + unchanged
    print(f"library -> .qmd/library/   {searchable} of {len(names)} file(s) searchable")
    print(f"  {written} written · {unchanged} unchanged · {pruned} removed · "
          f"{extracted} extracted this run")
    print(f"  {len(blind)} cannot be searched — listed by name in {MANIFEST}")
    for reason in sorted(groups):
        print(f"    {len(groups[reason]):>4}  {reason}")
    missing_tools = sorted({p for p in problems.values() if "not installed" in p})
    if missing_tools:
        print("  ! " + "; ".join(missing_tools) + " — those files were NOT read, which is not "
              "the same as unreadable")
    print("\nnext: qmd update && qmd embed   (or the reindex skill, which does both)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
