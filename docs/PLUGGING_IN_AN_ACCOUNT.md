# Plugging in an account — what to set, and exactly where

One page. Everything you decide about a publication, and the one place each
decision goes.

> **Since 2026-09-05 the recommended form is a preset**: the same fields plus
> a `[preset]` header, in `presety/<name>.toml`, plugged in with
> `python narzedzia/presety.py podlacz <name>`. Presets add a voice section,
> notes per day, articles per week and the schedule, get their own data
> directory, and can be unplugged. `konfiguracja.toml` still loads when no
> preset is active; `python narzedzia/presety.py importuj-konfiguracje`
> converts it. Full description: [PRESETY.md](PRESETY.md) (Polish),
> [../presety/README.md](../presety/README.md) (English).

**Almost all of it is one file.** Copy the template, edit it, done:

```bash
cp konfiguracja.example.toml agent-v2/konfiguracja.toml
```

The file is optional — without it the bot runs on the defaults in `config.py`.
A bad value **or a mistyped field name stops the start** with a message naming
what was allowed, because a config that silently ignores a typo is worse than
no config at all.

---

## The whole thing at a glance

| you decide | field | constraint |
|---|---|---|
| **who this is** | | |
| Substack handle | `konto.uchwyt` | part before `.substack.com` |
| publication name | `konto.nazwa_marki` | goes into the scout's and writer's system messages, and into 12 prompts |
| readers' timezone | `konto.strefa_czytelnika` | **readers', not the server's** — drives the publishing window |
| **what it writes about** | | |
| the subject, one sentence | `temat.nisza` | handed to the model verbatim: *"a publication about {nisza}"* |
| language | `temat.jezyk` | **read section "Language" below before changing this** |
| words the code matches on | `temat.znaki_niszy` | every search phrase must contain one |
| search phrases | `temat.hasla_szukania` | **≥19**, spread over ≥3 areas |
| curiosity domains | `temat.dziedziny` | **≥29** at 14 patterns (grid must be ≥400 cells) |
| **where research comes from** | | |
| topic sources | `zrodla.kanaly_youtube` | YouTube channel IDs; **empty is allowed** |
| hosts to skip | `zrodla.blokowane_hosty` | sites that refuse automated reading |
| **which model does what** | | |
| any of the 26 roles | `modele.role` | overlaid on the defaults — list only what you change |
| **how much per day** | | |
| notes per day | `publikowanie.miks_notek` | the **length of this list** is the count |
| comments | `wolumeny.komentarze_dziennie` | range `[from, to]`, drawn once per day |
| likes | `wolumeny.lajki_dziennie` | range |
| restacks | `wolumeny.restacki_dziennie` | range |
| follows per month | `wolumeny.follow_miesiecznie` | range |
| subscriptions per month | `wolumeny.subskrypcje_miesiecznie` | range |
| runs per day | `wolumeny.przebiegow_dziennie` | must match the systemd timer |
| **money** | | |
| monthly ceiling | `pieniadze.sufit_miesieczny_usd` | the only hard block in the system |
| daily ceiling | `pieniadze.sufit_dzienny_usd` | |
| per-run ceiling | `pieniadze.sufit_przebiegu_usd` | applies even under `NO_LIMIT` |
| **when and how it publishes** | | |
| publishing window | `publikowanie.okno_et` | hours in the readers' timezone |
| dead hours inside it | `publikowanie.martwe_godziny_et` | |
| notes promoting one article | `publikowanie.notek_promujacych` | one per day; several links in a day is not promotion, it is pestering |
| how long an article stays promotable | `publikowanie.okno_promocji_dni` | a cold link does not work |
| quiet days | `publikowanie.ciche_dni_wlaczone`, `...cichy_dzien_na_ile` | an account that posts *every* day also has a machine's rhythm |

27 fields. Everything else is either a secret (`.env`), a decision (see the end
of this page), or measured behaviour you should not be turning into a slider.

---

## Detail where it matters

### Identity

```toml
[konto]
uchwyt            = "your-handle"
nazwa_marki       = "Your Publication"
strefa_czytelnika = "America/New_York"
```

The handle used to live in **two independent constants**, and changing one gave
a bot that published to one account and read the profile of another. It is one
value now, and a test enforces that.

The name reaches the model through `SCOUT_SYSTEM`, `WRITER_SYSTEM` and the
`{marka}` field, which `stages._prompt` injects into every prompt. You do not
have to touch a prompt file to rename a publication.

The two files in `style-profiles/` carry the name as `{marka}`, which
`style.load_profiles` substitutes when the article writer reads them.

### Subject

```toml
[temat]
nisza          = "how everyday things are made and regulated"
znaki_niszy    = ["standard", "rule", "regulat", "code", …]
hasla_szukania = ["engineering standards", "building codes", …]   # ≥19
dziedziny      = ["how a standard becomes mandatory, and who sat in the room", …]  # ≥29
```

Four fields with different jobs, and mixing them up is the usual mistake:

