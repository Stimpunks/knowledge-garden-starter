#!/usr/bin/env python3
"""Rebuild the garden's index and search, in the one order that works.

    python3 .claude/skills/reindex/reindex.py             # everything
    python3 .claude/skills/reindex/reindex.py --check     # report only, writes nothing
    python3 .claude/skills/reindex/reindex.py --no-embed  # skip the slow vector step
    python3 .claude/skills/reindex/reindex.py --ocr       # also OCR scanned PDFs (slow)

The three steps feed each other, and NONE of them errors when run out of order:

    1  garden/wiki/_generate.py     the index over raw/            (fatal if it fails)
    2  garden/wiki/_qmd_library.py  the text of raw/, for search   (non-fatal)
    3  qmd update && qmd embed      re-index, then re-embed — last  (non-fatal)

Embed before the index is rebuilt and search describes the old index. That is the whole
reason this is a script rather than three lines in a README: a rule in a file is a
suggestion, and a fixed order is not.

`qmd embed` CAN EXIT 0 WITH WORK LEFT. On a big batch it stops at an internal limit, reports
success, and leaves documents without vectors — keyword search keeps working, so nothing
looks wrong, but `qmd query` silently cannot return what was skipped. So this checks qmd's
own `Pending:` count after every embed, runs it again while that count is still falling,
and never says "clean" while anything is pending.

Exit status: 0 everything that ran succeeded · 1 the index rebuild failed (that IS the
index — stop) · 2 a search step failed or is incomplete (the index is fine; search is behind).
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
GARDEN = os.path.join(ROOT, "garden")
QMD_YML = os.path.join(ROOT, ".qmd", "index.yml")
LIBRARY = os.path.join(ROOT, ".qmd", "library")
MAX_EMBED_PASSES = 5


def sh(cmd, cwd=ROOT, timeout=7200):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def have(tool):
    return subprocess.run(["which", tool], capture_output=True).returncode == 0


def collections():
    """Collection names in the project's own qmd config, or None if it has none."""
    if not os.path.exists(QMD_YML):
        return None
    names, inside = [], False
    for line in open(QMD_YML, encoding="utf-8"):
        if re.match(r"^collections:\s*$", line):
            inside = True
            continue
        if inside and re.match(r"^\S", line):
            break
        m = re.match(r"^  (\S[^:]*):\s*$", line) if inside else None
        if m:
            names.append(m.group(1))
    return names


def pending():
    try:
        p = sh(["qmd", "status"], timeout=120)
    except Exception:
        return None
    m = re.search(r"Pending:\s*([\d,]+)", p.stdout + p.stderr)
    return int(m.group(1).replace(",", "")) if m else 0


def stage(label, cmd, cwd=ROOT, tail=8):
    print(f"\n{'=' * 64}\n  {label}\n{'=' * 64}")
    t0 = time.time()
    try:
        p = sh(cmd, cwd=cwd)
    except subprocess.TimeoutExpired:
        print("  TIMED OUT")
        return False, None
    # qmd draws progress bars with terminal escape codes; they are noise in a report.
    text = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", p.stdout + p.stderr)
    lines = [ln for ln in text.splitlines() if ln.strip()]
    for ln in lines[-tail:]:
        print(f"  {ln}")
    if len(lines) > tail:
        print(f"  … ({len(lines) - tail} earlier lines)")
    ok = p.returncode == 0
    print(f"  {'ok' if ok else f'FAILED (exit {p.returncode})'} — {time.time() - t0:.1f}s")
    return ok, p


def search_setup_problems():
    """Why search cannot be refreshed here, or [] if it can. Each is a sentence to print."""
    probs = []
    if not have("qmd"):
        return ["qmd is not installed — README Step 4. The garden works without it; "
                "everything is on disk and greppable."]
    cols = collections()
    if cols is None:
        old = os.path.exists(os.path.join(GARDEN, ".qmd", "index.yml"))
        probs.append("no project search index at .qmd/ — from the top of the project run "
                     "`qmd init`, then add the collections (README Step 4)."
                     + (" (There is one at garden/.qmd/ — qmd only finds an index in the "
                        "folder you are in or above it, so Claude, working from the top of "
                        "the project, cannot see that one.)" if old else ""))
        return probs
    if os.path.isdir(LIBRARY) and "library" not in cols:
        probs.append("the library text exists but is not a qmd collection, so no search "
                     "can reach it. Add it once:  qmd collection add ./.qmd/library "
                     "--name library")
    return probs


