# NIA Substack Bot

[![tests](../../actions/workflows/testy.yml/badge.svg)](../../actions/workflows/testy.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![python: 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](requirements.txt)

An autonomous agent that runs an English-language Substack publication. It picks
its own topics, researches them on the web, writes the articles, posts Notes,
comments on other people's posts, replies, likes and restacks — and asks a human
for permission at no point.

```
5 notes/day · 15–23 comments/day · 1 article/week · $0.75 per article · $40/month ceiling
26 model roles · 143 tests · 12 gates on every finished text
```

This is not a demo. It ran against a live account for weeks, it spends real
money on model calls, and **every number in this repository was measured rather
than estimated** — the costs come from a production database reconciled against
a provider invoice, to the cent.

The account identity, the subject matter and the source list have been removed.
What ships is the machine plus an example configuration you are expected to
replace. [docs/INSTALL.md](docs/INSTALL.md) says exactly where.

---

## Why this is not "an LLM that writes blog posts"

Most content bots are one prompt and one model. This one has **26 distinct model
roles**, a research pipeline that fetches and classifies primary documents
before a word is written, and **12 deterministic gates** that read the
finished text back against the evidence it was supposed to rest on.

Four decisions explain most of the code.

**The model observes, the code decides.** Numeric self-ratings from an LLM
degenerate to a constant — measured three times independently here: confidence
always 1.0, "threads found" always six. So the model is only ever asked for
**quotes and facts**, and every threshold, count and sort happens in Python. The
one model signal that survives is a **forced ranking**, because absolute scales
can be flattened and comparisons cannot.

**Nothing blocks the article.** Gates return remarks, not verdicts. A filter
that cannot reject is not a filter — but a filter that kills a paid pipeline run
is worse. The reasoning is financial: one article rewritten three times cost
**$8.38 instead of $2.12**.

**Prohibitions leave room; prescriptions become a signature.** A rule dictating
position — "put the strongest fact in paragraph three" — turns into a
recognisable fingerprint after ten articles. So the prompts say what *not* to
do, and each article's shape is drawn at random.

**A fixed number per day looks like a robot.** Volumes are drawn from ranges
once per day, seeded from the date, so every run that day agrees on the budget
and consecutive days differ. Gaps between actions are randomised too — and not
arbitrarily: measured on a live account, failure rate **triples after the first
action** when gaps average four minutes.

And the rule that governs work on the code itself:

> **A grep in the source is not proof that the code runs.**
> Three times in this project a test went green over dead code.

Which is why the function map here is built from the abstract syntax tree — and
why building it that way turned up a [second dead paid
stage](docs/TROUBLESHOOTING.md) that the project's own guard test structurally
cannot see.

---

## Start here

| document | what's in it |
|---|---|
| **[docs/PLUGGING_IN_AN_ACCOUNT.md](docs/PLUGGING_IN_AN_ACCOUNT.md)** | **start here if you want to run it.** Every decision about a publication — name, subject, sources, model split, daily volumes, budget — and the one place each one goes |
| **[packs/README.md](packs/README.md)** | **subject packs** — ready-made subjects (AI, how things work, laws and public money) you can start from instead of inventing twenty search terms. One file each, and the place to contribute one |
| **[docs/INSTALL.md](docs/INSTALL.md)** | zero to running, step by step — including the one step no software can do for you |
| **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** | how it works and where everything lives: both pipelines, all 26 roles, every directory |
| **[docs/FUNCTION_MAP.md](docs/FUNCTION_MAP.md)** | all **563 functions** in 25 modules — line, signature, whether it calls a paid model and for which stage, whether it touches the browser, who calls it. Generated from the AST |
| **[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** | split in two: what will bite you on a fresh clone, and what already bit us and is fixed. **Read before your first run** |
| **[docs/CONFIGURATION_MAP.md](docs/CONFIGURATION_MAP.md)** | the deep analysis: what is configurable, what is welded to one platform, what would mean rewriting a module — and what the configurator already covers |
| **[docs/REPO_MAP.md](docs/REPO_MAP.md)** | the hand-written map: what each module decides, which stage reads which of the 24 briefs, the four places an account enters, what is deliberately absent |
| **[docs/IDENTITY_MAP.md](docs/IDENTITY_MAP.md)** | every physical occurrence of the account's name, subject and voice, classified FIELD / INJECTED / GENERATED / TEMPLATE / BY HAND. Generated |
| **[CONTRIBUTING.md](CONTRIBUTING.md)** | how to send a subject pack (no Python needed) or a code change, and the four habits review will ask you about |
| **[docs/CLEANING_LOG.md](docs/CLEANING_LOG.md)** | what was taken out when this stopped being one account's working tree, and exactly where each thing stood |

The Polish original of the troubleshooting journal, with the measurement
behind each entry, is [docs/ROZWIAZYWANIE_PROBLEMOW.md](docs/ROZWIAZYWANIE_PROBLEMOW.md).

The bot's own design documents are in `agent-v2/` and are in Polish:
`DOKTRYNA.md` (what it must and must not do — canonical, and its closing
"Discrepancies" section is part of the document), `JAK_DZIALA_V2.md`
(architecture with costs) and `JAK_ZBUDOWANY_JEST_BOT.md` — 13,084 lines,
**generated from the code** and guarded by a test so it cannot drift.

**A word on the language, before you open a file.** Everything written *for
you* is in English: this README, the ten documents above, the example
configuration and the setup program's questions. Everything written *for the
machine* is in Polish — identifiers, comments, test names, and two directories
you will see at the root (`narzedzia/` is "tools", `konfiguracja.example.toml`
is the example configuration). That is not an oversight and it is not going to
be translated: the comments in this codebase carry the *reasons* behind
decisions — measured numbers, the bug that forced a rule, what was tried and
rejected — and a translation pass over 30,294 lines would quietly lose exactly
that. The English documents are written to stand on their own, so you can run
and configure the bot without reading a line of Polish; you need it only if you
want to know *why* a particular line is the way it is.


---

## Quick start

```bash
pip install -r requirements-dev.txt
python narzedzia/kreator.py        # asks everything, writes the config and .env
python narzedzia/pakiety.py        # or: start from a subject pack
python agent-v2/alarm.py           # health check
```

The setup program asks for the account, the subject, the language, the sources,
the model for each of the 26 roles, the daily volumes and the budget ceilings,
then writes `agent-v2/konfiguracja.toml` and `agent-v2/.env`. Every answer is
checked with the same validator the bot uses on load, and the file it writes is
read back immediately — a setup tool that produces a file the program then
rejects is worse than no setup tool, because it looks like success. API keys go
only to `.env`, are never echoed, and never reach the TOML.

Prefer to edit by hand: `cp konfiguracja.example.toml agent-v2/konfiguracja.toml`.
Either way the file is optional — without it the bot runs on the defaults in
`config.py` — and a bad value or a mistyped field name **stops the start** with
a message naming what was allowed.

`python narzedzia/kreator.py --pokaz` prints every field and its current value
without writing anything.

The last command is the health check. It is the only entry point that runs
**with no session, no API keys and no data**, and it prints line by line what is
missing. For a fresh install it is the best to-do list you will get.

Then read [docs/INSTALL.md](docs/INSTALL.md).

---

## What it costs, and where

| item | cost |
|---|---|
| one comment | $0.03 |
| one reply | $0.02 |
| one note | $0.086 (Opus) / $0.010 (DeepSeek pro) |
| one article, end to end | **$0.75–0.78** |
| monthly ceiling — the only hard block in the system | **$40.00** |

Two stages are **59% of the entire bill**: `discovery` (34.9%, ~167k input
tokens per call, because every search round resends the whole conversation) and
`write` (24.4%). Everything else is rounding.

Two measured findings worth stealing:

* **Prompt caching is near-worthless for short outputs.** The standard advice is
  to cache the system prefix. Measured here: a note is 220 input tokens and
  1,667 output tokens — **97% of the cost is output**. Caching would save ~2%.
* **Batching notes into one call destroys them.** Given the whole candidate pool
  at once, the model produced five variants of the same fact, four of them about
  an elevator. Identical shape is a machine signature.

---

## Requirements

| requirement | why | optional? |
|---|---|---|
| Python 3.10+ | measured on 3.12 | required |
| `DEEPSEEK_API_KEY` | **21 of 26 model roles** | required |
| `ANTHROPIC_API_KEY` | notes, articles, repair pass | required |
| `OPENAI_API_KEY` | cover image only | optional — the article ships without one |
| Playwright + Chromium | the Substack layer | required |
| **a real Chrome with a display** | Cloudflare fingerprints headless mode and the note simply never appears | required to publish |
| **a Substack account, logged in by hand** | Substack has no publishing API — the bot *is* a signed-in user | required |
| SMTP | failure alerts | optional — degrades silently |

**The Substack session is the one place this system always needs a human.** The
automated login path exists in the code and the code itself advises against it,
because it loops on CAPTCHA.

---

## Safety rails you should not remove

Each exists because something went wrong once:

* **Test-copy marker.** A file named `TO_JEST_KOPIA_TESTOWA` next to
  `config.py` revokes the right to publish. A test copy can never post.
* **Databases separate themselves.** `DATA_DIR` derives from where `config.py`
  sits, so a second clone gets its own database with no environment variable
  anyone can forget.
* **Paid calls are barred from free tests.** `llm.call` refuses when the process
  looks like a free test with no stub installed — because a test without a stub
  once paid real money and the only trace was a row in `calls`.
* **The per-run ceiling always applies**, even under `NO_LIMIT`.
* **`DRY_RUN` blocks the browser too.** It used to block only model calls, so a
  "dry" run wrote nothing and still liked two strangers' posts.
* **Every paid call is attributed to a channel**, checked by a test that builds
  a reachability map from the AST.

---

## Lines this agent does not cross

In a project about automating someone else's platform this matters more than the
feature list.

**The account does not volunteer that it is AI-run, and never lies when asked
directly.** Denial is forbidden by doctrine. So is technical evasion of
detection.

**It does not farm reciprocity.** Measured: of twelve accounts given a
subscription, **zero** reciprocated. Unfollowing after silence is explicitly
"artificial activity" under Substack's terms, so it does not happen.

**It does not comment everywhere.** A comment must add something the post did
not say; when the bot cannot name what it is adding, it stays silent.

**Hosts that refuse automated reading are respected** (`config.BLOCKED_HOSTS`).

**Secrets never enter the repository.** `.env` and `agent-v2/data/` are
gitignored from the first commit; subscriber exports are written `0600` because
they contain other people's email addresses.

---

---

## License

**MIT** — see [LICENSE](LICENSE). Read it, fork it, run it, build a product on
it. Keep the copyright notice; that is the whole obligation.

**This was AGPL-3.0 until 2026-09-04, and the argument for AGPL was a good
one**, so it is worth recording what changed rather than quietly swapping the
file. The case was: this bot is meant to be *run as a service*, so under a
permissive licence somebody could operate a paid content business on it and
give nothing back — and because the software is never *distributed*, an
ordinary GPL would not even bite. AGPL closes exactly that hole.

What outweighed it: **most of the value here is in being read.** The 13,000-line
generated walkthrough, the cleaning log, the counterproof habit, the record of
which checks turned out to be doing nothing — that is the part worth having,
and AGPL keeps it away from a large share of the people who would benefit,
because plenty of organisations forbid AGPL outright regardless of how the code
is used. A licence that protects against a business model nobody has yet, at
the cost of readers who exist now, is the wrong trade for this project.

The risk is real and accepted: somebody can take this, close it, and give
nothing back. If you are the sort of person who would rather not, the
contribution that actually helps is a subject pack — see
[CONTRIBUTING.md](CONTRIBUTING.md).

## Honest notes

**How many tests fail depends on how far you got with the install**, and none
of the failures is a code defect. The table says **what** fails rather than how
many pass, because the second number rots the moment anyone adds a test — and
the version that stood here did exactly that, drifting to 102 while the real
figure had reached 137:

| after | what still fails |
|---|---|
| `pip install -r requirements-dev.txt` | four — `playwright` browser not downloaded, Windows has no POSIX signals, empty `data/`, no `.env` |
| `+ playwright install chromium` | the last three |
| `+ .env` and the first run | two — `test_czas` needs POSIX signal semantics, `test_zapora_platnych_wywolan` needs a real `ANTHROPIC_API_KEY` to prove the paid-call firewall refuses it |

Measured on this copy: of 143 test files, **137 pass, 2 skip themselves and 2
fail**. Both remaining failures are impossible to fix on a fresh Windows install
and neither says anything about the code. Each is listed with its cause in
[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md). The count of files is
checked against the tree on every run by `test_liczby_w_dokumentach.py`, so this
paragraph cannot drift again in silence.

**Twenty assertions skip themselves in this copy**, spread over twenty files.
Eighteen reproduce a counterproof out of a specific commit, because the
project's doctrine requires a reference version pinned to a SHA and never to
`HEAD`; this repository's history was started fresh when the account identity
was removed, so those commits do not exist here. Two are whole files. All of
them say so and exit cleanly rather than crashing — a skipped assertion is
printed with a dash instead of `OK`, because one that passed quietly would be
worse than one that failed: it would look like proof.

**`agent-v2/` is a leftover name** from when this repo held two agents side by
side. Renaming it was tried and reverted: nineteen tests read their reference
versions out of git by path, and a rename means a permanent path shim in each of
them. A nicer directory name is not worth that.

**It is a configurable product for one platform, not for any platform.**
`konfiguracja.toml` now drives the account, the subject, the model split, the
volumes and the budget. What is still hand-edited: the subject sentences inside
14 prompt files, and the brand name in nine of them. What will not become a
field at all: the Substack layer is ~2,500 lines a second platform would not
share, and the gates in `gates.py` are English regular expressions that stop
matching — silently — in another language. The full breakdown, split into a
day's work, a few days' work and rewriting a module, is in
[docs/CONFIGURATION_MAP.md](docs/CONFIGURATION_MAP.md).
