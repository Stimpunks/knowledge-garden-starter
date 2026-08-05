#!/usr/bin/env python3
"""Regenerates wiki/ as an AI-written table of contents referencing files in raw/.
Categorization is keyword-based over filenames. Re-runnable: overwrites wiki/.

Also refreshes the **concept layer** (`wiki/concepts/`) via `_concepts.py` — the
cross-corpus backlink index keyed on our published glossary. That layer is read-only
over site/, highlights/ and notes/; it links them, it never modifies or indexes them
as assets.

Flags:
  --no-concepts     skip the concept layer (fast; sections + README only)
  --force-concepts  ignore the concept cache and rescan every corpus
  --check           concept-layer health report, then exit
"""
import os, re, json, glob, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "raw")
WIKI = os.path.join(ROOT, "wiki")
sys.path.insert(0, WIKI)

# Optional per-file hints written by the add-new-resource skill:
#   { "exact filename.pdf": {"category": "<cat-id>", "title": "Human Title"} }
# Lets analysis place opaque-named files and give them readable titles — without
# ever hand-editing the generated .md (regenerate is still the only write path).
OVERRIDES = {}
_ovr = os.path.join(WIKI, "_overrides.json")
if os.path.exists(_ovr):
    try:
        OVERRIDES = json.load(open(_ovr))
    except Exception:
        OVERRIDES = {}

# Index top-level entries in raw/, excluding subfolders (e.g. raw/inputs/, which
# holds ingested session logs as reference provenance). Use "not isdir" rather than
# "isfile" so broken symlinks — which isfile rejects — stay indexed.
# A README in raw/ documents the folder; it is not an asset in it. Skipping it means a
# starter garden can explain its own rules in place — "write the rules down where the work
# happens" — without that note showing up as catalogued library material.
SKIP = {".DS_Store", "README.md", "readme.md"}
files = sorted([f for f in os.listdir(RAW)
                if f not in SKIP and not os.path.isdir(os.path.join(RAW, f))],
               key=str.lower)

# Ordered categories: (id, title, emoji, [keywords]). First match wins.
# Ordered categories: (id, title, emoji, [keywords]). First match wins.
# Loaded from wiki/_categories.json so the shelves are DATA, not code — that file is the one
# thing you rewrite to point this generator at a different library. Missing or unreadable file
# means no keyword categories at all, which is honest: everything lands in Unidentified and the
# index still builds, rather than silently falling back to somebody else's taxonomy.
def _load_config():
    p = os.path.join(WIKI, "_config.json")
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        print(f"  ! no usable {p} — every asset will land in Unidentified")
        return {}


CONFIG = _load_config()
VAULT_NAME = (CONFIG.get("vault") or {}).get("name") or "Knowledge System"
GLOSSARY_REL = (CONFIG.get("vault") or {}).get("glossary_path")


def _load_cats():
    data = CONFIG
    out = []
    for c in data.get("categories", []):
        if c.get("id") and c.get("title"):
            out.append((c["id"], c["title"], c.get("emoji", ""), [k.lower() for k in c.get("keywords", [])]))
    return out


CATS = _load_cats()

if "--check" in sys.argv:
    import _concepts
    _concepts.check(OVERRIDES)
    raise SystemExit(0)

MEDIA_EXT = {"png","jpg","jpeg","webp","mp4","m4a","vtt"}

VALID_CATS = {c[0] for c in CATS} | {"media", "unidentified"}

def cat_for(name):
    ov = OVERRIDES.get(name)
    if ov and ov.get("category") in VALID_CATS:
        return ov["category"]
    ext = name.rsplit(".",1)[-1].lower() if "." in name else ""
    # keyword-match against the filename AND any override title, so a title-only
    # override (e.g. from mdls metadata) still routes an opaque-named file correctly.
    low = (name + " " + (ov.get("title", "") if ov else "")).lower()
    # infographic naming pattern: "X vs. Y" images
    if ext in {"png","jpg","jpeg"} and " vs" in low:
        return "neurodivergent-insights"
    for cid, title, emoji, kws in CATS:
        for kw in kws:
            if kw in low:
                return cid
    # media fallback if uncategorized
    if ext in MEDIA_EXT:
        return "media"
    return "unidentified"