* **`nisza`** is prose for the *model*. One sentence, and it is substituted into
  fourteen prompts as `{nisza}`.
* **`znaki_niszy`** is for the *code*. Short substrings; a candidate post or one
  of your own search phrases counts as on-topic when it contains one. Keep the
  list short enough to read and argue with.
* **`hasla_szukania`** is what the agent types into search to find posts worth
  commenting under. **At least 19**, because at five phrases per run a smaller
  pool means looking at the same handful of accounts every day. They must also
  span three areas — twenty phrases about one thing reach the same accounts as
  three.
* **`dziedziny`** are not keywords. Each one describes *a place where something
  interesting sits* — "the tolerance on a part, and what happens at the edge of
  it". Short keywords give the model nothing to grip. Multiplied by the 14
  curiosity patterns they form the search grid, which must be **≥400 cells**.

Both thresholds are enforced by tests, so a too-thin configuration fails at
`python agent-v2/tests/test_szukanie_celow.py` rather than three weeks later in
the output.

### Language — read this before changing it

```toml
[temat]
jezyk = "English"
```

The field works: it flows into the writer, the note, the comment, the reply and
the scout's system message.

**But the gates are language-specific.** `agent-v2/jezyki.py` holds the patterns
that catch invented experience, unnamed studies, forbidden openings and
fake-sounding sources. Ship a language it does not know and every run prints:

```
[bramki] JEZYK 'Polish' NIE MA WZORCOW dla ZAKAZANE_OTWARCIA
         — TA BRAMKA JEST WYLACZONA.
         Nie zglosi niczego, i to nie znaczy, ze tekst jest czysty.
```

Eight of those, once per process. **The bot will still run** and still publish —
that is doctrine, nothing blocks content — but six gates and two phrase lists
are switched off and you will be told so on every run.

To do it properly, add an entry to `WZORCE` and `FRAZY` in `jezyki.py` with the
same keys as `"English"`. Every pattern there carries a note saying *what it
catches*, because translating a regular expression without knowing its purpose
produces something syntactically valid and functionally empty.

The 24 prompt files are also written in English. The model will follow
`{language}` and write in yours, but the *examples* inside those prompts stay
English until someone rewrites them.

### Where the research comes from

```toml
[zrodla]
kanaly_youtube  = { "Channel name" = "UCxxxxxxxxxxxxxxxxxxxxxx" }
blokowane_hosty = ["ecfr.gov", "researchgate.net", …]
```

This is the one people expect to work differently, so plainly:

**You cannot hand the bot a list of articles to write about.** There is no field
for source URLs and that is deliberate, not an omission. The whole credibility
chain — evidence card, `MIN_PRIMARY_SOURCES = 2`, fragment classification,
sentence-by-sentence review — assumes the bot **fetched and classified the
source itself**. Handing it finished links bypasses that.

What `kanaly_youtube` gives it is **seed**, not sources: channels that in your
niche have spent years deciding what is worth talking about. The bot takes the
*event* behind a headline and then goes and verifies it on its own. It never
takes the headline, and it never takes the channel's links.

It ships **empty**, and empty does not crash anything: the seed becomes
`(nothing fetched today)` and the domain grid carries the run. A note without
seed is less current; no note is worse.

Its own research route is `discovery` — a DeepSeek call with server-side web
search, the single most expensive stage in the system at 35% of the bill.

### Which model does what

```toml
[modele]
role = { note = "deepseek-v4-pro" }
```

**Listed roles are overlaid on the defaults**, so naming one does not wipe the
other 25. An unknown role name stops the start and prints the list of valid
ones.

The defaults, each measured rather than guessed:

| role | model | why |
|---|---|---|
| `write` | `claude-fable-5-1` | won a blind A/B on an identical evidence card |
| `note`, `naprawa` | `claude-opus-5` | notes drive most subscriber growth; all their force is in the first sentence |
| 13 roles incl. `comment`, `reply`, `discovery`, `review` | `deepseek-v4-pro` | SimpleQA 57.9 vs 34.1 — a ~70% edge on **factual recall** |
| classification, fact-check, curiosity, targets | `deepseek-v4-flash` | **extractive** work on supplied text, a third of the price |
| `obraz` | `gpt-image-1.5` | cover image; a failure here never blocks an article |

`note` and `note_tani` are the same stage with two writers, alternating by note
number. They are separate *stage names* rather than a parameter so the `calls`
table splits their cost by itself — a saving and a running blind test at once.

### Volumes and money

```toml
[wolumeny]
komentarze_dziennie = [15, 23]
lajki_dziennie      = [10, 16]

[publikowanie]
miks_notek = ["CIEKAWOSTKA", "CIEKAWOSTKA", "DYSKUSJA", "SPROSTOWANIE", "MYSL"]
```

Everything is a **range**, drawn once per day and seeded from the date, so every
run that day agrees on the budget and consecutive days differ. A fixed number
per day is a machine signature.

