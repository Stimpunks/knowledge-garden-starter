#!/usr/bin/env python3
"""Bring this computer up to date with your garden's remote — safely. The counterpart to
commit-garden: that one sends work out, this one brings work in.

    python3 .claude/skills/pull-garden/pull-garden.py --check   # show the gap; change nothing
    python3 .claude/skills/pull-garden/pull-garden.py           # bring the work in

WHY IT EXISTS. Keep your garden on two computers and sooner or later you commit on one while
the other is behind. The usual advice is `git pull --rebase`, and when that hits a conflict
it stops halfway and leaves the repository mid-rebase: every command afterwards says
something alarming and none of the usual advice applies. That is the worst state to hand
someone who is still learning git. So this script:

  * NEVER LEAVES A HALF-FINISHED REBASE. On any conflict it runs `git rebase --abort`, puts
    everything back exactly as it was, and names the file that collided.
  * WATCHES AUTOSTASH, RATHER THAN TRUSTING IT. Uncommitted work is set aside during the pull
    and put back after. Putting it back can itself fail, which leaves your work in a stash
    nothing mentions. This counts stashes before and after, and shouts if the count grew.
  * TELLS YOU WHAT CAME IN, and whether this computer is missing library files the other one
    added — raw/ is not in git, so the index can arrive here before the files do.

It does not commit and does not push. Exit status: 0 ok or already current · 1 setup
problem · 2 refused (conflict, or work left in a stash).
"""
import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
MANIFEST = os.path.join(ROOT, "garden", "wiki", "_raw_manifest.json")
RAW = os.path.join(ROOT, "garden", "raw")


def git(*a):
    return subprocess.run(["git", "-C", ROOT, *a], capture_output=True, text=True)


def count(rev):
    out = git("rev-list", "--count", rev).stdout.strip()
    return int(out) if out.isdigit() else 0


def stash_depth():
    return len([x for x in git("stash", "list").stdout.splitlines() if x.strip()])


def by_area(paths):
    areas = {}
    for p in paths:
        parts = p.split("/")
        key = "/".join(parts[:2]) + "/" if parts[0] == "garden" and len(parts) > 2 \
            else (parts[0] + "/" if len(parts) > 1 else parts[0])
        areas[key] = areas.get(key, 0) + 1
    return ", ".join(f"{n} in {k}" for k, n in sorted(areas.items(), key=lambda x: -x[1])[:8])


