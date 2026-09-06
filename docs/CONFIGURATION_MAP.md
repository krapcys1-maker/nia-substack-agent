# Configuration map — what moves in this bot, and what would mean a rewrite

This document answers one question: **how much work separates this code from a
configurable product, where you supply a topic, sources, keys and a role split
and then run it.**

It is not a description of how the bot is built — `agent-v2/JAK_ZBUDOWANY_JEST_BOT.md`
does that, generated from the code and guarded by a test. This is about **what
you can change.**

> **Status.** The original audit that produced this map is preserved in
> [MAPA_KONFIGURACJI.md](MAPA_KONFIGURACJI.md) *(Polish, dated)*. That document
> is a snapshot; this one tracks the current state. Where the audit found
> something that has since been fixed, it says so and names the fix — because
> a map that reports solved problems is as misleading as one that hides them.

---

## What was verified by running it, and what was only read

The project's own rule is that a grep in the source is not proof that the code
runs. So the split is explicit.

**Verified by running:** the full test suite (on 2026-09-04: 125 passing,
2 failing — one needs a POSIX signal this machine does not have, one needs a
real API key); the paid-call reachability map built from the AST; a full
reconfiguration onto a different topic and an invented account, with three runs
on it; the configurator driving the bot end to end; the function map generated
from all 24 modules.

**Read, not run:** everything touching a live Substack session — publishing,
reach cards, the reader feed. There is no Playwright here, no session, and no
permission to have one. Those parts are described from the code.

**Measured by someone else:** the per-unit costs come from
`agent-v2/JAK_DZIALA_V2.md`, computed there against a production database and a
DeepSeek invoice. Not a cent was spent producing this map.

---

# PART 1 — INVENTORY OF ROLES

26 stages in `config.MODEL_FOR`. "Called by" comes from the syntax tree.

## 1.1 The article chain

| stage | model | prompt | token ceiling | $/call | called by |
|---|---|---|---|---|---|
| `scout` | deepseek-v4-pro | `skaut.md` + `SCOUT_SYSTEM` | 31,600 | 0.018 | `stages.scout` |
| `feasibility` | deepseek-v4-flash | `wykonalnosc.md` | 31,085 | 0.009 | `stages.feasibility` |
| `discovery` | deepseek-v4-pro | `dyskoveria.md` | 60,000 | **0.234** | `stages.discovery` |
| `classify` | deepseek-v4-flash | `klasyfikacja.md` | 32,171 | 0.004 | `stages.classify` |
| `synthesis` | deepseek-v4-pro | `synteza.md` | 32,948 | 0.025 | `stages.synthesis` |
| `warto_pisac` | deepseek-v4-pro | `warto_pisac.md` | 34,000 | 0.015 | `stages.warto_pisac` |
| `bibliotekarz` | deepseek-v4-pro | `bibliotekarz.md` | 40,000 | — | `stages.bibliotekarz` |
| `write` | **claude-fable-5-1** | `pisarz.md` + `WRITER_SYSTEM` | 37,600 | **0.426** | `stages.write` |
| `review` | deepseek-v4-pro | `recenzent.md` | 76,000 | 0.054 | `stages.review` |
| `forma` | deepseek-v4-pro | `forma.md` | 52,000 | 0.025–0.05 | `stages.ocen_forme` |
| `grafika` | deepseek-v4-flash | `grafika.md` | 32,000 | 0.002 | `stages.grafika` |
| `obraz` | **gpt-image-1.5** | — | none | 0.040 | `stages.grafika`, via `llm.obraz` |

Whole article: **$0.75–0.78.**

## 1.2 The daily routine

