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

## 8. What the sweeps could not see, and reading found

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
| 12 | every count claimed in a document, against the tree | **the number of functions stood in six documents in five versions** (548, 548, 535, 529, 519, 519) while the tree held 549 — and one of those documents is the chapter titled *"Every number in the original README was out of date"*. Two of the disagreements were not errors at all but different counting rules nobody had written down |
| 13 | the niche's name as a **two-letter token** | it was in the *name* of a constant (`PRZESTAWIENIE_KONTA_NA_AI`), in a dictionary **key**, and in a header printed to the owner: *"EPOKA AI … OSOBNO OD EPOKI UKRYTYCH SYSTEMOW"* — both the current subject and the previous one, in one line. Unsearchable: two capitals, and the same letters appear legitimately in the same repo (Substack's own "Scan for AI text" feature) |
| 14 | module-level constants holding a **date literal** | the **fifth** copy of the account's pivot date, in a constant with the same name as the second one — it survived the fix to that one because the test's list of places was hand-written |
| 15 | the `systemd/` directory, read as if it were code | six units carrying **another machine's install path** twice each, another machine's user, and a placeholder brand in `Description=`. The audit reads these files, but it hunts identity patterns, and `/home/ubuntu/...` is not a name — it is a path |
| 16 | references to constants that **do not exist** | `config.NOTEK_DZIENNIE` in a live branch of `alarm.py` — the branch could never run, and `getattr` with a default meant nothing ever protested. Now checked by the audit on every run |
| 17 | assertions matching the **text of a `.py` source** | 138 of them; 9 find their needle only in a comment. Two were real — a pair guarding separate budgets that had been passing on a comment quoting the code as it used to be |
| 18 | **running our own configurator as a stranger**, then reading every failure as "is this a fault, or is this our number stated as a law?" | six failing assertions on a correct install, a field the configurator asks for that no module reads, and three article-length constants wired to nothing — see section 11 |

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

**And the commit hashes left behind.** Fourteen short hashes are still quoted
across the code and the docs — `df3de64` for the SIGTERM that corrupted seven
runs, `e88b456` for the commit that wrapped three stages in one `try`, and
twelve more. They were citations: *you can go and look*. In this repository
they resolve to nothing, and a citation that cannot be opened is worse than no
citation, because it promises verification it cannot deliver.

They are kept rather than deleted for one reason: the measurement behind each
one is real, and the hash is the only handle on it in the **production**
repository, where those commits still exist. `narzedzia/audyt.py` lists them at
every run so the number stays known and cannot grow quietly. Anything that
needs to be checkable in *this* repository has to carry the measurement itself,
not a pointer to one.