buckets = {}
for f in files:
    buckets.setdefault(cat_for(f), []).append(f)

EXTRA = [
    ("media", "Media & Graphics (uncategorized)", "🖼️"),
    ("unidentified", "Unidentified (opaque filenames — need review)", "❓"),
]
ALL = [(c[0], c[1], c[2]) for c in CATS] + EXTRA

# Concept layer: refreshed before the section pages, because those pages carry
# backlink chips derived from it. CONCEPT_MAP is raw filename -> [concept slug].
CONCEPT_MAP, CONCEPT_RECORDS = {}, []
if "--no-concepts" not in sys.argv:
    try:
        import _concepts
        CONCEPT_RECORDS, CONCEPT_MAP, _cmeta, _cbroad = _concepts.refresh(
            OVERRIDES, force="--force-concepts" in sys.argv)
    except ModuleNotFoundError:
        # No _concepts.py at all — the normal state for a garden that has not opted into
        # the concept layer. Not an error, and it must not read like one: a Python
        # traceback name in the output makes a newcomer think their install is broken.
        print("  · concept layer not installed (wiki/_concepts.py absent) — file index only")
    except Exception as e:                       # never let this break the index
        print(f"  ! concept layer skipped: {type(e).__name__}: {e}")

CHIP_CAP = 4

def link(f):
    ext = f.rsplit(".",1)[-1].upper() if "." in f else "?"
    ov = OVERRIDES.get(f) or {}
    label = ov.get("title") or (f.rsplit(".",1)[0] if "." in f else f)
    line = f"- [{label}](<../raw/{f}>) · `{ext}`"
    # Backlink chips — the wiki-to-wiki edges. A flat file list can't tell you a
    # paper is about monotropism *and* the double empathy problem; this can.
    slugs = CONCEPT_MAP.get(f, [])          # already strongest-first
    if slugs:
        chips = " · ".join(f"[{s.replace('-',' ')}](concepts/{s}.md)"
                           for s in slugs[:CHIP_CAP])
        more = f" +{len(slugs)-CHIP_CAP}" if len(slugs) > CHIP_CAP else ""
        line += f"<br>  ↳ {chips}{more}"
    return line

os.makedirs(WIKI, exist_ok=True)
# wipe only the top-level pages the generator OWNS (README + one per section id).
# Authored files like sources.md — and subfolders (learnings/, sessions/, curated/) —
# are left untouched.
_owned = {"README.md"} | {cid + ".md" for cid, *_ in ALL}
for old in os.listdir(WIKI):
    if old in _owned and os.path.isfile(os.path.join(WIKI, old)):
        os.remove(os.path.join(WIKI, old))

total = len(files)
# Section pages
section_meta = []
for cid, title, emoji in ALL:
    items = sorted(buckets.get(cid, []), key=str.lower)
    if not items:
        continue
    section_meta.append((cid, title, emoji, len(items)))
    with open(os.path.join(WIKI, f"{cid}.md"), "w") as fh:
        fh.write(f"# {emoji} {title}\n\n")
        fh.write(f"_{len(items)} item(s). Auto-generated index — links point into `../raw/`. "
                 f"Do not edit by hand; regenerate instead._\n\n")
        fh.write(f"[← Back to wiki index](README.md)\n\n")
        for it in items:
            fh.write(link(it) + "\n")

# README index
ext_counts = {}
for f in files:
    e = f.rsplit(".",1)[-1].lower() if "." in f else "(none)"
    ext_counts[e] = ext_counts.get(e,0)+1
ext_line = " · ".join(f"{v} {k}" for k,v in sorted(ext_counts.items(), key=lambda x:-x[1]))

