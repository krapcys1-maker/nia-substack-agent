# Troubleshooting

Two kinds of entry, and the difference matters more than the order.

**Part 1 — what will bite you.** Things that still happen on a fresh clone.
Read this before your first run.

**Part 2 — what already bit us.** Problems that are fixed in the code you are
holding. They are here because a fix only makes sense if you know what it was
for, and because each one is a class of mistake rather than a one-off.

Every entry has a **symptom** (what you actually see), a **meaning** (what it
really is) and a **what to do**.

---

# Part 1 — what will bite you

## 1.1 Two tests fail on a fresh clone, and neither is a bug

**Symptom.** The whole suite gives **123 passed, 2 failed**:

```bash
for t in agent-v2/tests/test_*.py; do python "$t"; done
```

```
test_czas
test_zapora_platnych_wywolan
```

**Meaning.** Neither is about the code.

| test | what it needs |
|---|---|
| `test_czas` | `SIGTERM`. Windows has no POSIX signals, so the test cannot run at all |
| `test_zapora_platnych_wywolan` | a key present in `agent-v2/.env` — it checks that the paid-call guard fires, and the guard cannot fire when there is nothing to guard |

**What to do.** Put placeholder keys in `agent-v2/.env` and the second one
passes. The first passes on Linux and on the server. Anything else red is real.

## 1.2 Twenty tests skip, saying they need commits that do not exist

**Symptom.**

```
POMINIETY: kontrdowod wymaga commitow: e88b456
=== POMINIETY (brak historii odniesienia) ===
```

**Meaning.** By design, and it has a price.

The project's doctrine requires a counterproof to be **reproduced, not
described**: a test claiming "before the fix this was broken" loads the old code
from a pinned commit and runs it. Pinned to a SHA, never to `HEAD` — a test
measured against `HEAD` stops meaning anything the moment you commit the fix it
guards.

This repository's history begins at one commit, on purpose (see
[CLEANING_LOG.md](CLEANING_LOG.md)). Those reference commits are gone.
**Clean history and SHA-pinned counterproofs are mutually exclusive** — there is
no arrangement where you publish a scrubbed history and these tests still work.

**What to do.** Nothing. `agent-v2/tests/historia.py` makes the skip explicit and
countable rather than a fake pass: it checks `git cat-file -e <sha>^{commit}`,
prints which commits are missing, and exits 0. The rest of each file still runs.

One trap if you write a new one: the guard must stand **before the first use of
git**, not before the first assertion. Two tests call `git show` at module level;
a guard placed "after the imports" sat behind the thing it was guarding and
changed nothing.

## 1.3 The article writer reads files from outside `agent-v2/`

**Symptom.** `agent-v2/config.py`:

```python
STYLE_PROFILES_DIR = REPO_ROOT / "style-profiles"
```

The `write` stage calls `style.load_profiles()`, which reads two files from the
repository root, not from `agent-v2/`.

**Meaning.** `agent-v2/` is **not self-contained**. Without those two files the
`write` stage raises `StyleError` and no article is produced — after the research
has been paid for.

The directory holds five files and the code reads two of them.

**What to do.** When moving the bot, take the whole repository root, not just
`agent-v2/`.

## 1.4 The writer also needs a style corpus, and this repository does not ship one

**Symptom.**

```
korpus stylu nie jest przypięty — brak .../styl/przypiecia.json
```

**Meaning.** Deliberate, and the reason is in
[CLEANING_LOG.md](CLEANING_LOG.md) §6: what used to be here was 9,383 words of a
working journalist's published columns.

**What to do.** The error message carries the three commands. In short: put your
own prose in `agent-v2/prompts/styl/`, run
`python narzedzia/przypnij_styl.py --pokaz`, then `--wybor`. Notes, comments,
restacks and research all work without it; only the article path stops.

## 1.5 Nothing sets the AI-disclosure statement on your profile

