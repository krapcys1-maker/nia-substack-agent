# Architecture — how the bot works and where everything lives

Two pipelines, one process, twenty-four modules. This document is the map: what
each directory holds, what each module does, and how a run actually proceeds.

For the complete function-level inventory — 555 functions with line numbers,
cost markers and call edges — see [FUNCTION_MAP.md](FUNCTION_MAP.md), which is
generated from the abstract syntax tree.

---

## Where everything lives

```
agent-v2/              the bot. Everything that runs is here
  run.py               the daily routine and the article chain
  artykul_z_puli.py    the weekly article, taking its topic from the idea bank
  alarm.py             health check and email alerts
  stages.py            every model stage
  browser.py           the entire Substack layer
  config.py            the single source of truth for settings
  konfiguracja.py      reads konfiguracja.toml and hands values to config.py
  llm.py               transport to model providers, and cost accounting
  db.py                four tables, narrow column migrations
  gates.py             deterministic checks on finished text
  prompts/             24 prompt files, read from disk on every call
  tests/               137 free tests, 9 paid ones in tests/platne/
  systemd/             three services, three timers
  dokumentacja-zrodla/ the generator for the reconstruction document
  data/                database, journal, session — gitignored, never committed
style-profiles/        two style profiles, READ BY THE CODE at the write stage
docs/                  this map, the function map, troubleshooting
narzedzia/             generators: function map, dependency check
konfiguracja.example.toml  the configuration template to copy
```

**`agent-v2/` is not self-contained.** The article writer reads
`style-profiles/ARTICLE_STYLE_PROFILE_V1.md` and its negative counterpart. Move
the bot without them and the `write` stage raises `StyleError` — after the
research has already been paid for.

### The four large modules, in proportion

| module | lines | of which code | prose | what it is |
|---|---|---|---|---|
| `stages.py` | 7,226 | ~3,320 | 43% | every model stage |
| `browser.py` | 5,131 | ~2,470 | 41% | the entire Substack layer |
| `run.py` | 2,843 | ~1,210 | 49% | orchestration |
| `config.py` | 2,714 | ~900 | 57% | settings, with reasons |

That prose is not decoration. It records what was measured and why a number is
what it is. Moving this bot to another platform, the comments are worth more
than the code.

---

## What actually runs

Three entry points, and nothing else. Anything not reachable from these is not
running, whatever it looks like:

| entry point | schedule | what it does |
|---|---|---|
| `run.py --dzien --wyslij` | 5×/day | notes, comments, replies, likes, restacks, follows |
| `artykul_z_puli.py --wyslij` | Tuesdays 14:00 UTC | one researched article |
| `alarm.py` | daily 07:00 UTC | health check, email alerts |

---

## Pipeline 1 — the day

`run.dzien()` walks a series of blocks. **Each block is isolated**: a failing
comment block does not take the notes with it.

```
replies under our own posts  →  notes  →  follows  →  subscriptions
   →  comments on others' posts  →  discussions  →  likes  →  restacks
   →  subscriber-list backup
```

Volumes are drawn once per day from ranges, seeded from the date — so every run
that day agrees on the budget and consecutive days differ. A fixed number per
day is a machine signature.

Gaps between actions are randomised per action type, and they are not arbitrary.
Measured on a live account: failure rate **triples after the first action** when
gaps average four minutes. Comments now sit 5–15 minutes apart.

### What the day costs

| stage | model | $/call |
|---|---|---|
| `cele` — pick targets | deepseek-flash | 0.006 |
| `curiosity` — find facts | deepseek-flash | 0.056 |
| `note` — write a note | claude-opus-5 | 0.086 |
| `note_tani` — the same stage, cheaper writer | deepseek-pro | 0.010 |
| `comment` | deepseek-pro | 0.006 |
| `reply` | deepseek-pro | 0.005 |
| `restack` | deepseek-pro | 0.003 |
| `factcheck` | deepseek-flash | 0.007 |
| likes, follows | no model | 0 |

Notes alternate between two writers — even-numbered to the expensive model,
odd-numbered to the cheap one. They are **separate stage names rather than a
parameter**, so the `calls` table splits their cost by itself, with no extra
column and nothing counted by hand. It is simultaneously a saving and a running
blind test.

---

## Pipeline 2 — the article

```
scout          6 topics, each with a named broken belief          $0.018
feasibility    cheap triage: does the topic have a second act     $0.009
discovery      search the web for sources, skip dead hosts        $0.234  ← 35% of the bill
fetch          download pages and PDFs; a second round below 4 sources    $0
classify       pull excerpts and figures out of what was fetched   $0.004
synthesis      assemble the evidence card                          $0.025
warto_pisac    the curiosity gate: is there a gap here             $0.015
write          THE PRODUCT                                         $0.426  ← 24% of the bill
review         reconcile the text against the card, sentence by sentence  $0.054
gates          sixteen deterministic checks                        $0
forma          four "the model observes" checks                    $0.025
grafika/obraz  cover image                                         $0.042
```

**Two stages are 59% of everything spent.** `discovery` costs what it does
because every search round resends the whole conversation — that is the price of
repetition, not of knowledge.

### The gates, and what they are for

**Before spending money** — four candidate gates, zero cost, pure code:
a named decision-maker *with a date*; a broken belief (*"most people don't know"
is ignorance, not a belief, and ignorance produces trivia*); contact with
something the reader owns; and a checkable source.

