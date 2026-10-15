---
name: pull-garden
description: Bring this computer up to date with the garden's remote — show what is coming in, pull it safely, and back out cleanly on any conflict instead of leaving a half-finished rebase. Use when the user says "pull my garden", "pull", "catch up", "get my changes from the other computer", "am I up to date", or when commit-garden refuses because the remote has commits this computer lacks.
---

# pull-garden

The other half of `commit-garden`. That skill sends work out; this one brings it in. It
matters as soon as a garden lives on two computers — a laptop and a desktop, say.

## Steps

1. **Look first.** This changes nothing:
   ```bash
   python3 .claude/skills/pull-garden/pull-garden.py --check
   ```
   It shows how many commits are coming in, their dates and messages, and which parts of the
   garden they touch. Pass that on in a sentence — *"4 commits from your other computer, all
   in notes/ and the index"* — not as a dump.

2. **Pull:**
   ```bash
   python3 .claude/skills/pull-garden/pull-garden.py
   ```
   Uncommitted changes are fine. They are set aside during the pull and put back after.

3. **Report what came in**, and pass on the two notes it may print:
   - **Library files missing here.** `garden/raw/` is not in git, so files added on the other
     computer do not come with the index. The user has to copy them over before the index can
     be rebuilt on this computer. Rebuilding first will refuse, correctly.
   - **Search is behind.** If notes or the index changed, offer the `reindex` skill.

## When it refuses

**That is the system working. Report it and stop.**

- **A conflict.** The same file was changed on both computers. The script has already run
  `git rebase --abort` and put everything back exactly as it was. Resolving it is a
  *decision* about what the file should say, so ask the user. Re-running will give the same
  refusal. If the collision is in `garden/wiki/` — the generated index — the usual fix is to
  take the remote copy and rebuild.
- **Changes left in a stash.** The pull worked, but putting the user's uncommitted changes
  back hit a conflict, so they are sitting in a stash. Say so plainly, and that
  `git stash pop` brings them back. **Do not run the pull again until that is resolved.**

## Rules

- **Never leave a half-finished rebase**, and never start one by hand. The script exists so
  that nobody has to meet that state while learning git.
- **Never force-push, reset, or rewrite history** to make a conflict go away.
- **It does not commit and does not push.** Bringing work in and sending it out stay
  separate. After a pull, `commit-garden` is the way out.
