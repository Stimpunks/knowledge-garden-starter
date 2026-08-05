# Putting your garden in git, for someone who has never used a terminal

You do not need to become a programmer. You need about six commands, and you can forget
most of them again afterwards.

The reason to bother is not collaboration and not backup, though you get both. It is that a
history makes changing your mind cheap. Once every version of your writing is recoverable,
you stop being careful with your own work in the way that stops you working. **Version
control is mercy, made structural.**

---

## What a terminal actually is

A text box where you type the name of a thing you want to happen, and press return. That is
all. It is not a hacker interface and there is nothing in it that judges you.

On a Mac, press `⌘ + space`, type `Terminal`, press return. You will see something ending in
`$` or `%`. That is a prompt, waiting.

**Two commands to feel at home:**

```bash
pwd
```

*Print working directory* — where am I? It answers with a path.

```bash
ls
```

*List* — what is in here? It answers with names.

Those two are unable to change anything. Type them as often as you like. When you feel lost,
`pwd` and `ls` tell you where you are and what is around you, which is usually enough.

**To move somewhere:**

```bash
cd ~/Documents/my-garden
```

*Change directory.* The `~` means your home folder. If the path has spaces in it, put quotes
around the whole thing: `cd "~/Documents/my garden"`.

**A shortcut worth knowing:** in Finder, drag a folder onto the Terminal window and it types
the path for you, correctly, including the spaces. You do not have to type paths by hand.

---

## The four commands that make a history

Do these once, inside your garden folder.

### 1. Start keeping history

```bash
git init
```

Creates a hidden `.git` folder. Nothing else changes — your files are untouched. Git is now
*watching* the folder, but it has not recorded anything yet.

### 2. Choose what to record

```bash
git add .
```

The `.` means "everything here." This stages your files — it says *these are the things I
want in the next snapshot.* Still nothing permanent.

### 3. Take the snapshot

```bash
git commit -m "My garden, day one"
```

This is the real one. It records the current state of everything you staged, with your note
about why. That snapshot is now permanent and recoverable, forever.

The text after `-m` is the message. Write it for a stranger — which is to say, for yourself
in eight months. *"Added the Milton papers and rewrote the monotropism index"* is worth
writing. *"Update"* is not.

### 4. Do it again tomorrow

```bash
git add .
git commit -m "what I changed and why"
```

That is the whole loop. `add`, `commit`, repeat. Everything else in git is optional.

---

## Seeing what you have

```bash
git status
```

What has changed since the last snapshot. Run this constantly. It is the most useful command
in git and it changes nothing.

```bash
git log --oneline
```

Your history, one line per snapshot. This is the thing you built. After a month it is a
record of how your thinking moved, which no folder of files can show you.

```bash
git diff
```

Exactly what changed, line by line — removals marked `-`, additions marked `+`. Press `q` to
get out of it.

Diffs are worth getting comfortable with for one specific reason: **a diff is how a human
supervises a machine.** If you ever let an AI edit your files, the diff is where you see what
it actually did rather than what it claimed.

---

## What can go wrong, and what to do

**Almost nothing you have typed above can lose your work.** `init`, `add`, `commit`,
`status`, `log`, and `diff` either record things or report things. None of them delete.

Things that genuinely can destroy uncommitted work, so **do not paste these because someone
on the internet suggested them**:

- `git reset --hard` — throws away changes since the last snapshot
- `git checkout .` / `git restore .` — same
- `git clean -fd` — deletes files git is not tracking

The safe habit: **commit before you try anything you do not understand.** A snapshot is free
and it makes everything afterwards reversible.

### Common stumbles

| What you see | What it means | What to do |
|---|---|---|
| `not a git repository` | You are not in the garden folder | `pwd` to see where you are, then `cd` to the right place |
| `Author identity unknown` | Git wants to know who you are | Run the two `git config` lines it prints |
| `nothing to commit, working tree clean` | Nothing changed since last time | Nothing is wrong. This is success. |
| Editor opens and traps you | You forgot `-m "message"` | Type `:q!` and press return, then redo with `-m` |
| `command not found: git` | Git is not installed | On a Mac, run `git --version` and accept the install prompt |

**If you are stuck, `git status` first.** It usually tells you what git thinks the problem is
in plainer language than the error did.

---

## Sending it somewhere else (optional)

Everything above works entirely on your own machine and is already a real history. You only
need this part if you want an offsite copy.

Make an empty repository on GitHub, then:

```bash
git remote add origin git@github.com:yourname/your-garden.git
git push -u origin main
```

After that, `git push` on its own sends up anything you have committed.

**Think before you push.** A pushed repository is a copy that exists somewhere you do not
control. If your garden holds anything you would not hand to a stranger, make the repository
private — or leave it off GitHub entirely and let a local backup handle it. A history is
useful; publication is a separate decision.

---

## What "good" looks like after a week

- You can get to your garden folder without thinking about it.
- You commit when you finish something, with a message you would understand later.
- You have run `git log` once and thought *huh, that is actually a record of my thinking.*

That is it. That is the skill. It took four commands.