**After writing** — twelve deterministic gates catch invented experience, unnamed
studies, numbers absent from the corpus, quoted prompt text, one-source
articles, excess hedging, forbidden openings, and the article having the same
skeleton as any of the previous four.

**None of them blocks.** `gates.verdict` always returns `SAVED`. Once the
research is paid for, the article ships and the objections go to a file beside
it. The reason is financial: one article rewritten three times cost $8.38
instead of $2.12.

Four further gates ask a model to observe form — beat density, escalation,
whether the reader is ever caught with something concrete, whether the opening
rests on what they already know. **The model returns only quotes and yes/no.**
Counting, dividing and locating are done in code: a model's arithmetic cannot be
checked, a quote can be found in the text.

---

## The 26 model roles

`config.MODEL_FOR` maps a stage name to a model. Four tiers, and each assignment
was measured rather than guessed:

| tier | model | roles | why |
|---|---|---|---|
| top | `claude-fable-5-1` | `write` | won an A/B on an identical evidence card — caught that a regulation was narrower than its popular summary |
| top | `claude-opus-5` | `note`, `naprawa` | notes drive most subscriber growth and all their force is in the first sentence |
| mid | `deepseek-v4-pro` | 11 roles: comments, replies, restacks, discovery, synthesis, review… | SimpleQA 57.9 vs 34.1 — a ~70% edge on **factual recall**, which is what "where else does this mechanism appear" needs |
| cheap | `deepseek-v4-flash` | classification, fact-check, curiosity, targets | **extractive** work on supplied text at a third of the price |
| image | `gpt-image-1.5` | `obraz` | cover image only; a failure here never blocks the article |

Two roles are dead and documented as such: `factcheck` reached through
`stages.sprawdz_fakty` (zero callers anywhere) and **`fedreg`** through
`stages.kandydaci_z_fedreg` — called only from a paid test. The project's own
guard test cannot see the second one, because it checks the channel decorator
*before* checking whether anything calls the function. See
[TROUBLESHOOTING.md](TROUBLESHOOTING.md#5).

---

## Configuration: where the subject lives

Since the niche was given a single source of truth, four constants define what
this publication is about:

| constant | what it is | enforced by |
|---|---|---|
| `NISZA` | one sentence, handed to the model verbatim | `test_prompty_o_niszy` checks the prompts name it |
| `ZNAKI_NISZY` | 22 words the **code** matches on | `test_szukanie_celow` — every search phrase must contain one |
| `OBSZARY_REWIRU` | three areas the beat must cover | twenty phrases about one thing reach the same handful of accounts as three |
| `HASLA_SZUKANIA` | search phrases, ≥19 | `test_szukanie_celow` |
| `DZIEDZINY_CIEKAWOSTEK` | curiosity domains | `test_generatory`: `GENERATORY × DZIEDZINY ≥ 400` |

Before that change, six tests each had the subject written into their own body —
a good property enforced in a way that cemented the niche. Changing the topic
failed six tests for reasons that had nothing to do with the code.

### Prompts: on disk, but not all of them

The 24 files in `agent-v2/prompts/` are read from disk **on every model call**,
so editing one takes effect immediately. But alongside them sit **22 system
messages as Python constants** in `stages.py` (`SCOUT_SYSTEM`, `WRITER_SYSTEM`,
`NOTE_SYSTEM`…). Those are not read from disk and cannot be swapped without
editing code.

Code and prompt must be changed together: `test_generatory` compares the
placeholder fields the code supplies against the fields the prompt actually
uses, because a prompt gaining a field the code does not pass raises `KeyError`
at `format()` time — in production, not in the test.

---

## Data

Four tables, one access layer (`llm.py`), no migrations, no queues. A schema
change is a new column with a default, never a rewrite of existing rows.

| table | what |
|---|---|
| `runs` | one row per run, with status and stage |
| `calls` | one row per paid model call: stage, tokens, cost, channel |
| `articles` | one row per **attempt** at a text, not per published article |
| `sources` | fetched documents |

Every paid call is attributed to a channel (`artykul`, `notka`,
`komentarz@artykul`, `komentarz@notka`, `odpowiedz`, `restack`, `bank`).
`tests/test_kanal_platnego_wywolania.py` builds a reachability map from the AST
and fails if any paid call site can be reached without attribution. That test
exists because half the bill had no channel by any path, and "per dollar"
without a denominator is not a measurement.

---

## What is universal and what is not

Measured across the 555 functions:

| layer | functions | portable? |
|---|---|---|
| editorial pipeline (`stages.py`) | 155, of which 23 paid | **yes** — touches the platform in exactly one place |
| Substack layer | 62 touch the browser, 44 of them in `browser.py` | **no** |
| accounting and measurement | ~90 | mostly |
| configuration and gates | 48 | **language-dependent**, not platform-dependent |

Roughly: **~55% general-purpose editorial machine, ~25% Substack, ~15% "in
English", ~5% subject matter.** The ordering surprises people — the subject is
the cheapest thing to change and the language is the most underestimated,
because the gates in `gates.py` are English regular expressions. Change the
language and they do not complain; they quietly stop matching anything.

The full analysis, with the work broken into "a day", "a few days" and
"rewriting a module", is in [CONFIGURATION_MAP.md](CONFIGURATION_MAP.md).