def missing_library_files():
    """Files the (possibly just-pulled) index lists that this computer's raw/ lacks."""
    try:
        with open(MANIFEST, encoding="utf-8") as fh:
            known = json.load(fh).get("assets", [])
    except (OSError, ValueError):
        return []
    here = set(os.listdir(RAW)) if os.path.isdir(RAW) else set()
    return sorted(f for f in known if f not in here)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="report the gap; change nothing")
    a = ap.parse_args()

    if git("rev-parse", "--is-inside-work-tree").stdout.strip() != "true":
        print("ERROR: this folder is not a git repository yet — see README Step 2.")
        return 1
    if git("rev-parse", "-q", "--verify", "REBASE_HEAD").returncode == 0 or \
            os.path.isdir(os.path.join(ROOT, ".git", "rebase-merge")) or \
            os.path.isdir(os.path.join(ROOT, ".git", "rebase-apply")):
        print("ERROR: a rebase is already in progress here (not one this script started).\n"
              "  To put everything back the way it was before it began:\n"
              "      git rebase --abort")
        return 1

    branch = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if git("rev-parse", "--abbrev-ref", "@{upstream}").returncode != 0:
        print(f"Nothing to pull: branch '{branch}' is not connected to a remote. That is "
              "normal if\nyou took the ZIP route or have not pushed yet — README Step 2.")
        return 0

    f = git("fetch", "--quiet")
    if f.returncode != 0:
        last = f.stderr.strip().splitlines()[-1] if f.stderr.strip() else "fetch failed"
        print(f"Could not reach the remote, so nothing changed here.\n  {last}")
        return 2

    behind, ahead = count("HEAD..@{upstream}"), count("@{upstream}..HEAD")
    dirty = [ln[3:].strip('"') for ln in git("status", "--porcelain").stdout.splitlines()
             if ln.strip()]
    print(f"{branch}: {behind} commit(s) to bring in · {ahead} here not yet pushed · "
          f"{len(dirty)} uncommitted change(s)")

    if behind == 0:
        print("Already up to date with the remote.")
        if ahead:
            print(f"  {ahead} commit(s) here are not on the remote yet — commit-garden "
                  "pushes them.")
        return 0

    print(f"\nComing in:")
    for ln in git("log", "--format=  %h  %ad  %s", "--date=short", "-12",
                  "HEAD..@{upstream}").stdout.splitlines():
        print(ln)
    if behind > 12:
        print(f"  … and {behind - 12} more")
    changed = [p for p in git("diff", "--name-only", "HEAD...@{upstream}").stdout.splitlines()
               if p.strip()]
    print(f"\nTouching {len(changed)} file(s): {by_area(changed)}")

    if a.check:
        print("\nCHECK ONLY — nothing was pulled.")
        return 0

    before, depth = git("rev-parse", "HEAD").stdout.strip(), stash_depth()
    p = git("pull", "--rebase", "--autostash")
    if p.returncode != 0:
        aborted = git("rebase", "--abort")
        still = os.path.isdir(os.path.join(ROOT, ".git", "rebase-merge")) or \
            os.path.isdir(os.path.join(ROOT, ".git", "rebase-apply"))
        out = p.stdout + p.stderr
        if "CONFLICT" in out:
            print("\nREFUSED: the same file was changed here and on the remote, so nothing "
                  "was pulled.")
        else:
            print("\nREFUSED: the pull could not finish, so nothing was pulled. Git said:")
        if still:
            print("  !! The rebase could not be undone automatically. Run `git rebase --abort`"
                  "\n     before anything else.")
        else:
            print("  Everything is back exactly as it was before this ran"
                  + ("." if aborted.returncode == 0 else
                     " (no rebase had started)."))
        for ln in out.splitlines():
            if "CONFLICT" in ln or ln.startswith(("error:", "fatal:")) or ln.startswith("\t"):
                print(f"    {ln.strip()}")
        if "CONFLICT" in out:
            print("\n  Open both versions and decide what the file should say — this is a"
                  "\n  choice, not a retry. If the collision is in garden/wiki/ (the generated"
                  "\n  index), the usual fix is simpler: take the remote copy and rebuild.")
        if stash_depth() > depth:
            print("\n  Your uncommitted changes were set aside and are still in a stash."
                  "\n  Bring them back with:  git stash pop")
        return 2

    if stash_depth() > depth:
        print(f"\n!! The pull worked, but YOUR UNCOMMITTED CHANGES ARE STILL SET ASIDE in a "
              f"stash\n   (putting them back hit a conflict). Recover them with:\n"
              f"       git stash pop\n   and do not run this again until that is done.")
        return 2

    after = git("rev-parse", "HEAD").stdout.strip()
    print(f"\nBrought in {behind} commit(s): {before[:8]} -> {after[:8]}"
          + (f", with your {ahead} unpushed commit(s) replayed on top" if ahead else ""))

    gone = missing_library_files()
    if gone:
        print(f"\nNote: the index now lists {len(gone)} file(s) that are not in garden/raw/ on "
              "this computer.\n  raw/ is not in git, so files added on your other computer do "
              "not travel with the\n  index. Copy them over before rebuilding the index here — "
              "the rebuild will refuse until you do.")
        for f in gone[:8]:
            print(f"    - {f}")
        if len(gone) > 8:
            print(f"    … and {len(gone) - 8} more")

    if any(c.startswith(("garden/notes/", "garden/wiki/")) for c in changed) and \
            os.path.exists(os.path.join(ROOT, ".qmd", "index.yml")):
        print("\nNotes or the index changed, so search is behind. Run the reindex skill "
              "(or `qmd update && qmd embed`).")
    if ahead:
        print("\nYour own commits are not on the remote yet — commit-garden pushes them, "
              "or `git push`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