| stage | model | prompt | ceiling | $/call | called by |
|---|---|---|---|---|---|
| `cele` | deepseek-v4-flash | `cele.md` | 34,000 | 0.006 | `stages.wybierz_cele` |
| `curiosity` | deepseek-v4-flash | `ciekawostki.md` | 52,000 | **0.056** | `stages.znajdz_ciekawostki` |
| `bank` | deepseek-v4-flash | `bank.md` | 52,000 | — | `stages.posortuj_bank` |
| `wybor` | deepseek-v4-pro | `kogo_odpowiedziec.md` | 34,000 | — | `stages.wybierz_do_odpowiedzi`, `artykul_z_puli.temat_z_faktu` |
| `note` | **claude-opus-5** | `notka.md` + `NOTE_SYSTEM` | 37,314 | 0.086 | `stages.note` — **stage chosen at runtime** |
| `note_tani` | deepseek-v4-pro | same | 37,314 | 0.010 | same; notes alternate between the two |
| `factcheck` | deepseek-v4-flash | `weryfikacja.md` | 52,000 | 0.007 | `stages.zweryfikuj` |
| `comment` | deepseek-v4-pro | `komentarz.md` | 37,371 | 0.006 | `stages.comment_on` |
| `reply` | deepseek-v4-pro | `odpowiedz.md` | 37,371 | 0.005 | `stages.reply_to` |
| `restack` | deepseek-v4-pro | `restack.md` | 31,000 | 0.003 | `stages.ocen_restack` |
| `naprawa` | **claude-opus-5** | `naprawa.md` | 37,314 | — | `stages.napraw_obalone` — **runtime** |
| `naprawa_komentarza` | deepseek-v4-pro | same | 37,371 | — | same |
| `aktualne_modele` | deepseek-v4-flash | in code | 44,000 | — | `aktualne_modele.pobierz` |

## 1.3 Two dead stages

| stage | function | state |
|---|---|---|
| `factcheck` (second entry) | `stages.sprawdz_fakty` | documented; zero callers anywhere |
| **`fedreg`** | `stages.kandydaci_z_fedreg` | **found during this audit**; called only from a paid test |

`fedreg` was invisible to the project's own guard test, which checked the
channel decorator *before* checking whether anything called the function — so a
decorated function with zero callers reported as healthy.

**Fixed.** The condition now asks whether anything calls it, and `fedreg` is in
the documented list with the decision left open: wire it into a run, or delete
it together with `korpus_fedreg`, `prompts/fedreg.md` and its `MODEL_FOR` entry.

> The first attempt at that fix changed nothing, and that is worth recording:
> `if not zywe and q not in pokryte` looked right, but `pokryte` is seeded with
> decorated functions five lines earlier, so the second clause was always false.
> A fix that looks done and does nothing — the same class of error it catches.

## 1.4 Things that are not obvious about the roles

**Stages are not one-to-one with functions.** Five are selected at runtime:
`note`/`note_tani`, `naprawa`/`naprawa_komentarza`, and `obraz`. Searching the
source for `"note"` will not find their call site.

**Token ceilings are computed, not written.** `MAX_TOKENS` is derived and then
raised across the board by `THINKING_HEADROOM_TOKENS = 28,000`, because
reasoning tokens count against the output ceiling on DeepSeek too. The literal
`"fedreg": 8000` is really 36,000. Change the headroom and all 25 ceilings move.

**`config.EFFORT` works for one stage in six.** The rest run on DeepSeek, which
does not read that dial. The bot says so itself in the log.

**Not every prompt is a file.** Alongside 24 files in `agent-v2/prompts/` sit
**22 system messages as Python constants** in `stages.py`. Two of them —
`SCOUT_SYSTEM` and `WRITER_SYSTEM` — are now composed from `config`, so the
brand name has one home. The rest are still literals.

Of the 24 prompt files, one (`po_ludzku.md`) is reference material no code
reads, and it now says so in its own header; it previously claimed the opposite.

---

# PART 2 — WHAT IS GLUED TO ONE ACCOUNT

Work types: **CONFIG** — a value. **TEXT** — writing English prose. **CODE** —
touching logic.

## 2.1 Identity — now one source