Notes are the exception in shape: **the count is the length of `miks_notek`**,
because a separate "how many notes" constant kept drifting away from the mix.
Valid types: `ARTYKUL`, `CIEKAWOSTKA`, `DYSKUSJA`, `MYSL`, `SPROSTOWANIE`.

At the defaults, a day of notes, comments and replies costs roughly **$0.30**
and one article **$0.75–0.78**.

---

## What is NOT in the file, and why

Three things look like fields and are decisions:

* **"No limit"** — the monthly ceiling is the only hard block in the system.
  The override exists as the environment variable `AGENT_V2_NO_LIMIT`, not as a
  default sitting in a config file.
* **Gate thresholds** (`SLOW_NA_BEAT`, `BUDZET_ZASTRZEZEN`,
  `MIN_ZRODEL_DO_PISANIA`) — measurement results, not sliders. Exposed as dials
  they get turned toward "blocks less", because that is the direction they
  always get turned.
* **The AI-disclosure switch** — `config.py` says outright that this is a public
  choice, not a technical setting. It stays there with its reasoning.

Two more things live elsewhere by nature:

* **Keys** — `agent-v2/.env`, never in the repository.
* **Run times** — `agent-v2/systemd/nia-agent.timer`. Note that
  `config.LIMIT_CZASU_PRZEBIEGU_S` and `TimeoutStartSec` in the service file are
  **the same number in two places** and must match, or the agent computes a
  different deadline than systemd enforces.

---

## Order to do it in

1. `pip install -r requirements-dev.txt`
2. `cp .env.example agent-v2/.env` — fill in the three keys
3. `cp konfiguracja.example.toml agent-v2/konfiguracja.toml` — edit
4. `python agent-v2/alarm.py` — the health check tells you what is still missing
5. `python agent-v2/tests/test_szukanie_celow.py` and `test_generatory.py` —
   confirms your topic passes the thresholds
6. `python agent-v2/dokumentacja-zrodla/sklej.py` — **not optional**, a test
   fails until the generated documentation is rebuilt
7. The Substack session — [INSTALL.md](INSTALL.md) step 5. This is the one step
   no software does for you.
8. `python agent-v2/run.py --dzien` — no `--wyslij`, so nothing reaches the world
9. `python narzedzia/audyt.py` — 28 checks, including that no previous
   account's identity survived your edit
10. Prove it can publish — see the next section. Nothing above this line ever
    puts a word on your account, so until you do this you have tested
    everything except the one thing your readers will see.

---

## Proving it can publish

Two stages, in this order. Measured end to end on 2026-09-05 against a live
Substack account; the outputs below are real, not illustrative.

**Stage 1 — fill the field, click nothing.** `wyslij=False` types the note into
the real composer on the real site and stops:

```bash
python -c "import sys; sys.path.insert(0,'agent-v2'); import browser; print(browser.wystaw_notke('short test sentence', wyslij=False))"
```

```
  wpisane w pole notki: 23 słów
  przycisk wysyłki: 'Post'
  przycisk wysyłki widoczny: True
  (nie wysyłam — tryb sprawdzenia)
```

`przycisk wysyłki widoczny: True` is the line that matters. It says the code
found the composer, typed into the right field, and located the send button.
Everything except the click has now been proven, and nothing is public.

**Stage 2 — actually send it.** This needs `DRY_RUN=false`, and that is
deliberate: `agent-v2/.env` ships with `DRY_RUN=true` so that a fresh clone
cannot publish by accident. The flag blocks model calls **and** the browser —
an earlier version blocked only the models, and a "dry" run went on to like two
strangers' posts.

```bash
DRY_RUN=false python -c "import sys; sys.path.insert(0,'agent-v2'); import browser; print(browser.wystaw_notke('short test sentence', wyslij=True))"
```

```
  NOTKA PRZYJETA (odpowiedz Substacka: 200)
  id notki: 000000000
```

If you see `DRY_RUN — NIE wysylam, mimo ze proszono`, the flag is still on. That
message is the bot refusing out loud rather than reporting a success it did not
achieve.

**Then check it from outside.** The id in the output builds a public URL —
`https://substack.com/@YOUR_HANDLE/note/c-<THE ID FROM YOUR OWN OUTPUT>` — open it in
a browser where you are *not* logged in. A note that exists in the bot's own
ledger and nowhere else is the failure this step is here to catch.

---

## Where things live, if you need to go deeper

| you want to change | file |
|---|---|
| anything in the table above | `agent-v2/konfiguracja.toml` |
| gate patterns for a new language | `agent-v2/jezyki.py` |
| what the model is told at each stage | `agent-v2/prompts/*.md` (24 files) |
| the four candidate gates and twelve text gates | `agent-v2/gates.py` |
| the editorial voice | `agent-v2/prompts/styl/` + `style-profiles/` |
| the order of a day | `agent-v2/run.py`, `dzien()` |
| anything about Substack itself | `agent-v2/browser.py`, `agent-v2/kanal.py` |

Full function-level index: [FUNCTION_MAP.md](FUNCTION_MAP.md) — 658 functions,
which of them cost money and for which stage, and who calls each one.
