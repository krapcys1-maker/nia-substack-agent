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
- `test_podlogi_playbook.py` — a file glob carrying part of a published title

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

## 8. What seven sweeps could not see, and one reading found

Sections 1–7 were written after the identity scan came back green. Everything
below was found **afterwards**, and each item was invisible to every sweep that
preceded it. The order is the order they were found in, because that order is
the point: each sweep was designed against the previous one's blind spot, and
each still had a new one.

| sweep | what it looks for | what it found that the earlier ones could not |
|---|---|---|
| 1 | capitalised word-pairs in `.py` | **10 real people's names** in test fixtures, 11 other publications, 20 article titles |
| 2 | the same in `.md` | the name of the journalist whose columns were the style corpus — **in two configuration maps at once** |
| 3 | URLs, handles, emails, paths | a person's name glued into a subdomain — it survived the name sweep because a URL has no spaces or capitals |
| 4 | English prose inside Polish comments | a named researcher and their university, quoted as an example of a good mechanism description |
| 5 | four-digit article numbers | the number was a **filename prefix**, and the filename carried the title — two full directory listings |
| 6 | eight-to-ten-digit ids | **17 real Substack note ids.** A number does not look like identity until you paste it: `.../note/c-<id>` opens one specific note on one specific account |
| 7 | reading, line by line | three system messages with the subject written into them; the owner's own words quoted verbatim, twice, with the swearing left in; seven topics of *other people's* posts the bot had commented under |
| 8 | letters that are neither ASCII nor Polish | a word in which one letter was **Cyrillic** where its Latin twin belongs. The character itself cannot be written here — the audit refuses the file, which is the check working. It reads as an ordinary word and no search for its Latin spelling can find it. The same sweep surfaced two real people's names — one with hangul in brackets, one pasted into a domain |
| 9 | the shape `note/c-<digits>` | **four more real note ids.** Sweep 6 looked for eight-to-ten-digit numbers and replaced seventeen; searching by the shape of the URL instead of the length of the number has no false positives, and found the four that sweep had walked past |
| 10 | every domain in the source, counted | **three people's personal websites**, eighty occurrences across five files. Sweep 3 hunted a name glued into a *subdomain*; here the name was the *whole* domain, `www.<firstnamesurname>.com` |
| 11 | the shape `<something>.substack.com` | **eleven real accounts.** A handle can be one lower-case word with no dot and no capital, so no sweep looking for names, addresses or numbers could ever see one |

**What only reading found.** Three system messages — `CURIOSITY_SYSTEM`,
`BANK_SYSTEM`, `FEDREG_SYSTEM` — had the niche written into them literally. This
is a configuration defect, not a hygiene one: a system message outranks the user
prompt, so those stages were given two contradictory instructions at once. The
comment sitting directly above `CURIOSITY_SYSTEM` describes exactly this bug and
ends "the audit found it" — and the fix after it swapped one niche for another
instead of reaching for `config.NISZA`. The fault was documented and not fixed.

**And one thing that made a whole sweep lie.** One pattern — a short model name
from the previous era — had been on the audit's list from the start and had
never matched anything. The line in the file held that name **wrapped in
backspace characters**, which arrived with a paste. It compiled, it sat on the
list, it was counted in the summary, and no source file contains a backspace.
The audit reported that pattern as absent, in green, over **eleven files that
contained it**. The audit now refuses any pattern carrying a control character
and names the line it is on.

That is the same class of fault this project hunts everywhere else — a check
that looks alive and does nothing — committed inside the tool that hunts it.

**And the same class again, one layer down.** The Cyrillic letter found by
sweep 8 is the backspace problem without the backspace: a string that reads
normally and cannot be matched. The audit now refuses source carrying Greek,
Cyrillic, Hebrew, Arabic, Devanagari, Thai, kana, hanzi or hangul, and prints
extended-Latin letters for a person to look at — because that range holds both
`Veröffentlichen` from Substack's German interface and surnames.

**The lesson sweeps 9, 10 and 11 keep repeating.** Search for the *shape of
the thing you are hunting*, not for a property it happens to have. Numbers,
capital letters and dots are properties; `note/c-<digits>`, `<name>.com` and
`<handle>.substack.com` are shapes. Every sweep built on a property drowned in
false positives and was skimmed; every sweep built on a shape had none.

**And a lesson about how to search.** Sweep 6 hunted eight-to-ten-digit numbers
and drowned in token ceilings and file sizes, so it was skimmed. Sweep 9 hunts
`note/c-<digits>` and has no false positives at all. Four ids had survived the
first. Searching by the *shape of the thing* beats searching by a property the
thing happens to have.

**Documentation has twins.** `agent-v2/dokumentacja-zrodla/` holds both
generated parts and 5,700 lines of hand-written chapters, and the hand-written
ones restate what the code comments say. Fixing a comment does not fix its twin,
and nothing notices: three chapters described code that had been changed hours
earlier. Anything corrected in a comment has to be grepped for there too.

## 9. What this cost

Seventeen test files compare current code against named past commits. Those
commits no longer exist, so `tests/historia.py` makes them skip cleanly and say
why, rather than fail.

**And that skip was costing far more than the counterproofs.** Every one of
those files called the guard in its *header*, so the whole file went dark — not
just the block that needs the old version. Counted on 2026-09-04: **617
assertions out of 1,174 never executed**, and the suite reported itself as
passing, because a skip exits 0. Measured the hard way the same day: a constant
in `run.py` was changed and three test files said "OK" without running a single
line.

The guard now takes the pass/fail counters and moves down to just above the
block that actually reaches into git. Six files split cleanly this way and
**189 assertions came back**, all passing. The remaining eleven load the old
version during setup and use it throughout, so they cannot be split without
restructuring — that is written down here rather than hidden, and it is the
honest size of what a wiped history costs:

| | assertions |
|---|---:|
| running before | 557 |
| recovered by moving the guard | **189** |
| still dark (old version needed at setup) | 428 |

They no longer prove what they used to prove. That is the price of a history
that begins here.

**And an honest figure for the rest.** The tree is 70,269 lines of Python:
29,741 in the agent's 27 modules, 38,422 in 140 test files, 2,106 in the tools.
This is where the line-by-line reading stands, and it is deliberately a table
rather than a percentage, because a percentage hides which half you got.

| module | lines | read line by line |
|---|---:|---|
| `stages.py` | 7,401 | **all of it** |
| `browser.py` | 5,204 | **all of it** |
| `run.py` | 2,845 | **all of it** |
| `config.py` | 2,922 | in parts, following the sweeps |
| `llm.py` | 823 | most |
| `konfiguracja.py`, `jezyki.py`, `style.py` | ~800 | all — they were rewritten |
| `audyt_systemu.py`, `audyt_tematow.py` | 980 | the parts touched here |
| the other 15 modules | ~9,000 | **not yet** |
| the 140 test files | 38,422 | roughly 30 of them, in the parts touched |

That is 15,450 of the 29,741 lines in the agent's modules — the three largest
files, and the three that carry every publishing decision.

The unread part has been through all thirteen sweeps but not through a person's
eyes. Every one of those sweeps found something the earlier ones could not, and
reading found things no sweep could — so neither substitutes for the other, and
the reading continues.

Anything stronger than this table would be a guess dressed as a measurement.

## 10. How to check the claim rather than believe it

```bash
python narzedzia/audyt.py --historia
```

Scans the working tree and every commit for identity patterns, secrets, keys,
session files, subscriber lists and databases. Section 9 is a counterproof: it
builds files that *should* trip the audit and fails if they do not, because an
audit that catches nothing looks exactly like a clean repository.