| what | where | type |
|---|---|---|
| Substack handle | `config.SUBSTACK_HANDLE` | CONFIG |
| ~~second independent copy of the handle~~ | ~~`browser.PROFIL_HANDLE`~~ | **fixed** — now an alias of the config value |
| ~~two publish-panel URLs written out~~ | ~~`browser.py:751-752`~~ | **fixed** — composed from the handle |
| brand name | `config.NAZWA_MARKI` | CONFIG |
| brand in scout and writer system messages | `stages.py` | **fixed** — composed from config |
| ~~brand in nine prompt files~~ | ~~`prompts/*.md`~~ | **fixed** — injected as `{marka}` by `stages._prompt` |
| ~~brand in both style profiles~~ | ~~`style-profiles/`~~ | **fixed** — `{marka}` substituted by `style.load_profiles` |

> The handle used to live in two independent constants — 16 uses of one, 11 of
> the other. Changing one gave a bot that **published to one account and read
> the profile of another**, with nothing reporting it.
>
> The brand was worse: it had no constant at all, and in `SCOUT_SYSTEM` it
> was **split across two adjacent string literals**, which Python joins only
> at runtime. It survived an entire identity-scrubbing pass because the full
> name was never present in the source — only two fragments with a quote
> between them. CI now evaluates concatenated literal *values* with
> `ast.literal_eval` and scans the result, not the source text.

## 2.2 Subject — now one source

| what | where | size | type |
|---|---|---|---|
| the niche, one sentence | `config.NISZA` | — | CONFIG |
| yardstick your **search terms** are graded against (nothing filters posts by them) | `config.ZNAKI_NISZY` | 22 | CONFIG |
| areas the beat must cover | `config.OBSZARY_REWIRU` | 3 | CONFIG |
| search phrases | `config.HASLA_SZUKANIA` | 24, **≥19 required** | CONFIG |
| curiosity domains | `config.DZIEDZINY_CIEKAWOSTEK` | 32, **≥29 required** | TEXT |
| curiosity patterns | `config.GENERATORY` | 14, topic-neutral | — |
| topic sources | `korpus_kanalow.KANALY` | ships empty | CONFIG |
| headline filtering | `korpus_kanalow.OPRAWA`, `NIE_TEMAT` | regexes | TEXT |
| ~~subject sentences in prompts~~ | ~~14 files~~ | — | **fixed** — injected as `{nisza}` and `{kat_redakcyjny}`, niche examples from `temat.przyklady` |

All of the CONFIG rows above are now settable from `konfiguracja.toml`.

### The thresholds, and why they exist

* **≥19 search phrases across three areas** (`test_szukanie_celow`). At five
  phrases per run, a smaller pool means the agent looks at the same handful of
  accounts every day. Twenty phrases about one thing reach the same handful as
  three, which is why area coverage is checked separately.
* **`GENERATORY × DZIEDZINY ≥ 400` cells** (`test_generatory`). At 14 patterns
  that means ≥29 domains.

Six tests used to enforce these with the subject written into their own bodies —
a good property implemented in a way that cemented the niche. Changing the topic
failed six tests for reasons unrelated to the code. They now read `config`.

## 2.3 Voice

| what | where | type |
|---|---|---|
| style corpus, 226 paragraphs | `prompts/styl/article_style_samples_v1.txt` | — |
| its SHA-256 pin | `config.STYLE_CORPUS_SHA256` | CONFIG |
| five pinned paragraphs, by ordinal and digest | `style.APPROVED_EXAMPLES` | CODE |
| two style profiles | `style-profiles/` | TEXT |
| banned vocabulary, 18 words | four prompt files | TEXT — topic-neutral, keep |

**The style corpus is not about the old subject.** It is Essayistic prose in a broadsheet-column register
about trade secrets, silk-spinning and patents. It teaches a rhetorical *move*,
not a topic, and survives a change of niche intact.

