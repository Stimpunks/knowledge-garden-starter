#!/usr/bin/env python3
"""Commit the garden's text layer, with the guards that a hand-typed `git add -A` has none of.

Ordinary commits do not need a script. This one exists because three specific mistakes are
easy to make, hard to notice, and expensive to undo — and because an instruction in a prose
file is a suggestion, while a non-zero exit is a refusal.

    python3 .claude/skills/commit-garden/commit-garden.py -m "Add the Milton papers; retitle six opaque files"
    python3 .claude/skills/commit-garden/commit-garden.py -F -          # message on stdin
    python3 .claude/skills/commit-garden/commit-garden.py -m "..." --dry-run

Exit status: 0 committed (or nothing to commit), 2 a guard refused, 1 an error.

WHAT IT GUARDS, and why each one is here:

  * Mass deletion. If the staged set removes more than --max-deletes files, the run stops
    before anything is committed. This is the one that matters most. A sync bug in the
    upstream system this template came from deleted 1,014 of 1,468 tracked files in one
    pass; the only reason that was recoverable is that it had not yet been committed on top
    of. An uncommitted deletion is a `git restore` away. A committed one is archaeology.

  * Placeholder messages. "update", "wip", "changes" are rejected. Writing a real sentence
    is the entire difference between a history you can read in eight months and a wall of
    noise, and it costs the same keystrokes.

  * Whether your originals are actually in the commit. `garden/raw/` is git-ignored by
    default in this template, so a successful push may protect none of your library. That
    is a legitimate setup — but you should know which one you have, so this reports it
    every run rather than letting a green checkmark imply more than it means.

It only ever moves forward: no amend, no rebase, no force, no history rewriting. There are
no flags for those on purpose.
"""

import argparse
import os
import subprocess
import sys

# Messages that cost the same to type as a real one and tell you nothing. The subject is
# also rejected for being too short — "Fix bug" passes this set and still says nothing.
LAZY = {"update", "updates", "updated", "changes", "change", "changed", "wip", "fix",
        "fixes", "fixed", "commit", "misc", "stuff", "cleanup", "tidy", "save", "sync",
        "checkpoint", "snapshot", "notes", "."}


def git(*args, root=None, check=False):
    """Run a git command and hand back the completed process. Never raises on exit code."""
    return subprocess.run(["git", "-C", root or ".", *args],
                          capture_output=True, text=True, check=check)


def repo_root():
    r = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("ERROR: not inside a git repository.\n"
                 "  This garden has no version history yet. From the garden's folder:\n"
                 "    git init && git add -A && git commit -m 'My garden, first commit'")
    return r.stdout.strip()


def check_message(msg):
    """Return a refusal string, or None if the message is worth having."""
    body = msg.strip()
    if not body:
        return "empty commit message"
    subject = body.splitlines()[0].strip().rstrip(".")
    if len(subject) < 12:
        return (f"subject is {len(subject)} chars — say what changed, not just that it did")
    bare = subject.lower().split(":")[-1].strip()
    if bare in LAZY or subject.lower() in LAZY:
        return f"placeholder subject {subject!r} — a message like that is why this guard exists"
    return None


def pending(root):
    """Everything that would go into the commit, grouped: {'A': [...], 'M': [...], ...}.

    Read from `git status --porcelain`, NOT from the index, so that previewing costs nothing
    and mutates nothing. `git add -A` happens once, immediately before the commit — a
    --dry-run that silently staged the whole tree would destroy any partial staging the user
    had set up, which is a rude thing for a preview to do.
    """
    groups = {}
    # -uall matters: the default collapses a new directory into one "?? dir/" entry, so a
    # commit adding 30 notes would report "+1 added". A count that under-reports the size of
    # the commit is the exact failure this script exists to prevent.
    for line in git("status", "--porcelain", "-uall", root=root).stdout.splitlines():
        if not line.strip():
            continue
        xy, path = line[:2], line[3:]
        if xy == "??":
            code = "A"                          # untracked: `add -A` will add it
        else:
            code = (xy[0] if xy[0] != " " else xy[1]).upper()
        if code == "R" and " -> " in path:
            path = path.split(" -> ", 1)[1]     # report the destination
        path = path.strip('"')
        groups.setdefault(code, []).append(path)
    return groups


def by_area(paths, limit=8):
    """Counts by top-level area, so the report is 'six in notes/' not a file dump."""
    tally = {}
    for p in paths:
        if "/" in p:
            head = p.split("/")[0] + "/"
            if head == "garden/" and p.count("/") >= 2:
                head = "/".join(p.split("/")[:2]) + "/"   # garden/notes/ — the useful grain
        else:
            head = p                            # a root-level file is its own name, no slash
        tally[head] = tally.get(head, 0) + 1
    ranked = sorted(tally.items(), key=lambda kv: -kv[1])
    shown = ", ".join(f"{n} in {a}" if a.endswith("/") else f"{a}" for a, n in ranked[:limit])
    if len(ranked) > limit:
        shown += f", and {len(ranked) - limit} more"
    return shown


