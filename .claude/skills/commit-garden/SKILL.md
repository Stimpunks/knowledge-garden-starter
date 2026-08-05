---
name: commit-garden
description: Commit and push the garden's text — notes, index, and config — with a message that says what changed. Use when the user says "commit my notes", "back this up", "save my work", "commit the garden", or wants today's writing safely offsite.
---

# commit-garden

Gets the user's writing into git and offsite. Purely mechanical — no analysis, no
reorganising, no rewriting anything.

## Steps

1. **See what is actually pending.** Never commit blind:

   ```bash
   git -C . status --short
   ```

   If the tree is clean, **say so and stop.** A clean tree is a no-op, not a problem. Do not
   invent work to commit.

2. **Look at what changed before writing a message about it.** If the diff is small, read it:

   ```bash
   git diff --stat
   ```

3. **Commit with a real message.**

   ```bash
   git add -A
   git commit -m "Notes from Tuesday: three papers on monotropism, plus index rebuild"
   ```

   Write the message for the user in eight months. *"Added the Milton papers and retitled six
   opaque filenames"* is worth having. *"Update"* is not — it costs the same to type and
   tells them nothing.

4. **Push, if there is somewhere to push to.**

   ```bash
   git push
   ```

   **If push fails, do not panic and do not retry blindly.** Read the error:
   - *"does not appear to be a git repository"* or no remote → there is no offsite copy yet.
     The commit is safe locally. Offer to help set up a remote.
   - *permission denied / 403* → the remote points at a repository the user cannot write to.
     This is the classic result of cloning someone else's template without detaching. Fix:
     `git remote remove origin`, then add their own.
   - *rejected, non-fast-forward* → the remote has commits they do not have. `git pull` first.

5. **Report what went in, and what you left.** Counts by area, not a file dump:
   *"Committed a1b2c3d — 9 files: 6 in notes/, 2 in wiki/, 1 config. Pushed."*

## Rules

- **`garden/raw/` may be git-ignored.** Check `.gitignore`. If it is, the library is *not*
  going offsite with this commit — it is covered by whatever backup the user has for large
  files. **Say that out loud** rather than letting them believe a commit protected their PDFs.
- **Never rewrite history.** No amend, no rebase, no force. This skill only moves forward.
- **Never reorganise or reformat the user's notes** on the way past. Commit what is on disk,
  untouched.
- If something looks half-finished, **ask before committing it.** A commit is cheap; a
  confusing history is not.

## Note

Committing is not the same as publishing. If the remote is public, everything in this commit
becomes public. If the garden holds anything the user would not hand to a stranger, that is a
conversation to have *before* the first push, not after.