**And an honest figure for the rest.** Measured 2026-09-04, with the counting
rule spelled out because two documents in this repository once disagreed on the
number of modules purely by counting different things: `find agent-v2 -name
'*.py' -not -path '*/tests/*'` gives **27 files, 29,844 lines** (the 25 modules
plus `dokumentacja-zrodla/sklej.py` and `prompts/`' helper); the tests are
**143 files, 39,086 lines**; the tools 2,106. Total 71,036 lines of Python.

This is where the line-by-line reading stands, and it is deliberately a table
rather than a percentage, because a percentage hides which half you got.

| module | lines | read line by line |
|---|---:|---|
| `stages.py` | 7,401 | **all of it** |
| `browser.py` | 5,204 | **all of it** |
| `run.py` | 2,845 | **all of it** |
| `config.py` | 2,985 | **all of it** |
| `wzajemnosc.py` | 1,442 | **all of it** |
| `llm.py` | 848 | **all of it** |
| `gates.py` | 599 | **all of it** |
| `statystyki.py` | 530 | **all of it** |
| `db.py`, `kanal.py`, `bramki.py` | 940 | **all of them** |
| `style.py`, `konfiguracja.py`, `jezyki.py` | 800 | **all of them** |
| `kopia_subskrybentow.py`, `audyt_researchu.py`, `aktualne_modele.py` | 590 | **all of them** |
| `alarm.py` | 1,053 | **all of it** |
| `norma.py` | 1,170 | **all of it** |
| `audyt_systemu.py`, `audyt_tematow.py` | 1,030 | **all of them** |
| `raport_statystyk.py`, `korpus_kanalow.py` | 690 | **all of them** |
| `migracja_okno_promocji.py` | 97 | **all of it** |
| the test files | 39,000+ | ~40 read; **all of them** swept by shape (below) |

That is all 30,294 lines in the agent's 25 modules — every module, in full,
from `stages.py` at 7,401 lines down to `migracja_okno_promocji.py` at 97.

**And how the tests were checked.** Reading 39,000 lines of tests would have
cost as much again as reading the bot. Four shape-based sweeps over **all**
test files were cheaper and answered definitively:

| sweep | result |
|---|---|
| assertions matching the **text of a `.py` source** | 138 of them; 9 find their needle only in a comment, and **2 of those were real**: `budzet["follow"]` survived only in a comment about a fix from three weeks earlier. Now permanently guarded by `test_asercje_po_zrodle.py` |
| `sprawdz(..., True)` — assertions that cannot fail | 26, and **all 26 legitimate**: each sits in a `try`/`except` where reaching the line *is* the measurement |
| assertions pinning the **size of a configuration constant** | 6, and all 6 correct: the two that pin an operator's own choice use `sprawdz_nasze`, which skips itself when a `konfiguracja.toml` exists |
| references to constants that do not exist | zero in tests (one in the bot — see sweep 16) |

The first of those sweeps produced a wrong number first — 95 instead of 9,
because the comment-stripper joined tokens and destroyed the layout, so no
multi-token needle could match. That is written into the file that made the
mistake.

**What the reading found that no sweep did.** Every defect listed in the sweeps
table above was found by a pattern. These were not: a guard written for
"just before publishing" that nothing ever called; a daily-ceiling raise
applied **twice**, so the day it fired the limit was four times the base; a
configurator field that was asked for, validated, and silently dropped; four
names in a nine-name list that do not exist; an assertion that read as a
guarantee about a whole file and tested one string. Each of those reads as
working code. None of them is.

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

---

## 11. The sweep that reading could not replace: **being a stranger**

Everything above was found by reading the code or by sweeping it for shapes.
Both share a blind spot, and it is a large one: **they are performed from
inside this installation**, where every value is our value and therefore every
check passes.

The last sweep was different. We ran the repository's own configurator from
scratch, as a person who has never seen this account — an invented English
publication about how bread is made and regulated — and then took the result
seriously. Two commands:

```
python narzedzia/kreator.py            # answer as a stranger
python narzedzia/audyt.py
```

The audit dropped from **236 passing / 0 failing** to **234 / 2**, and
`test_szukanie_celow.py` failed **six times**, on an installation that was
entirely correct. Every one of those failures was one of our own values stated
as if it were a law:

| what failed | what it really was |
|---|---|
| `hasel szukania jest >= 19` | 19 is **our** phrase count. The rule that holds for anyone is structural: the pool must be wider than one run draws (`3 × ILE_HASEL_NA_PRZEBIEG`), or every run takes the whole pool and returns the same handful of accounts |
| `rewir obejmuje: ludzie i prawo` (×2) | `OBSZARY_REWIRU` is **our** map of the beat, with Polish names — and it is **not in the configurator at all**, so an operator cannot change it. Demanding that an English publication about bread cover "pieniądze i władza" is impossible by construction |
| `kazde haslo miesci sie w niszy` | a mismatch between two of the operator's **own** fields — a hint, not a failed install. The audit had no way to say that: it could only say OK or BŁĄD |

**And the finding under those findings.** Chasing the niche-marker check
revealed that `ZNAKI_NISZY` — the field the configurator asks for, the field
`config.py` described as "the words the **code** matches on", the field two of
the English documents we wrote describe the same way — **is read by no module
of the agent at all**. Its complete set of readers is the loader, the audit,
the configurator, one test, and the documentation. What decides whether a post
is on topic is the model, from `prompts/cele.md`. An operator retuning that
list to change the bot's beat would change nothing except whether the audit
passes.

The file whose entire job is finding constants no code reads —
`test_martwe_sygnaly.py` — could not see it, for two reasons that are worth
copying down:

- its evidence of "something uses this" included `konfiguracja.py`, which holds
  the table mapping every TOML field to its constant name. **The mere fact that
  a field can be set counted as proof that something reads it.**
- its exemption for "used inside the config itself" counted occurrences in the
  **raw** text, and nearly every constant in that file has a paragraph above it
  naming it. **One sentence of prose exempted a constant from the question.**

Both are now closed, and the counterproof is run: with an empty registry the
scan now prints `ZNAKI_NISZY`, which it never did before.

**The proof that a stranger's install now works** is a command anyone can run:

```
cp konfiguracja.example.toml agent-v2/konfiguracja.toml
python narzedzia/audyt.py
```

The full test suite under that configuration gives **138 passing / 2 failing**
— the same two environmental failures as our own installation
(`test_czas.py` needs POSIX signal semantics, `test_zapora_platnych_wywolan.py`
needs a real API key). A new test, `test_przyklad_przechodzi_reguly.py`, keeps
it that way: it asks whether **our own example** survives the rules we impose
on everyone, because a failure there means either the example is broken or the
rule was ours all along.

**If you take one thing from this section:** reading thirty thousand lines did
not find any of it. Standing outside your own installation for ten minutes did.

## 12. The previous account's history inside the prompts

Removed 2026-09-05. The 24 briefs in `agent-v2/prompts/` had grown to 4,287
lines, and close to half of that was not instruction but memory: measurements
from one account's runs ("82 comments went out and 3 came back", "four cards
in ninety-three claims", "156 subjects from 12 channels"), dated incidents
("in August this cost us an article", what the target-selection stage did on
2 September), sentences quoted from that account's own published comments and
articles, and paragraphs explaining what an earlier version of the same brief
used to say and why it was changed.

Every one of those was a trace of the old life: its subject, its channels,
its reception numbers and its mistakes. A bot pointed at a different account
was being taught on somebody else's failures, and the owner's instruction was
direct: the prompts are too long and they hold the writers too tightly.

| Kept | Removed |
|---|---|
| every `{field}` the code injects, and only those | measurements, counts and dates from the previous account's runs |
| every JSON contract the code parses, byte for byte | sentences quoted from its published comments and articles as examples |
| every rule a gate or a test depends on: the injection barrier and its position, the five silence labels, the `your` requirement, the datestamp rule, the limits-paragraph rule, the banned openers, the six-word echo check and the three sentences it is tested against | paragraphs about what an earlier version of the brief said and why it changed |
| the method: what each stage is for, what it may assert, what it must return | rules stated twice or three times inside one brief, and blocks repeated across three briefs |
| the style block for the header image, verbatim | the punctuation-rate table measured on the old account's articles |

Where a rule had been argued from "measured on this account, X happened", it
is now stated as the rule. The writer's brief went from 519 lines to 300, the
scout's from 615 to 388, the note brief from 298 to 159, the comment brief
from 268 to 137; the set from 4,287 lines to about 2,740.

Six tests had pinned the anecdotes rather than the rules, and were re-pointed
at the rules, each change commented in place: `test_cele_o_niszy`,
`test_rekordy_nie_omowienia`, `test_cytat_niesie_twierdzenie`,
`test_zastrzezenie_o_datach`, `test_wybor_tematu`, and `test_prompty_o_niszy`
(two entries in its exception list covered sentences that no longer exist).

The same day, a second pass took the rest of the account's history out of the
places that feed the same briefs:

- `config.py`: the "this went wrong live" records in `NOTE_FORMS` (a patent
  number and a named circular from the old account's notes), the
  previous-subject flavour in `NOTE_TYPES["MYSL"]` and
  `NOTE_FORMS["ZACZEP_I_KONKRET"]`, the tic story in
  `POSTAWY_KOMENTARZA["KOREKTA"]`, and the monthly attention hints in
  `W_TYM_MIESIACU`, which described one industry's calendar and now describe
  the rhythm of institutions in general.
- `style-profiles/`: the two profiles injected into every article described a
  pipeline that no longer exists (frozen evidence IDs, `BLOCK`,
  `REWRITE_ONCE`, a route key), in Polish, and named the previous account's
  private corpus as their origin. Rewritten in English against the current
  pipeline, brand kept as `{marka}`. `NOTES_STYLE_PROFILE_V1.md` and
  `STYLE_SOURCES_MANIFEST.md`, which documented that corpus (path, hash,
  extraction date) and were read by nothing, were deleted.

What is still tied to the previous subject, on purpose and outside the scope
of a clean core: the default subject in `config.py` (`NISZA`,
`KAT_REDAKCYJNY`, `HASLA_SZUKANIA`, `ZNAKI_NISZY`, `DZIEDZINY_CIEKAWOSTEK`,
`OBSZARY_REWIRU`), which is the same material as
`packs/everyday-things-and-regulation.toml` and is what the tests exercise as
"our own example"; the version-name pattern `WZORZEC_WERSJI`, tuned for one
industry's product names; and the measurement narratives in `config.py`
comments and in the documentation, which are the reasons behind the constants
rather than material any model sees. Making the subject a required, separate
package is the next step, not this one.
