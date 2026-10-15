# raw/ — your originals. Never edited.

Everything you read, save, or are given goes in here **untouched**. Do not rename,
reformat, tidy, or reorganise anything in this folder, ever.

That one rule is the whole system. It is what makes this a record you can trust and
cite years from now, instead of a pile you have quietly been editing.

Keep it **flat** — no subfolders. Sorting happens in `../wiki/`, where changing your
mind costs nothing. Moving files around costs you the ability to trust your own links.

If something in here looks wrong, leave it wrong and write the correction somewhere else.

**Copy files out of here; never hard-link them.** A hard link is not a copy — it is the same
file under a second name, so anything that writes to the link writes into `raw/`. If you build
a website or an export from your garden, copy (on a Mac, `cp -c` makes an instant clone that
is safe to write to). This one has happened: a site build linked originals out to save space,
two names collided, and the build wrote into an original.