def raw_state(root):
    """Is garden/raw/ in this repo's history, or only on this disk? Report, never refuse.

    Both answers are legitimate — .gitignore ships it ignored and documents un-ignoring a
    small text-only library. What is NOT legitimate is not knowing, and believing a push
    backed up a gigabyte of PDFs that git never saw.
    """
    raw = os.path.join(root, "garden", "raw")
    if not os.path.isdir(raw):
        return None

    # The folder's own README.md is un-ignored by .gitignore so the empty folder survives a
    # clone. It is scaffolding, not a source — counting it would report "1 of 1 tracked" for
    # a library git has never seen, which is the precise false reassurance this exists to stop.
    def is_source(p):
        return os.path.basename(p) not in ("README.md", ".DS_Store", ".gitkeep")

    n_tracked = len([p for p in git("ls-files", "garden/raw", root=root).stdout.splitlines()
                     if p and is_source(p)])
    on_disk = sum(len([f for f in files if is_source(f)]) for _, _, files in os.walk(raw))

    if on_disk == 0:
        return "garden/raw/: empty — nothing stored yet, so nothing to protect."
    if n_tracked == 0:
        return (f"garden/raw/: 0 of {on_disk} sources tracked (git-ignored). Your originals "
                f"are NOT in this commit and will not reach the remote. Whatever backs up "
                f"large files on this machine is their only copy — check that it does.")
    if n_tracked < on_disk:
        return (f"garden/raw/: {n_tracked} of {on_disk} sources tracked — the other "
                f"{on_disk - n_tracked} are ignored and are NOT going offsite with this push.")
    return (f"garden/raw/: all {on_disk} sources tracked — your originals ARE in git and go "
            f"offsite with this push.")


def diagnose_push(stderr):
    """Turn git's push failure into the one sentence that names the actual fix."""
    e = stderr.lower()
    if "does not appear to be a git repository" in e or "no configured push destination" in e \
            or "'origin' does not appear" in e:
        return ("no remote configured, so there is no offsite copy yet. The commit is safe "
                "locally. Create an empty repo on your host, then:\n"
                "    git remote add origin <url> && git push -u origin HEAD")
    if "permission denied" in e or "403" in e or "not authorized" in e:
        return ("the remote points at a repository you cannot write to — the classic result "
                "of cloning someone else's template without detaching. Fix:\n"
                "    git remote remove origin && git remote add origin <your-own-url>")
    if "non-fast-forward" in e or "rejected" in e or "fetch first" in e:
        return ("the remote has commits you do not. Pull first, then push again:\n"
                "    git pull --rebase && git push\n"
                "  (Do NOT force-push to resolve this.)")
    if "could not read from remote" in e or "host key" in e or "authentication failed" in e:
        return ("could not authenticate to the remote. The commit is saved locally and the "
                "next successful push carries it up — usually an unlocked-key problem.")
    return "see git's message above. The commit is saved locally either way."


def main():
    ap = argparse.ArgumentParser(description="Commit the garden's text layer, guarded.")
    ap.add_argument("-m", "--message", help="commit message")
    ap.add_argument("-F", "--file", help="read the message from a file, or - for stdin")
    ap.add_argument("--max-deletes", type=int, default=25,
                    help="refuse if the staged set deletes more than this many files (default 25)")
    ap.add_argument("--dry-run", action="store_true", help="show what would happen; commit nothing")
    ap.add_argument("--no-push", action="store_true", help="commit locally, do not push")
    a = ap.parse_args()

    root = repo_root()

    msg = a.message
    if a.file:
        msg = sys.stdin.read() if a.file == "-" else open(a.file).read()
    if not msg:
        sys.exit("ERROR: no message. Use -m \"what changed\" or -F - to read it from stdin.\n"
                 "  Read the diff first; the message is supposed to come from it.")

    if bad := check_message(msg):
        print(f"REFUSED: {bad}", file=sys.stderr)
        print("\n  Write a sentence for whoever reads this in eight months. "
              "'Added the Milton papers and retitled six opaque filenames' is worth having.",
              file=sys.stderr)
        return 2

    if not git("status", "--porcelain", root=root).stdout.strip():
        print("Nothing to commit — the tree is clean. That is a no-op, not a problem.")
        return 0

    groups = pending(root)
    adds, mods = groups.get("A", []), groups.get("M", [])
    dels, rens = groups.get("D", []), groups.get("R", [])

    if len(dels) > a.max_deletes:
        print(f"REFUSED: this commit would delete {len(dels)} files "
              f"(limit {a.max_deletes}).", file=sys.stderr)
        print(f"  Deleting from: {by_area(dels)}", file=sys.stderr)
        print("\n  Nothing has been committed. If the deletions are wrong, they are still\n"
              "  undoable right now — that is the whole point of stopping here:\n"
              "      git reset && git restore --worktree -- .\n"
              "  If they are genuinely intended, re-run with --max-deletes "
              f"{len(dels)} and say so in the message.", file=sys.stderr)
        print("\n  Do not raise the limit to make a surprise go away. Look at the list first.",
              file=sys.stderr)
        return 2

    print(f"Staged: +{len(adds)} added, ~{len(mods)} modified, -{len(dels)} deleted"
          + (f", {len(rens)} renamed" if rens else ""))
    for label, paths in (("added", adds), ("modified", mods), ("deleted", dels)):
        if paths:
            print(f"  {label}: {by_area(paths)}")

    if state := raw_state(root):
        print(f"\n{state}")

    if a.dry_run:
        print("\n--dry-run: nothing committed, nothing staged.")
        return 0

    git("add", "-A", root=root)                 # first mutation of the run, and the only one
    r = git("commit", "-m", msg.strip(), root=root)
    if r.returncode != 0:
        print(r.stdout + r.stderr, file=sys.stderr)
        return 1
    sha = git("rev-parse", "--short", "HEAD", root=root).stdout.strip()
    subject = msg.strip().splitlines()[0]
    print(f"\nCommitted {sha} — {subject}")

    if a.no_push:
        print("Not pushed (--no-push). There is no offsite copy of this commit yet.")
        return 0

    p = git("push", root=root)
    if p.returncode == 0:
        print("Pushed.")
    else:
        print(f"\nPush failed — {diagnose_push(p.stderr)}")
        print("\n  This is not a lost commit. It is on this machine, in history, and the "
              "next successful push carries it up.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
