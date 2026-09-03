# What was removed, and where it stood

This repository began as one account's working tree. Making it something other
people can point at their own accounts meant taking that account out of it —
its name, its server, its subscribers, its published articles, its subject, and
the voice it borrowed.

Git history here begins at one commit, on purpose. That means this file is the
**only** record of what was taken out and where it was. It exists so that a
problem traced back to one of these edits can be understood rather than
guessed at.

Nothing below is a list of strings to search for. The list the audit actually
uses is `narzedzia/dawne-tozsamosci.txt`, which is gitignored — a list of
things you do not want published cannot itself be published.
`dawne-tozsamosci.example.txt` shows its shape.

---

## 1. The account

| What | Where it stood | Now |
|---|---|---|
| Substack handle | two independent constants — `config.SUBSTACK_HANDLE` and a second copy in `browser.py` | one constant; `browser.PROFIL_HANDLE = config.SUBSTACK_HANDLE`, and the audit asserts they are the same object |
| publication name | **no constant at all.** Written out in nine prompts, two system messages and both style profiles | `config.NAZWA_MARKI`, injected into every prompt |
| panel URLs | composed from a literal handle | composed from the constant |
| owner's country of residence | a comment in `config.py` explaining a timezone choice | removed; the reasoning stayed |
| owner's username | file paths in comments | removed |

The brand was the hardest of these, and not because it was in many places. In
`SCOUT_SYSTEM` it was **split across two adjacent string literals**, which
Python joins only at runtime. It survived an entire scrubbing pass because the
full name was never present in the source — only two fragments with a quote
between them. The audit now evaluates concatenated literal *values* with
`ast.literal_eval` and scans the result.

## 2. The server

| What | Where it stood |
|---|---|
| production IP | `wdroz.sh`, systemd units, several comments |
| deploy host alias | `wdroz.sh`, docs |
| two SSH key names | `wdroz.sh`, INSTALL |
| the branch used for live testing | test comments |

Replaced with placeholders and a description of what the value is for. The
deploy script now says what it needs rather than where it used to point.

## 3. Third parties

Twelve YouTube channels and their presenters' names stood in `config.py`
comments, in `korpus_kanalow.py`, and in the fixtures of six tests. Five real
people were named. Roughly thirty other Substack handles appeared in test
fixtures — real accounts the bot had interacted with.

All replaced with neutral placeholders (`Kanal Newsowy`, `@autor1`,
`@czytelnik4`). The replacements are **distinct**: collapsing two real channels
onto one placeholder once turned three channels into two and broke a test for a
reason that had nothing to do with the code.

Two company names and one research system were in a test fixture that had been
copied from the text of a real published note. One model's real name and
version appeared in 37 places across 8 files.

## 4. Published articles

Seven article titles, each findable in a search engine, stood in:

- `stages.py` — two in a single comment explaining the diversity rule
- `run.py` — one inside the fact-check comment, **wrapped across a line**
- test docstrings and fixtures — four more
- `test_podlogi_playbook.py` — a file glob, `0025-*was-never*.md`

The `run.py` one is worth its own paragraph. Identity patterns use `\s+`
instead of a space specifically so a wrapped phrase still matches. That is not
enough inside a **comment**, because the continuation line begins with `#`,
which is not whitespace. The title sat there through every green audit until it
was found by reading. The audit now scans three views of every file: the
original, one with line-wraps joined, and one with quotes, backticks, plus
signs and backslashes removed.

Article *prose* was removed too, not just titles: `test_podlogi_playbook.py`
carried seven paragraphs of a published article verbatim as gate fixtures. The
gates react to phrases, not to subject matter, so the fixtures were rewritten
with the same triggers and neutral content.

## 5. The previous subject

The bot had already been re-pointed once before, and traces of **both** earlier
subjects were still in the tree.

`skaut.md` alone carried thirteen passages that argued about the previous
subject — its worn-out claims, its typical objects, its famous cases — while
the first line said the publication was about `{nisza}`. One of them
(`flushable wipes`) was from the subject before that, so it had survived two
re-pointings.

The fix was not deletion. The *method* in those briefs is the product; the
*examples* were the problem. Examples moved out to configuration
(`config.PRZYKLADY_NISZY`, five optional lists), injected by
`stages._pola_wspolne()`. An empty list does not mean "skip": the brief then
tells the model to work out the equivalent for its own subject, which is worse
than a real list but always about the right field.

The same applied to the editorial angle, which was hard-coded into **nine**
briefs — six of them as "what these systems actually do". That single phrase
made every account a technology publication regardless of its configured
subject. It is now `config.KAT_REDAKCYJNY`.

Two prompts described a real legislative failure with the state, the committee,
the bill number and the publication date. Two more named a real company, a real
institute and its published figures. All are now described by the *kind* of
document, which is what made the lesson work in the first place.

## 6. The style corpus

`agent-v2/prompts/styl/article_style_samples_v1.txt` held **9,383 words of a
working journalist's published columns**, transcribed verbatim, in a public
repository. It was the corpus the writer stage imitated.

This is not a naming problem. It is republishing somebody's work, and "we only
use it as a style reference" does not change what the file is.

Removed from the tree and from tracking. With it went
`config.STYLE_CORPUS_SHA256` and `style.APPROVED_EXAMPLES`, which described
that one file — paragraph 65 means nothing in a corpus nobody else has. The
pinning mechanism is unchanged and now lives beside whatever corpus you supply,
generated by `narzedzia/przypnij_styl.py`. Proof the refactor changed nothing:
run against the same file, the tool produced exactly the hashes that had been
in the code.

## 7. Data and dead code

| What | Where |
|---|---|
| an abandoned prototype's tree | 11 SQLite databases and an activity log, present only in history |
| `agent-v2/wariant-ai/dane/opisane.json` | two real production topics with filenames and timestamps; nothing in the code referenced it |
| nine git tags | `archive/stary-agent-*`, `prototyp-gpt-2026-08`, `v1`, `v2` — every one pointing into the old history |
| six documents about one installation | moved out of the product |

## 8. What this cost

Twenty tests compared current code against named past commits. Those commits no
longer exist, so `tests/historia.py` makes them skip cleanly and say why,
rather than fail. They no longer prove what they used to prove. That is the
price of a history that begins here, and it is written down rather than hidden.

## 9. How to check the claim rather than believe it

```bash
python narzedzia/audyt.py --historia
```

Scans the working tree and every commit for identity patterns, secrets, keys,
session files, subscriber lists and databases. Section 9 is a counterproof: it
builds files that *should* trip the audit and fails if they do not, because an
audit that catches nothing looks exactly like a clean repository.