def check():
    print("CHECK ONLY — nothing is rebuilt or written.\n")
    raw = [f for f in os.listdir(os.path.join(GARDEN, "raw"))
           if f not in {".DS_Store", "README.md", "readme.md"}
           and not os.path.isdir(os.path.join(GARDEN, "raw", f))]
    try:
        known = json.load(open(os.path.join(GARDEN, "wiki", "_raw_manifest.json"),
                               encoding="utf-8")).get("assets", [])
    except (OSError, ValueError):
        known = None
    print(f"  raw/: {len(raw)} file(s) on this computer"
          + ("" if known is None else f"; the index knows {len(known)}"))
    if known is not None:
        missing = sorted(set(known) - set(raw))
        new = sorted(set(raw) - set(known))
        if missing:
            print(f"  ! {len(missing)} indexed file(s) are not here — a rebuild would refuse. "
                  "Is this your other computer, or is a drive unplugged?")
        if new:
            print(f"  + {len(new)} file(s) in raw/ are not in the index yet — rebuild")
    if os.path.isdir(LIBRARY):
        n = len([f for f in os.listdir(LIBRARY) if f.endswith(".md")])
        print(f"  library text: {n} file(s) in .qmd/library/")
    for p in search_setup_problems():
        print(f"  ! {p}")
    if have("qmd") and collections():
        print(f"  qmd collections: {', '.join(collections())}")
        n = pending()
        if n:
            print(f"  ! {n} document(s) still need embedding — `qmd query` under-reports "
                  "until that is 0")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="report only; write nothing")
    ap.add_argument("--no-embed", action="store_true",
                    help="run `qmd update` but skip `qmd embed` (the slow part)")
    ap.add_argument("--ocr", action="store_true",
                    help="also OCR scanned PDFs — slow, minutes per book, cached after")
    a = ap.parse_args()

    if not os.path.isdir(os.path.join(GARDEN, "raw")):
        sys.exit("ERROR: no garden/raw/ here — run this from a garden made from the template.")
    if a.check:
        return check()

    failures = []

    # 1. The index. Fatal: if this fails, everything downstream would describe a broken one.
    cmd = [sys.executable, "wiki/_generate.py"]
    if not os.path.exists(os.path.join(GARDEN, "wiki", "_concepts.py")):
        cmd.append("--no-concepts")
    ok, _ = stage("1/3  the index over raw/", cmd, cwd=GARDEN, tail=25)
    if not ok:
        print("\nSTOPPED. The index did not rebuild, so search was left alone — refreshing it"
              "\nnow would only spread the problem. Read the message above; if it is the"
              "\nmanifest guard, this is probably not the computer that holds your library.")
        return 1

    # 2. The library text.
    lib = [sys.executable, os.path.join("garden", "wiki", "_qmd_library.py")]
    if a.ocr:
        lib.append("--ocr")
    ok, _ = stage("2/3  the text of raw/, for search", lib, tail=(40 if a.ocr else 10))
    if not ok:
        failures.append("library text did not rebuild — search over raw/ may be stale")

    # 3. Search, last.
    print(f"\n{'=' * 64}\n  3/3  search (qmd)\n{'=' * 64}")
    probs = search_setup_problems()
    if probs and (not have("qmd") or collections() is None):
        for p in probs:
            print(f"  · {p}")
        print("  skipped — the index and library text are rebuilt; search is not set up.")
    else:
        for p in probs:
            print(f"  ! {p}")
            failures.append(p)
        ok, p = stage("3/3a  qmd update", ["qmd", "update"], tail=8)
        if not ok:
            failures.append("qmd update failed — search not refreshed")
        elif a.no_embed:
            print("\n  --no-embed: keyword search (`qmd search`) is current; meaning-based "
                  "search (`qmd query`) still answers from the old vectors.")
        else:
            last = None
            for n in range(1, MAX_EMBED_PASSES + 1):
                ok, _ = stage(f"3/3b  qmd embed (pass {n})", ["qmd", "embed"], tail=4)
                if not ok:
                    failures.append("qmd embed failed — meaning-based search is behind")
                    break
                left = pending()
                if not left:
                    break
                print(f"  qmd embed exited 0 with {left} document(s) still pending — "
                      "that is normal on a big batch; going again.")
                if last is not None and left >= last:
                    failures.append(f"{left} document(s) still unembedded and the count "
                                    "stopped falling — run `qmd embed` again later")
                    break
                last = left
            else:
                left = pending()
                if left:
                    failures.append(f"{left} document(s) still unembedded after "
                                    f"{MAX_EMBED_PASSES} passes — run this again")

    dirty = [ln for ln in sh(["git", "status", "--porcelain", "--", "garden/wiki"]).stdout
             .splitlines() if ln.strip()]
    if dirty:
        print(f"\n  garden/wiki/ has {len(dirty)} changed file(s) — the rebuilt index. "
              "Commit it with commit-garden. (Nothing under .qmd/ is ever committed.)")

    if failures:
        print(f"\n  The index is fine. Search is behind — {len(failures)} problem(s):")
        for f in failures:
            print(f"    ! {f}")
        print("  Until these clear, a search that finds nothing is not evidence of absence.")
        return 2
    print("\n  All steps clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