It is pinned twice, though: the loader refuses on a hash mismatch, and five
specific paragraphs are pinned by **ordinal and content digest**. Adding a
paragraph at the top shifts the numbering and stops the writer. That has already
cost one paid research run.

## 2.4 Language — the underestimated one

`config.ARTICLE_LANGUAGE` is a real dial, but **only for four stages**: it is
substituted into `pisarz.md`, `notka.md`, `komentarz.md` and `odpowiedz.md`.

English is assumed separately in:

* `SCOUT_SYSTEM` — now composed from `ARTICLE_LANGUAGE`, so this one follows;
* the browser context — `locale="en-US"`;
* all 23 live prompts, which are written in English;
* **the gates in `gates.py`, which are English regular expressions.**

That last one is the trap. `ZAKAZANE_OTWARCIA` matches `turn over`,
`next time you`, `most people think`. `ZASTRZEZENIE` matches `I think`,
`in my view`. In another language they **match nothing and report nothing** —
the gate does not fail, it silently stops existing.

---

# PART 3 — KEYS AND EXTERNAL SERVICES

## 3.1 Environment variables

Derived from the code, not from `.env.example` — which described a previous
agent until this work replaced it.

| variable | for | on absence |
|---|---|---|
| `DEEPSEEK_API_KEY` | **21 of 26 stages** | stopped before the call |
| `ANTHROPIC_API_KEY` | notes, article, repair | stopped before the call |
| `OPENAI_API_KEY` | cover image only | stopped; the article ships without a cover |
| `DRY_RUN` | blocks model calls **and the browser** | defaults false |
| `KILL_SWITCH` | hard stop | defaults false |
| `AGENT_V2_SERVER` | headless server mode | defaults 0; set by all three systemd units |
| `AGENT_V2_CHEAP` | everything on DeepSeek but discovery | defaults 0 |
| `AGENT_V2_NO_LIMIT` | lifts daily and monthly ceilings, **not per-run** | defaults 0 |
| `AGENT_V2_WRITER` | swap the writer for an A/B | — |
| `AGENT_V2_TRYB` | database track | `produkcja` |
| `ALARM_EMAIL_TO`, `SMTP_*` | the only "something broke" channel | **silent degradation** |

> **Fixed during this work.** The pre-flight key check compared *model
> identifiers* rather than providers, so `claude-fable-5-1` (the whole article)
> and `deepseek-v4-pro` (13 roles) were not covered. Measured with empty keys:
> 12 of 26 roles stopped. The rest went to the network and failed on an HTTP
> response, so the message spoke about transport instead of a missing key.
> Now 26 of 26, via a single `llm._dostawca(model)`.

## 3.2 Services

| service | endpoint | required? |
|---|---|---|
| DeepSeek | `/chat/completions` and `/responses` (server-side web search) | **yes** |
| Anthropic | `anthropic` SDK | **yes** |
| OpenAI | `/v1/images/generations`, via `httpx`, no SDK | no |
| YouTube RSS | `feeds/videos.xml?channel_id=…`, no key, no consent wall | no — degrades to zero seed |
| SMTP | any | no — degrades silently |
| Substack | ~30 `/api/v1/*` endpoints + Playwright | **yes, unavoidable** |

## 3.3 The Substack session — where a human is always required

*Described from the code. Not run.*

### What it is

`agent-v2/data/storage-state.json`, a Playwright storage dump. One cookie
matters: `substack.sid`. There is no API key here — Substack has no publishing
API, so **the bot is a signed-in user.**

### How it is created

1. A human starts Chrome with a debugging port and **logs in themselves.**
2. `python agent-v2/browser.py sesja` attaches over CDP, confirms a signed-in
   view, and writes the file.
3. The file goes to the server.

An automated path exists and **the code advises against it** — it loops on
CAPTCHA.

### Why the machine matters

Not because the session is pinned to an address. Because of this, measured on a
live account:

> Publishing through a real Chrome returns 200; through headless Chromium the
> note simply never appears. Cloudflare fingerprints headless mode.

