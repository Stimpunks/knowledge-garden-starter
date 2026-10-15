#!/usr/bin/env python3
"""Move files from the inbox tray into the library — copied in untouched, checked, then cleared.

    python3 .claude/skills/process-inbox/process-inbox.py list
    python3 .claude/skills/process-inbox/process-inbox.py categories
    python3 .claude/skills/process-inbox/process-inbox.py ingest "garden/inbox/file.pdf" \\
        --title "A Real Title" --category reading

`ingest` also takes a file from anywhere else (that is how add-to-garden stores one); only a
file inside garden/inbox/ is removed afterwards. It does not rebuild the index — run that
once at the end of a batch, not once per file.

THE GUARDS, and why each is here:

  * NEVER OVERWRITES. The copy is opened with O_EXCL, so if a file of that name appears in
    raw/ between the check and the write, the write fails instead of replacing an original.
    A name collision gets a " (2)" suffix and is reported.
  * NO DUPLICATES. If raw/ already holds the same bytes under any name, nothing is copied and
    the result says which file it already is.
  * CHECKED BEFORE CLEARED. The copy in raw/ is hashed and compared with the source, and the
    inbox file is removed only if they match. Nothing outside garden/inbox/ is ever deleted.
  * A COPY, NOT A LINK. A hard link into raw/ would be the same file under two names, so
    editing the "inbox copy" would edit the original. This writes new bytes.

Prints one JSON object per ingest. Exit status: 0 ok · 1 a refusal or error.
"""
import argparse
import hashlib
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
GARDEN = os.path.join(ROOT, "garden")
RAW = os.path.join(GARDEN, "raw")
INBOX = os.path.join(GARDEN, "inbox")
WIKI = os.path.join(GARDEN, "wiki")
SKIP = {".DS_Store", "README.md", "readme.md", ".gitkeep"}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def inbox_files():
    out = []
    for d, dirs, files in os.walk(INBOX):
        dirs[:] = [x for x in dirs if not x.startswith(".")]
        for f in files:
            if f in SKIP or f.startswith("."):
                continue
            out.append(os.path.join(d, f))
    return sorted(out, key=str.lower)


def category_ids():
    try:
        with open(os.path.join(WIKI, "_config.json"), encoding="utf-8") as fh:
            cats = json.load(fh).get("categories", [])
    except (OSError, ValueError):
        cats = []
    return [(c["id"], c.get("title", "")) for c in cats if c.get("id")] + \
        [("media", "Media & Graphics"), ("unidentified", "Unidentified")]


def already_stored(src, digest):
    size = os.path.getsize(src)
    for f in os.listdir(RAW):
        p = os.path.join(RAW, f)
        if f in SKIP or os.path.isdir(p) or not os.path.isfile(p):
            continue
        if os.path.getsize(p) == size and sha256(p) == digest:
            return f
    return None


def free_name(name):
    if not os.path.lexists(os.path.join(RAW, name)):
        return name
    stem, dot, ext = name.rpartition(".")
    if not dot:
        stem, ext = name, ""
    n = 2
    while True:
        cand = f"{stem} ({n}).{ext}" if ext else f"{stem} ({n})"
        if not os.path.lexists(os.path.join(RAW, cand)):
            return cand
        n += 1


def copy_exclusive(src, dest):
    """Write new bytes at dest, refusing if dest exists. Never a link, never an overwrite."""
    fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(fd, "wb") as out, open(src, "rb") as inp:
            shutil.copyfileobj(inp, out, 1 << 20)
        shutil.copystat(src, dest)
    except BaseException:
        try:
            os.remove(dest)
        except OSError:
            pass
        raise


def record(name, title, category):
    """Add or fill in this file's entry in _overrides.json. Never replaces an existing title."""
    path = os.path.join(WIKI, "_overrides.json")
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        data = {}
    ent = dict(data.get(name) or {})
    kept = None
    if title:
        if ent.get("title") and ent["title"] != title:
            kept = ent["title"]
        else:
            ent["title"] = title
    if category:
        ent.setdefault("category", category)
    if not ent:
        return None
    data[name] = ent
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, path)
    return kept


def prune_empty_dirs():
    for d, dirs, files in sorted(os.walk(INBOX), key=lambda x: -len(x[0])):
        if d != INBOX and not os.listdir(d):
            os.rmdir(d)


def ingest(a):
    src = os.path.abspath(a.path)
    if not os.path.isfile(src):
        return {"error": f"not a file: {a.path}"}
    if os.path.commonpath([src, os.path.abspath(RAW)]) == os.path.abspath(RAW):
        return {"error": "that file is already in garden/raw/ — nothing to store"}
    ids = [c for c, _ in category_ids()]
    if a.category and a.category not in ids:
        return {"error": f"unknown category {a.category!r}",
                "valid": ids,
                "hint": "leave --category out to let the index file it (or Unidentified); "
                        "adding a new shelf is a change to wiki/_config.json the user owns"}

    digest = sha256(src)
    dup = already_stored(src, digest)
    if dup:
        stored, status = dup, "already-present"
    else:
        stored = free_name(os.path.basename(src))
        dest = os.path.join(RAW, stored)
        copy_exclusive(src, dest)
        if sha256(dest) != digest:
            os.remove(dest)
            return {"error": "the copy in raw/ did not match the source byte for byte — "
                             "removed it; the source is untouched"}
        status = "added"

    kept_title = record(stored, a.title, a.category)
    in_inbox = os.path.commonpath([src, os.path.abspath(INBOX)]) == os.path.abspath(INBOX)
    cleared = False
    if in_inbox and not a.keep:
        os.remove(src)           # only reached once raw/ holds these exact bytes
        prune_empty_dirs()
        cleared = True

    shown = os.path.relpath(src, ROOT) if src.startswith(ROOT + os.sep) else src
    out = {"source": shown, "stored_as": f"garden/raw/{stored}",
           "status": status, "cleared_from_inbox": cleared}
    if stored != os.path.basename(src) and status == "added":
        out["renamed_because"] = "a different file already had that name in raw/"
    if a.title:
        out["title"] = kept_title or a.title
    if kept_title:
        out["title_note"] = "an existing title was kept; change _overrides.json by hand if " \
                            "the new one is better"
    if a.category:
        out["category"] = a.category
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="what is waiting in garden/inbox/")
    sub.add_parser("categories", help="the shelf ids from wiki/_config.json")
    ing = sub.add_parser("ingest", help="store one file in raw/, then clear it from the inbox")
    ing.add_argument("path")
    ing.add_argument("--title", help="the real title, from opening the file")
    ing.add_argument("--category", help="a shelf id; leave out if none fits")
    ing.add_argument("--keep", action="store_true", help="store it but leave it in the inbox")
    a = ap.parse_args()

    if not os.path.isdir(RAW):
        sys.exit("ERROR: no garden/raw/ here — run this from a garden made from the template.")

    if a.cmd == "list":
        files = inbox_files()
        if not files:
            print("The inbox is empty. Nothing to process.")
        for f in files:
            print(f"{os.path.getsize(f):>12,}  {os.path.relpath(f, ROOT)}")
        return 0
    if a.cmd == "categories":
        for cid, title in category_ids():
            print(f"{cid:<16} {title}")
        return 0

    res = ingest(a)
    print(json.dumps(res, indent=1, ensure_ascii=False))
    return 1 if "error" in res else 0


if __name__ == "__main__":
    sys.exit(main())
