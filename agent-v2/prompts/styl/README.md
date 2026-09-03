# The style corpus goes here — and it is yours to supply

This directory is empty on purpose. It is the one part of the bot that cannot
ship with the code.

## What belongs here

One `.txt` file of prose whose **voice** the writer stage should learn from.
Paragraphs separated by a blank line. Anything from a few thousand words up.

The writer never sees the whole file. It receives three to five short
paragraphs, each chosen to illustrate a rhetorical *move* — how a piece opens,
how it gets from a concrete thing to a system, how it explains a mechanism, how
it answers its own strongest objection, how it ends. Anything longer than 900
characters is rejected, because at that length a model copies phrasing instead
of learning a move.

## What must NOT go here

**Somebody else's published writing.** This repository shipped with 9,383 words
of a working journalist's columns in this directory, transcribed verbatim, and
the repository is public. That is republishing someone's work, and no amount of
"it is only used as a style reference" changes what the file is.

If you want a voice that is not your own, the options that actually work are:

- your own writing, from anywhere;
- writing you hold the rights to, or have permission to use;
- text out of copyright.

## Wiring it up

The loader refuses to run against an unpinned corpus. That is deliberate: the
corpus is the one thing separating this account from a thousand others, and a
silent swap would change the voice the owner agreed to without anybody noticing.

```bash
python narzedzia/przypnij_styl.py --pokaz
```

That prints every paragraph that is the right length to be an example, with its
index. Read them, pick one per rhetorical function, then:

```bash
python narzedzia/przypnij_styl.py --wybor OPENING=12,CONCRETE_TO_SYSTEM=31,MECHANISM=44,COUNTERARGUMENT=58,ENDING=70
```

That writes `przypiecia.json` next to the corpus: the file's SHA-256, and the
index plus content hash of each chosen paragraph. Both the corpus and
`przypiecia.json` are in `.gitignore` — the pins describe your corpus, so they
have no meaning in anybody else's checkout.

Edit the corpus later and the run stops with a message naming what changed.
Re-run the command above to re-pin.

## What happens without it

The writer stage refuses to start and says so. Every other path — notes,
comments, restacks, research — runs normally. You can operate the bot for a
long time before you need this, and it is better to have no corpus than a
borrowed one.
