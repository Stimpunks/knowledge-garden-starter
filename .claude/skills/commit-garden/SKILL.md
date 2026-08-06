---
name: commit-garden
description: Commit and push the garden's text — notes, index, and config — with a message that says what changed, guarded against mass deletions and placeholder messages. Use when the user says "commit my notes", "back this up", "save my work", "commit the garden", or wants today's writing safely offsite.
---

# commit-garden

Gets the user's writing into git and offsite. Purely mechanical — no analysis, no
reorganising, no rewriting anything.

**Use the script. Do not assemble `git add`/`commit` by hand.**

```bash
python3 .claude/skills/commit-garden/commit-garden.py -m "Notes from Tuesday: three papers on monotropism, plus index rebuild"
```

Other forms: `-F -` reads the message from stdin (easier for multi-line), `--dry-run` shows
what would happen and commits nothing, `--no-push` keeps it local, `--max-deletes N` raises
the deletion limit.

## Why a script and not just `git add -A`

Because the three mistakes worth preventing are all invisible at the moment you make them,
and a rule in a file is a suggestion where a non-zero exit is a refusal. The script:

- **Refuses a mass deletion** (more than 25 staged deletes). This is the important one. An
  uncommitted deletion is one `git restore` away; a committed one is archaeology. When it
  refuses, it prints the exact recovery command.
- **Refuses a placeholder message** — "update", "wip", "fix", or any subject under 12
  characters.
- **Reports whether `garden/raw/` is actually in the commit**, because it is git-ignored by
  default. A successful push may protect none of the library, and you should never let a
  green checkmark imply otherwise.
- **Diagnoses a failed push** instead of retrying blindly — no remote, wrong remote,
  behind the remote, or an auth problem each get the one command that fixes them.

## Steps

1. **Read the diff before writing a message about it.** The message is supposed to come
   *from* the diff. This is the whole reason the skill exists:

   ```bash
   git status --short
   git diff --stat
   ```

2. **Run the script with a real message.** Write it for the user in eight months. *"Added
   the Milton papers and retitled six opaque filenames"* is worth having. *"Update"* is not
   — it costs the same to type and tells them nothing. The script will reject the second one.

3. **Report what went in, and what was left out.** Counts by area, not a file dump. The
   script prints exactly this; pass it along rather than re-summarising it:
   *"Committed a1b2c3d — 9 files: 6 in garden/notes/, 2 in garden/wiki/, 1 config. Pushed."*

   **Include its `garden/raw/` line.** If the library is ignored, say so out loud rather
   than letting the user believe a commit protected their PDFs.

## When a guard refuses

**That is the system working. Report it and stop.**

Do not raise `--max-deletes` to make a surprise go away, and do not reword a message just
enough to slip past the length check. If 400 files are staged for deletion, something
deleted them — find out what before making it history. The refusal is the last moment when
the answer is still a one-line `git restore`.

If the deletions really are intended, say so in the message and pass the explicit count.
That is a different act from silencing the guard: it leaves a record of the decision.

## Rules

- **Never rewrite history.** No amend, no rebase, no force. This skill only moves forward,
  and the script has no flags for any of it. If a commit message is wrong, the fix is a new
  commit, not a rewritten one — especially on a repository anyone else has pulled.
- **Never reorganise or reformat the user's notes** on the way past. Commit what is on
  disk, untouched.
- **A clean tree is a no-op, not a problem.** Say so and stop. Do not invent work to commit.
- If something looks half-finished, **ask before committing it.** A commit is cheap; a
  confusing history is not.

## Note

Committing is not the same as publishing. If the remote is public, everything in this commit
becomes public — and on a public repository, a commit is effectively permanent even if you
delete it later. If the garden holds anything the user would not hand to a stranger, that is
a conversation to have *before* the first push, not after.