with open(os.path.join(WIKI, "README.md"), "w") as fh:
    fh.write(f"# 🗂️ {VAULT_NAME} — Wiki Index\n\n")
    fh.write("> **AI-written table of contents.** Every link below points to an original, "
             "unaltered file in [`../raw/`](../raw). This wiki is generated by Claude and "
             "**must never be hand-edited** — to change it, ask Claude to regenerate it. "
             "The `raw/` assets are never modified.\n\n")
    fh.write(f"**{total} files** indexed · {ext_line}\n\n")

    # The concept layer: the only part of the wiki that indexes *ideas* rather than
    # files, and the only part that reaches across every corpus in the garden.
    if CONCEPT_RECORDS:
        n_linked = len([r for r in CONCEPT_RECORDS if r["total"]])
        n_auth = len([r for r in CONCEPT_RECORDS if r["authored"]])
        top = sorted(CONCEPT_RECORDS, key=lambda r: -r["total"])[:12]
        fh.write("## 🕸️ Concepts\n\n")
        gloss = (f"[glossary](../{GLOSSARY_REL})" if GLOSSARY_REL else "glossary")
        fh.write(f"_**{len(CONCEPT_RECORDS)} concepts** from our published "
                 f"{gloss} · "
                 f"{n_linked} with links · {n_auth} with written synthesis._ "
                 "→ **[browse the concept index](concepts/README.md)**\n\n")
        fh.write("Section pages below index **files**; concept pages index **ideas** — "
                 "what `raw/`, `site/`, `highlights/`, `notes/` and curated sources "
                 "each hold on a topic, cross-linked. Start here when you want "
                 "everything we have on something.\n\n")
        fh.write("Most-covered: " + " · ".join(
            f"[{r['slug'].replace('-',' ')}](concepts/{r['slug']}.md)"
            for r in top) + "\n\n")

    # Authored guides (workflow learnings) live in wiki/learnings/ and are NOT
    # generated from filenames — they're distilled by Claude and preserved across
    # regenerations. Surface them here if present.
    guides_dir = os.path.join(WIKI, "learnings")
    guides = sorted(glob.glob(os.path.join(guides_dir, "*.md"))) if os.path.isdir(guides_dir) else []
    if guides:
        fh.write("## 🧭 Guides & Workflow Learnings\n\n")
        fh.write("_Distilled from past Claude Code sessions (source logs in "
                 "[`../raw/inputs/`](../raw/inputs)). Authored, not auto-generated._\n\n")
        for g in guides:
            first = ""
            for ln in open(g):
                if ln.startswith("#"):
                    first = ln.lstrip("#").strip(); break
            rel = os.path.relpath(g, WIKI)
            fh.write(f"- [{first or os.path.basename(g)}]({rel})\n")
        fh.write("\n")

    # Per-session summaries maintained by the sync-claude-sessions skill (also authored,
    # also preserved across regenerations). Surface the index if present.
    sessions_idx = os.path.join(WIKI, "sessions", "README.md")
    if os.path.exists(sessions_idx):
        n_sessions = len([f for f in glob.glob(os.path.join(WIKI, "sessions", "*.md"))
                          if os.path.basename(f) != "README.md"])
        fh.write("## 🗓️ Session Summaries\n\n")
        fh.write(f"_{n_sessions} Claude Code session(s) digested by the "
                 "`sync-claude-sessions` skill._ → **[browse the index](sessions/README.md)**\n\n")

    # Curated content (claims + tags) maintained by the sync-curated-content skill.
    curated_idx = os.path.join(WIKI, "curated", "README.md")
    if os.path.exists(curated_idx):
        n_cur = len([f for f in glob.glob(os.path.join(WIKI, "curated", "*.md"))
                     if os.path.basename(f) != "README.md"])
        fh.write("## 🗞️ Curated Content\n\n")
        fh.write(f"_Key claims + tags from {n_cur} followed source(s) "
                 "([sources.md](sources.md)), by the `sync-curated-content` skill._ "
                 "→ **[browse the index](curated/README.md)**\n\n")

    fh.write("## Sections\n\n")
    for cid, title, emoji, n in section_meta:
        fh.write(f"- {emoji} **[{title}]({cid}.md)** — {n} item(s)\n")
    fh.write("\n---\n\n")
    fh.write("### How this is organized\n\n")
    fh.write("- Files were flattened into `raw/` (no subfolders) and grouped here by topic "
             "using keyword matching on filenames.\n")
    fh.write("- Items with opaque filenames (DOIs, hashes) land in **Unidentified** until "
             "their titles are confirmed — a good next task is to open those and retitle their wiki entries.\n")
    fh.write("- A file appears in exactly one section (first topic match wins).\n")

print(f"Wrote wiki/ with {len(section_meta)} sections, {total} files.")
for cid, title, emoji, n in section_meta:
    print(f"  {n:>4}  {title}")