**Symptom.** No error. The account simply has no "how this is made" statement.

**Meaning.** `browser.ustaw_oswiadczenie_ai` is the only code that reads
`prompts/OSWIADCZENIE_AUTORSTWA.md` and writes that statement — and **nothing
calls it**. It was a one-off manual action.

The doctrine says the publication never lies when asked directly, and a scan for
machine-written text is asking directly. That promise is kept by a function no
timer runs.

**What to do.** Treat it as an install step: read
`agent-v2/prompts/OSWIADCZENIE_AUTORSTWA.md`, decide what your account says, and
set it by hand. No log will tell you it is missing.

## 1.6 A search term outside your own niche markers makes the bot look picky

**Symptom.** In the run log:

```
[cele] warte komentarza: 0/15
[cele] warte komentarza: 1/13
```

**Meaning.** Not the model being fussy. The bot searches with
`temat.hasla_szukania`, gets posts, and then the targeting rule correctly rejects
them because they carry none of `temat.znaki_niszy`. It is searching for the
wrong thing and rejecting the results properly.

**What to do.** `python agent-v2/tests/test_szukanie_celow.py` names every term
that carries no niche marker and tells you which stem to add.

## 1.7 Some of the five daily runs may be unable to publish

**Symptom.** In the run log:

```
okno publikacji: NIE — 23:30 u czytelnikow — poza oknem, publicznosc spi
```

**Meaning.** The systemd timers fire at fixed UTC times. The publishing window is
in **the reader's** timezone. Change `konto.strefa_czytelnika` or
`publikowanie.okno_et` and some runs land outside it — they still run, they just
never post a note.

**What to do.** `python agent-v2/tests/test_okno_publikacji.py` counts it for
you: it prints how many of the five can publish and warns when some cannot. Only
zero is an error. Widen the window, or change the times in
`agent-v2/systemd/*.timer`.

---

# Part 2 — what already bit us

These are fixed in the code you are holding. Each is kept because the mistake is
repeatable.

## 2.1 A name split across two string literals survived a full scrub — and a public release

**Symptom.** After a complete identity-removal pass, and after publishing:

```bash
grep -ril "Stara Marka Konta" .    # 0 files
```

And in the source:

```python
SCOUT_SYSTEM = (
    "You are a topic scout for the English-language Substack 'Stara Marka "
    "Konta', a publication about ..."
)
```

**Meaning.** Python joins adjacent literals. The full name is nowhere in the
**source** — there is `"Stara Marka "` and separately `"Konta'"`. Grep works on
source. The value exists only after parsing.

The old account name stood in a public repository from the first release.

**The fix, on two tracks, because one was not enough.** The audit evaluates every
assignment with `ast.literal_eval` and scans the **value**; and the brand became
`config.NAZWA_MARKI`, with the system messages built from it, so there is one
place to change instead of nine.

**The rule.** A scan of source text cannot see a value produced at parse time:
joined literals, f-strings, `+` concatenation, phrases wrapped across a line.
Anything that MUST be gone needs two scans — over the source and over the value.

## 2.2 The same phrase, wrapped across a line inside a comment

**Symptom.** The audit passed. A published article's title was sitting in
`run.py` the whole time.

**Meaning.** Identity patterns use `\s+` instead of a space precisely so a
wrapped phrase still matches. Inside a **comment** that is not enough: the
continuation line starts with `#`, which is not whitespace.

**The fix.** The audit now scans three views of every file: the original, one
with line-wraps joined, and one with quotes, backticks, plus signs and
backslashes removed. The third view exists because the account name also survived
inside the comment *explaining how it had hidden* — there, `" "` sat between the
words.

## 2.3 The key check covered 12 of 26 roles

**Symptom.** With empty keys, some stages stopped before spending anything and
others failed on an HTTP response — so the message talked about transport rather
than about a missing key.

