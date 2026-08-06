# Working with Claude on your garden

You can run this whole thing by hand. This document is for when you would rather not.

The setup below is what we actually use: [Claude Code](https://claude.com/claude-code) inside
the Claude desktop app, pointed at the garden folder, as the main way of maintaining it. Not a
chatbot you paste files into — a session that can read your library, rebuild your index, and
commit your work, while you stay the one deciding what any of it means.

---

## Why this template already knows about Claude

Two files do the work, and they are both plain text you can read and change:

- **`CLAUDE.md`** at the top of the repo. Claude reads it at the start of every session, so
  the rules — *never edit `raw/`*, *never hand-edit the generated index* — arrive before any
  work does. Rules written down where the work happens beat rules you have to remember to
  repeat.
- **`.claude/skills/`** — five named tools, each a plain-language instruction file. You invoke
  one by describing what you want in ordinary words.

| Skill | Say something like |
|---|---|
| **add-to-garden** | *"add this paper to my garden"* |
| **tend-the-garden** | *"build my index"* · *"what's in Unidentified?"* |
| **ask-my-garden** | *"what do I have on monotropism?"* |
| **commit-garden** | *"commit my notes"* |
| **check-readability** | *"is this readable?"* |

**Narrow on purpose.** A tool that does one thing can be trusted, and when it goes wrong the
failure is legible. None of them touch your originals.

---

## Getting set up

1. **Install the Claude desktop app** and sign in. Claude Code is also available as a
   terminal command and as editor extensions — the app is the gentlest starting point, and it
   is what these notes assume.
2. **Point a session at your garden folder** — the directory containing `garden/`, `CLAUDE.md`,
   and `.claude/`. Claude Code works on a directory, so it needs to be the *right* directory:
   if `CLAUDE.md` is not in it, the rules will not load and the skills will not appear.
3. **Check it worked.** Ask *"what are the rules for this garden?"* If it can tell you that
   `raw/` is never edited, it read `CLAUDE.md`. If it cannot, you are in the wrong folder.

The exact menus move as the app changes, so if a label here does not match what you see,
trust the app and the [official documentation](https://claude.com/claude-code) over this page.

---

## A first week that works

Nothing here needs the terminal except where noted, and Claude can run those parts for you.

**1. Make it yours.** Create your repository from the template, clone it, and open it in the
app. See the [README](../README.md) for the three routes.

**2. Put some real things in.** Drop a handful of PDFs into `garden/raw/`. Set up the
[Obsidian Web Clipper](https://obsidian.md/help/web-clipper) to save pages there too — the
[full write-up is here](https://stimpunks.org/fieldguide/it/filling-the-garden/), and the part
that matters is that every clipping keeps its source URL and clip date.

**3. Write a few notes.** In `garden/notes/`, using Obsidian or Ulysses or anything. Do not
try to be organised yet. Twenty real files beat a perfect empty structure.

**4. Then ask Claude to build the index.** *"Build my index."* This is the moment the thing
starts feeling like a system: a front page, a page per shelf, every entry pointing at a real
file. It will probably also tell you the shelves in `_config.json` are still the placeholders
and offer to fix them — let it, because that is the file that makes the index yours.

**5. Work the Unidentified pile.** *"What's in Unidentified?"* Claude opens the files it can
read, records real titles in `_overrides.json`, and regenerates. **The originals never move.**
Watch the count drop; that is the system getting smarter rather than merely bigger.

**6. Commit it.** *"Commit my notes."* You now have a history of your own thinking.

**7. Ask it something.** *"What do I have on X?"* — and pay close attention to whether the
answer cites your files. That is the whole game.

---

## The thing to hold onto

**Claude writes the index here. It does not write the sources, and it does not get to answer
for them.**

That boundary is what makes the garden worth having, and it is the one you have to enforce,
because a language model is *most* fluent exactly where it is least grounded. A confident
paragraph with no file behind it is worse than an admitted gap — the gap tells you what to go
and read; the paragraph tells you nothing and feels like it told you everything.

So the `ask-my-garden` skill is written to cite a file beside every claim and to say *"the
garden does not say this"* when it does not. **If you ever get an answer with no citations,
that is a bug, and it is worth saying so out loud** — to Claude, in the session. It will
usually go and look properly.

## What to check, at least once

Do these once so you know the guardrails are real rather than decorative:

- **Ask it to break a rule.** *"Rename that file in raw/ to something tidier."* It should
  refuse and explain why. A rule nobody has tested is a hope.
- **Ask a question you know is not covered.** It should say the garden is silent instead of
  producing something plausible.
- **Read a diff before you accept it.** `git diff` after a session that edited config or
  overrides. A diff is how a human supervises a machine.

One guardrail you may meet without asking for it: **`commit-garden` refuses to commit a
message like "update", and refuses outright if a commit would delete more than 25 files.**
Seeing `REFUSED` is not a bug and you have not broken anything — it means the commit stopped
while a mistake was still one command away from being undone. If Claude responds to a refusal
by working around it, that is worth pushing back on.

None of this is distrust. It is the same reason you keep the originals untouched: so that
when you need to know where something came from, you can find out.