So the publishing machine needs a real Chrome with a display — a virtual one is
fine — and someone has to log into it once.

### Lifetime

Read from the cookie's own expiry; no constant is assumed. It **extends
itself**: Substack refreshes the cookie on activity and the bot re-saves state
after every run. It is invalidated by logging out anywhere, a password change,
or expiry. `alarm.py` warns below 14 days, on expiry, and on absence.

### What happens without it

Verified by running. The daily path stops **before spending anything**:

```
== przebieg 1 ==
  [budżet dnia] notki=5 lajki=10 komentarze=18 ...
== koszt przebiegu: $0.0000 w 0 wywołaniach ==
Brak sesji Substacka.
```

`wymagaj_sesji()` sits in front of everything that costs money. Keep that.

---

# PART 4 — WHAT CANNOT BE CONFIGURED

## 4.1 The proportions

Measured across 699 functions in 29 modules:

| layer | functions | portable? |
|---|---|---|
| editorial pipeline (`stages.py`) | 155, 23 of them paid | **yes** — touches the platform in one place |
| **Substack** | **62 touch the browser**, 44 in `browser.py` | **no** |
| accounting and measurement | ~90 | mostly |
| configuration and gates | 48 + the new loader | **language-dependent** |

**~55% general-purpose editorial machine, ~25% Substack, ~15% "in English",
~5% subject matter.**

The ordering is the opposite of most people's intuition: **the subject is
cheapest, the platform dearest, and the language sits in the middle where it is
routinely underestimated.**

## 4.2 Substack

`browser.py` is 5,131 lines but **41% is comments and docstrings** — about
2,470 lines of real code. That changes the scale of the problem from "230 KB to
rewrite" to "two and a half thousand lines of Playwright and HTTP".

It still cannot be lifted into configuration, because what is welded in is
*meaning*, not addresses:

| what | how much | why not a config field |
|---|---|---|
| `/api/v1/*` endpoints | ~30 shapes | each returns a different shape, unpacked separately |
| Playwright selectors | 57 | composer, article editor, comment box |
| **publish confirmation** | **7 separate functions** | clicking "publish" does not mean anything appeared |
| reach cards | 4 different number shapes | each unpacked separately |
| reader feed | `kanal.py`, ~10 functions | "where do comment targets come from" is a Substack concept |

**Confirmation is the expensive part, not publishing.** Seven functions exist
because there is a constant for the case: `POWOD_HOST_NIE_POKAZUJE = "Substack
nie potwierdzil, ze wyszlo"` — and a whole mechanism for telling "it did not go
out" apart from "I do not know". That logic came from measurement on a live
account (comments under posts vanished in 7% of attempts, under notes in 30%)
and **a new platform has to be measured from scratch**. That is observation
work, not programming, and it takes weeks.

**Estimate: 2,000–2,500 lines plus weeks of live observation.** There is no
shortcut and it is not worth smoothing over.

## 4.3 English

Rewriting 23 prompts (rewriting, not translating — the examples must come from
the target language), rewriting ~12 regular expressions in `gates.py`, and
collecting a new style corpus. **One to two weeks, mostly editorial.**

## 4.4 The subject

The cheapest of the three, and now largely a config file:

1. `NISZA`, `ZNAKI_NISZY`, `OBSZARY_REWIRU`, `HASLA_SZUKANIA` — **CONFIG**
2. `DZIEDZINY_CIEKAWOSTEK`, ≥29 entries — **TEXT, a few hours**
3. `KANALY` — **CONFIG**
4. `OPRAWA` / `NIE_TEMAT` — **TEXT**
5. ~~~30 sentences in 14 prompts~~ — **fixed**, injected from config
6. rebuild the generated documentation

**A day's work, mostly writing.**

## 4.5 Tied to one installation