**Meaning.** The check compared the model **id** against two constants. There are
five ids: `claude-fable-5-1` (the whole article) and `deepseek-v4-pro` (eleven
stages) were not covered.

**The fix.** `llm._dostawca(model)` resolves the provider, and both the key check
and the routing in `llm.call` use it. Adding a sixth model no longer requires
remembering this place.

## 2.4 A guard test that went green over dead code

**Symptom.** The paid-call guard reported `stages.kandydaci_z_fedreg` as healthy
while nothing in production called it.

**Meaning.** The order of conditions. The decorator check stood **before** the
"does anything call this" check, so a decorated function with zero callers
reported as covered. Two paid stages were dead, not one.

**And then the fix did nothing.** The obvious correction —

```python
if not zywe and q not in pokryte:
```

— left the behaviour unchanged, because `pokryte` is seeded five lines above from
the decorators themselves, so `q not in pokryte` was always false. It compiled,
broke no test, and did nothing. The right question turned out not to involve
`pokryte` at all: `if not zywe and not z_main`.

**The rule.** After a fix, check that the **symptom is gone**, not that the code
changed. One run and one look at the list was enough.

## 2.5 `.env.example` described a different agent

**Symptom.** It listed `ANTHROPIC_MODEL_FAST`, `ANTHROPIC_MODEL_QUALITY` and five
`PRICE_*` variables — none of which any line under `agent-v2/` reads — and was
**missing** `DEEPSEEK_API_KEY`, which carries 21 of the 26 roles.

Anyone filling it in to the letter got a bot that did almost nothing.

**The fix.** Rewritten from the code. The same class of mistake turned up once
more later: an error message told the operator to set `NIA_SERVER=1`, a variable
nothing reads — the code asks for `AGENT_V2_SERVER`, like the systemd units and
the deploy script. A name that appears in exactly one place has nothing to be
checked against.

## 2.6 Databases in the history that `git ls-files` could not see

**Symptom.** A scan of every commit — not the working tree — found twelve files
present in no branch: an abandoned prototype's SQLite databases and its activity
log, about 2.5 MB, reachable only from a tag.

**Meaning.** "The database is in `.gitignore`" is true of today's tree and says
nothing about the history. They were committed before `.gitignore` covered
`data/`.

Checked rather than assumed: 25 tables, 24 empty, three test runs at zero cost,
no email addresses and no keys. No secrets — but by luck, not by design.

**The fix.** The history begins at one commit and the tags are gone. The audit
scans every commit, not just the tree:

```bash
python narzedzia/audyt.py --historia
```

**The rule.** `git ls-files` answers "what is in the tree". The question before
publishing is "what is in the history", and it needs a different command.

## 2.7 Every number in the original README was out of date

**Symptom.** It claimed 11 Python files (there were 23), 11,231 lines (28,000),
43 test suites (122). Two documents in the same repository gave different totals
for spend, because both were measurements from different days with no date next
to the number.

**Meaning.** Exactly the class of error the project warns about elsewhere: a
figure typed in by hand to show scale stops being true at the first change, and
nothing watches it.

The same project solved this properly for the big document:
`JAK_ZBUDOWANY_JEST_BOT.md` is generated and guarded by `test_dokumentacja_zywa`,
which fails when a rebuild changes anything. The README stood outside that.

**The fix.** [FUNCTION_MAP.md](FUNCTION_MAP.md) and
[IDENTITY_MAP.md](IDENTITY_MAP.md) are generated. Numbers in hand-written docs
are checked against the files before release — every count in
[REPO_MAP.md](REPO_MAP.md) was verified against `wc -l` rather than remembered,
and the first pass of that check found six of them wrong.

---

The Polish original of this journal — written entry by entry while the work was
happening — is kept as
[ROZWIAZYWANIE_PROBLEMOW.md](ROZWIAZYWANIE_PROBLEMOW.md). It carries more detail
on the measurement behind each entry, and it says which entries were still open
at the time of writing.