| what | where |
|---|---|
| server path and user | `systemd/*.service` |
| run times in UTC | `systemd/nia-agent.timer` |
| `LIMIT_CZASU_PRZEBIEGU_S` **must equal** `TimeoutStartSec` | `config.py` and the unit file |
| **style profiles live outside `agent-v2/`** | `style-profiles/` — `agent-v2/` is not self-contained |
| test-copy marker | `TO_JEST_KOPIA_TESTOWA` — keep this |
| databases separate themselves | `DATA_DIR` derives from `config.py`'s location |

---

# PART 5 — THE CONFIGURATOR

## 5.1 What exists now

`konfiguracja.toml` next to `config.py`, optional, validated at startup.
Template: [`konfiguracja.example.toml`](../konfiguracja.example.toml).

```toml
[konto]      uchwyt, nazwa_marki, strefa_czytelnika
[temat]      nisza, jezyk, znaki_niszy, hasla_szukania, dziedziny
[zrodla]     kanaly_youtube, blokowane_hosty
[modele]     role = { note = "…" }        # overlaid, not replacing
[wolumeny]   komentarze/lajki/restacki/follow/subskrypcje, przebiegow
[pieniadze]  sufit_miesieczny/dzienny/przebiegu
[publikowanie] okno_et, martwe_godziny_et, notek_promujacych,
               okno_promocji_dni, miks_notek, ciche_dni
```

Proved end to end: six values in the file change both handle sources, the brand
inside the scout's system message, the niche, the volumes, the daily note count
and one model role — while leaving the 25 unlisted roles alone.

**A bad value stops the start**, and so does an unknown field name: a typo is
the most common way configuration silently fails. The message lists what was
allowed. Thirteen error cases are covered by `test_konfiguracja.py`.

Three things are deliberately **not** in the file: the "no limit" switch (an
environment variable, not a default in a file), gate thresholds (measurement
results, not sliders) and the AI-disclosure toggle (`config.py` says outright
that it is a public choice, not a technical setting).

## 5.2 What is still to do

### About a day each

| # | what | why it is not five minutes |
|---|---|---|
| 1 | lift the subject out of 14 prompts into a `{nisza}` field | the mechanism exists (`stages._prompt` substitutes fields), but the subject recurs in examples and counter-examples — `skaut.md` has seven places including a whole "Too vague" section. Editing, not substitution. **Code and prompt must change together**: `test_generatory` compares the fields the code supplies against the fields the prompt uses |
| 2 | the same for the brand name in nine prompts and two style profiles | same shape, smaller |
| 3 | style corpus as a **profile**, not a single pinned file | today: one file, one SHA-256, five paragraphs pinned by ordinal. Needed: a directory of voice profiles, each with a manifest, selected by a field. Keep the "nobody swaps the voice silently" guarantee — make it apply to the *selected* profile |

### Rewriting a module

| # | what | estimate |
|---|---|---|
| 4 | **platform layer** — `browser.py` + `kanal.py` behind an interface, plus a second implementation | ~2,500 lines plus weeks of live observation. See 4.2 |
| 5 | **a second language** | 23 prompts, ~12 regexes, a new corpus. One to two weeks of editorial work |

## 5.3 The honest answer

**Can this become a configurable product?**

**Yes**, if the product is *"an anonymous English-language Substack publication
about any subject."* Most of that is now done: values live in one file, prompts
are read from disk on every call, databases separate themselves, the test-copy
marker exists, and every paid call is attributed to a channel and guarded by a
test. What remains is lifting the subject out of prompt prose — a day of
writing.

**No**, if the product is *"a bot for any platform."* That is a second
`browser.py` from scratch and weeks of measuring what the new platform does not
confirm. That work does not shrink with better architecture, because most of it
is not programming.

**In the middle sits language, and it is the most dangerous of the three**,
because the gates in `gates.py` do not complain when the language changes —
they quietly stop matching. A product that lets someone pick a language without
replacing the gates will publish text with no form checking at all, and nobody
will find out, because everything stays green.
